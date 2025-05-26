from dotenv import load_dotenv
from google import genai  # The new, recommended SDK
import os
from django.conf import settings  # Assuming you still need Django settings for something
import copy
from typing import List, Dict, Any

# Assuming saccessco.ai.instructions and saccessco.utils.singleton exist
from saccessco.ai.instructions import SYSTEM_INSTRUCTIONS
from saccessco.utils.singleton import Singleton  # Keep your Singleton if you need it

load_dotenv()


class Role:
    def __init__(self, name):
        self.name = name

    @property
    def cap_name(self):
        return self.name.upper()


User = Role("user")
Model = Role("model")
ROLES = {"User": User, "Model": Model}


class Message:
    def __init__(self, role: Role, content):
        self.role = role.name if isinstance(role, Role) else role
        self.content = content

    @property
    def to_gemini_content_dict(self):
        """
        Converts the message to the format expected by the Gemini API for history.
        This handles both text and potentially other parts (though we're focusing on text here).
        """
        return {"role": self.role, "parts": [{"text": self.content}]}


# @Singleton # Uncomment this decorator if you intend for AIEngine to be a singleton
class AIEngine:
    """
    A class to manage interactions with Google's Generative AI models
    using the new, recommended 'google-genai' SDK, with explicit history management.
    """

    def __init__(self, initial_instructions: str = SYSTEM_INSTRUCTIONS):

        print(f"Using api_key: {os.getenv('GEMINI_API_KEY')}, model: {os.getenv('GEMINI_API_MODEL')}")

        self.client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        self.model_name = os.getenv('GEMINI_API_MODEL')
        self._chat_history: List[Dict[str, Any]] = []

        if initial_instructions:
            self.add_message_to_history(Model, initial_instructions)

    def add_message_to_history(self, role: Role, content: str):
        """
        Adds a message to the internal chat history.
        The content is stored in the format expected by the Gemini API.
        """
        self._chat_history.append({"role": role.name, "parts": [{"text": content}]})

    def get_chat_history(self) -> List[Dict[str, Any]]:
        """
        Returns the current chat history.
        """
        return copy.deepcopy(self._chat_history)

    def respond(self, role: Role, prompt: str) -> str:
        """
        Sends a user prompt to the AI model and returns the response.
        Manually manages the chat history for the continuous conversation.
        """
        # Add user's message to history before sending
        self.add_message_to_history(role, prompt)

        try:
            # Send the entire accumulated history with the current prompt
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=self._chat_history
            )

            ai_response_text = response.text

            return ai_response_text
        except Exception as e:
            print(f"Error communicating with Gemini: {e}")
            # If an error occurs, remove the last user message from history
            # to avoid sending an incomplete turn in the next request.
            if self._chat_history and self._chat_history[-1]["role"] == User.name:
                self._chat_history.pop()
            return f"Error: Could not get a response from the AI. {e}"

    def reset_chat(self):
        """
        Resets the current chat session, clearing its history.
        The initial system instructions will be re-added.
        """
        self._chat_history = []
        if self._initial_instructions:
            self.add_message_to_history(Model, self._initial_instructions)
        print("Chat session reset.")

