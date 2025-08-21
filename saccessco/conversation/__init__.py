import json
from concurrent.futures import ThreadPoolExecutor, Future
from channels.layers import get_channel_layer
from saccessco.ai import GeminiAIEngine as AIEngine, User, Model  # Assuming these are correctly defined
# from saccessco.ai import ChtgptAIEngine as AIEngine, User, Model  # Assuming these are correctly defined
import logging
from asgiref.sync import async_to_sync
import threading  # For logging thread info

from saccessco.consumers import AiConsumer
from saccessco.conversation.ai_response_tests import TESTS
from saccessco.conversation.ai_response_tests.utils import parse_test_prompt
import json, re

logger = logging.getLogger("saccessco")

def _smart_join(a: str, b: str) -> str:
    a = (a or "").strip()
    b = (b or "").strip()
    if not a: return b
    if not b: return a
    # If a ends with sentence punctuation, just add a space; otherwise add a comma
    return f"{a} {b}" if re.search(r'[.!?]\s*$', a) else f"{a}, {b}"

def _extract_json_and_preamble(raw: str):
    """
    Returns (preamble_text, json_obj).
    Finds the first fenced code block ```json ... ``` (or any ``` ... ```),
    or falls back to the first {...} block. Any text outside the JSON is 'preamble'.
    """
    s = raw or ""
    # Prefer ```json ... ```
    m = re.search(r"```json\s*([\s\S]*?)\s*```", s, flags=re.IGNORECASE)
    if not m:
        # Accept generic fenced block
        m = re.search(r"```\s*([\s\S]*?)\s*```", s)
    if m:
        json_str = m.group(1).strip()
        pre = (s[:m.start()] + s[m.end():]).strip()
    else:
        # Fallback: grab the first {...} region
        lb = s.find("{"); rb = s.rfind("}")
        if lb != -1 and rb != -1 and rb > lb:
            json_str = s[lb:rb+1].strip()
            pre = (s[:lb] + s[rb+1:]).strip()
        else:
            raise ValueError("No JSON block found")

    obj = json.loads(json_str)  # let it raise; caller handles
    return pre, obj

def _parse_ai_response_merge_speak(ai_response: str):
    """
    Produces a dict like:
      {"speak": "...", "execute": [...]}
    Merges any free text into obj['speak'].
    Ensures 'execute' exists (list).
    """
    preamble, obj = _extract_json_and_preamble(ai_response)

    # Normalize structure
    if not isinstance(obj, dict):
        obj = {"speak": str(obj)}
    if "execute" not in obj:
        obj["execute"] = []
    # Some models might emit execute as dict; normalize to list
    if isinstance(obj.get("execute"), dict):
        obj["execute"] = [obj["execute"]]

    # Merge speak
    speak = obj.get("speak", "").strip()
    if preamble:
        obj["speak"] = _smart_join(preamble, speak)
    else:
        obj["speak"] = speak or ""

    return obj


class Conversation:
    # Class-level dictionary to store instances by ID
    _instances = {}
    _lock = threading.Lock()  # Use a lock to ensure thread-safe instance management

    def __new__(cls, conversation_id: str):
        """
        Called before __init__. Checks if an instance with this ID already exists.
        """
        with cls._lock:  # Acquire a lock to prevent race conditions during instance creation/retrieval
            if conversation_id not in cls._instances:
                # If no instance exists, create a new one
                instance = super(Conversation, cls).__new__(cls)
                cls._instances[conversation_id] = instance
                # Set a flag to indicate that __init__ should perform full initialization
                instance._initialized = False
            else:
                # If an instance exists, return the existing one
                instance = cls._instances[conversation_id]
                # Set a flag to indicate that __init__ should skip full re-initialization
                instance._initialized = True
            return instance

    def __init__(self, conversation_id: str):
        if self._initialized:
            logger.info(f"Returning existing Conversation instance for ID: {conversation_id}")
            return

        self.id = conversation_id
        self.ai_engine = AIEngine()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"Conv-{conversation_id}-")
        self.channel_layer = get_channel_layer()

        logger.info(f"New Conversation instance created and initialized for ID: {conversation_id}")
        self._initialized = True  # Mark as initialized

    def page_change(self, new_html):
        def _inner():
            current_thread_name = threading.current_thread().name
            logger.info(f"[{current_thread_name}] Processing page change for conversation {self.id}")
            try:
                page_analysis = self.ai_engine.respond(User, f"PAGE CHANGE\n{new_html}")
                self.ai_engine.add_message_to_history(Model, page_analysis)
                logger.info(f"[{current_thread_name}] Page change analysis complete.")
            except Exception as e:
                logger.error(f"[{current_thread_name}] Error during page change analysis: {e}", exc_info=True)

        self.executor.submit(_inner)

    def user_prompt(self, prompt) -> Future:
        def _run_test():
            logger.info(f"--DEBUG-- Existing tests: {TESTS}")
            logger.info(f"--DEBUG-- Looking for test: {prompt}")
            test_name, kwargs = parse_test_prompt(prompt)
            test = TESTS.get(test_name)
            if test is None:
                logger.info(f"--DEBUG-- No test: {test_name}")
                _send({"execute": {"plan":[], "parameters":{}}, "speak": f"Test not found: {prompt}"}, "test_thread")
            else:
                logger.info(f"--DEBUG-- Test: {test_name} Found!!!")
                _send(test.get_test_response(**kwargs), "test_thread")

        def _inner():
            current_thread_name = threading.current_thread().name
            logger.info(f"[{current_thread_name}] Processing user prompt for conversation {self.id}")
            try:
                ai_response = self.ai_engine.respond(User, prompt)
                self.ai_engine.add_message_to_history(Model, ai_response)

                # IMPORTANT: Safely parse JSON
                # IMPORTANT: Safely parse & merge any preamble text into JSON.speak
                try:
                    logger.info(f"--DEBUG--: _inner thread: raw ai_engine.response (first 500): {ai_response[:500]!r}")
                    ai_response_object = _parse_ai_response_merge_speak(ai_response)
                except Exception as e:
                    logger.error(
                        f"[{current_thread_name}] Failed to parse AI response as JSON: {e}. "
                        f"Raw response head: {ai_response[:200]!r}",
                        exc_info=True
                    )
                    # sensible fallback
                    ai_response_object = {"speak": ai_response.strip(), "execute": []}

                # --- CRUCIAL LOGIC FOR SENDING VIA CHANNEL LAYER ---
                _send(ai_response_object, current_thread_name)
                # --- END CRUCIAL LOGIC ---

            except Exception as e:
                logger.error(f"[{current_thread_name}] Error during user prompt processing: {e}", exc_info=True)

        def _send(ai_response_object, current_thread_name):
            if self.channel_layer:
                conversation_group_name = f"{AiConsumer.GROUP_NAME_PREFIX}{self.id}"

                # This is the line that was missing before!
                async_to_sync(self.channel_layer.group_send)(
                    conversation_group_name,
                    {
                        'type': 'ai_response',
                        'ai_response': ai_response_object,
                    }
                )
                logger.info(
                    f"[{current_thread_name}] Sent structured AI response to group '{conversation_group_name}'.")
            else:
                logger.error(f"[{current_thread_name}] Channel layer was not available to send AI response.")
        if prompt.startswith("Test") or prompt.startswith("test"):
            _run_test()
        else:
            return self.executor.submit(_inner)

    def shutdown(self):
        logger.info(f"Shutting down ThreadPoolExecutor for Conversation ID: {self.id}")
        self.executor.shutdown(wait=True)
