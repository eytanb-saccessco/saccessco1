from __future__ import annotations

import os
import copy
import logging
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from openai import OpenAI
# keep your existing imports
from saccessco.ai.instructions import SYSTEM_INSTRUCTIONS
from saccessco.utils.singleton import Singleton  # optional, leave commented if you don't need it

load_dotenv()

logger = logging.getLogger("saccessco")


# ---- Roles (kept identical for drop-in compatibility) ----
class Role:
    def __init__(self, name: str):
        self.name = name

    @property
    def cap_name(self) -> str:
        return self.name.upper()


User = Role("user")
Model = Role("model")
ROLES = {"User": User, "Model": Model}


class Message:
    """
    Same helper as your Gemini version. We preserve it for compatibility.
    """
    def __init__(self, role: Role, content: str):
        self.role = role.name if isinstance(role, Role) else role
        self.content = content

    @property
    def to_gemini_content_dict(self) -> Dict[str, Any]:
        # Kept for compatibility with existing code that might call it.
        return {"role": self.role, "parts": [{"text": self.content}]}


# @Singleton  # Uncomment if you really want a singleton
class AIEngine:
    """
    Drop-in replacement for your Gemini-based AIEngine, using OpenAI Chat Completions.

    - Public API matches your original:
        add_message_to_history(role, content)
        get_chat_history()
        respond(role, prompt) -> str
        reset_chat()

    - Internal history format remains your Gemini-style:
        [{"role": "...", "parts": [{"text": "..."}]}, ...]

    - Converts to OpenAI messages at call time, with a proper 'system' message.
    """

    def __init__(self, initial_instructions: str = SYSTEM_INSTRUCTIONS):
        self._initial_instructions: str = initial_instructions or ""
        self._chat_history: List[Dict[str, Any]] = []

        # OpenAI client / config
        self.model_name: str = os.getenv("OPENAI_API_MODEL", "gpt-4o")
        # self.temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0"))
        self.max_tokens: Optional[int] = (
            int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS")) if os.getenv("OPENAI_MAX_OUTPUT_TOKENS") else None
        )

        # Construct client; it will pick up OPENAI_API_KEY from env
        self.client = OpenAI()

        print(f"Using OPENAI_API_KEY set: {bool(os.getenv('OPENAI_API_KEY'))}, model: {self.model_name}")

        # For strict compatibility with your Gemini engine, we add the initial instructions
        # as a "Model" message to history (but we will *map it* to OpenAI 'system' at call time).
        if self._initial_instructions:
            self.add_message_to_history(Model, self._initial_instructions)

    # ---------- history helpers (identical signatures) ----------
    def add_message_to_history(self, role: Role, content: str):
        """
        Stores a message in the same structure your Gemini code expects:
        { "role": role.name, "parts": [{"text": content}] }
        """
        role_name = role.name if isinstance(role, Role) else str(role)
        self._chat_history.append({"role": role_name, "parts": [{"text": content}]})

    def get_chat_history(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(self._chat_history)

    def reset_chat(self):
        """
        Clears state and re-adds initial system instructions (as a 'Model' message in history
        for drop-in parity). We'll convert it to OpenAI 'system' at request time.
        """
        self._chat_history = []
        if self._initial_instructions:
            self.add_message_to_history(Model, self._initial_instructions)
        print("Chat session reset.")

    # ---------- public: respond ----------
    def respond(self, role: Role, prompt: str) -> str:
        """
        Sends the prompt and returns assistant text. Maintains chat history.
        """
        # 1) Record user's turn in your Gemini-style history
        self.add_message_to_history(role, prompt)

        # 2) Convert history to OpenAI Chat messages
        messages = self._to_openai_messages()

        # 3) Call OpenAI with retries
        try:
            resp = self._call_openai(messages)
            text = (resp.choices[0].message.content or "").strip()
        except Exception as e:
            logger.exception("Error communicating with OpenAI: %s", e)
            # On failure, mirror your Gemini engine behavior: remove the last user turn
            if self._chat_history and (self._chat_history[-1].get("role") in ("user", "User")):
                self._chat_history.pop()
            return f"Error: Could not get a response from the AI. {e}"

        # 4) Append assistant reply to history (so multi-turn has full context)
        if text:
            self.add_message_to_history(Model, text)

        logger.info("AI Response: %s", text)
        return text

    # ---------- internals ----------
    def _to_openai_messages(self) -> List[Dict[str, str]]:
        """
        Transform your Gemini-style history into OpenAI Chat messages.
        - The first 'Model' message that matches initial instructions is mapped to a single system message.
        - Other 'Model' messages are mapped to 'assistant'.
        - 'user' maps to 'user'.
        """
        msgs: List[Dict[str, str]] = []

        # Always add system up front using the stored initial instructions.
        if self._initial_instructions:
            msgs.append({"role": "system", "content": self._initial_instructions})

        # Now walk the stored history and convert the rest.
        # Skip the first Model message if it equals the initial instructions (to avoid duplication).
        skipped_initial_model = False
        for entry in self._chat_history:
            role = (entry.get("role") or "").lower()
            parts = entry.get("parts") or []
            text = parts[0].get("text") if parts and isinstance(parts[0], dict) else ""

            if not text:
                continue

            if role in ("user",):
                msgs.append({"role": "user", "content": text})
            elif role in ("model", "assistant"):
                if (not skipped_initial_model) and text == self._initial_instructions:
                    # already placed as system message
                    skipped_initial_model = True
                    continue
                msgs.append({"role": "assistant", "content": text})
            else:
                # Unknown roles -> treat as user for safety
                msgs.append({"role": "user", "content": text})

        return msgs

    def _call_openai(self, messages: List[Dict[str, str]], max_retries: int = 3):
        """
        Basic retry loop for transient errors.
        """
        attempt = 0
        last_exc: Optional[Exception] = None

        while attempt < max_retries:
            attempt += 1
            try:
                kwargs = dict(
                    model=self.model_name,
                    messages=messages,
                )
                if self.max_tokens is not None:
                    # New SDKs support max_output_tokens for responses.*; for chat.completions it's max_tokens
                    kwargs["max_tokens"] = self.max_tokens

                return self.client.chat.completions.create(**kwargs)
            except (RateLimitError, APIError) as e:
                last_exc = e
                logger.warning("OpenAI transient error (attempt %d/%d): %s", attempt, max_retries, e)
            except BadRequestError as e:
                # Schema / prompt issues are usually not transient; re-raise.
                logger.error("OpenAI bad request: %s", e)
                raise
            except Exception as e:
                last_exc = e
                logger.exception("OpenAI unexpected error: %s", e)

        assert last_exc is not None
        raise last_exc
