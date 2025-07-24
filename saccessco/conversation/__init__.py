import json
from concurrent.futures import ThreadPoolExecutor, Future
from channels.layers import get_channel_layer
from saccessco.ai import AIEngine, User, Model  # Assuming these are correctly defined
import logging
from asgiref.sync import async_to_sync
import threading  # For logging thread info

from saccessco.consumers import AiConsumer
from saccessco.conversation.ai_response_tests import TESTS
from saccessco.conversation.ai_response_tests.utils import parse_test_prompt

logger = logging.getLogger("saccessco")

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
                try:
                    # Remove markdown code block delimiters if present
                    json_str = ai_response.replace("```json", "").replace("```", "").strip()
                    logger.info(f"--DEBUG--: _inner thread: self.ai_engine.response: {json_str}")
                    ai_response_object = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(
                        f"[{current_thread_name}] Failed to parse AI response as JSON: {e}. Raw response: {ai_response[:200]}...",
                        exc_info=True)
                    ai_response_object = {"error": "JSON parsing failed", "details": str(e),
                                          "raw_ai_response": ai_response[:100]}

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
