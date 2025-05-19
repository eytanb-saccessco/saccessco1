from dotenv import load_dotenv
import openai
import os
from django.conf import settings
from saccessco.utils.singleton import Singleton
import copy
from typing import List, Dict, Any

load_dotenv()
openai.api_key = os.getenv("OPEN_API_KEY")

SYSTEM_INSTRUCTIONS = (
    "You are an AI that helps users use a webpages. "
    "The you are helping in the context of a 'conversation'."
    "The conversation history is represented by the messages you received."
    "When the page on the browser changes you receive a system message with header 'PAGE CHANGE'."
    "The page change message will contain the HTML content of the current page."
    "User intent is conveyed via user messages containing what the user said."
    "Your job is to determine if and how the user's goal can be achieved via interactions with the current page."
    "Your response will be a json objects with the following fields: "
    "'execute' - will contain a DOM manipulation script in the form of a list of json objects containing the following fields: "
    "   'element' whose value should a locator for locating an element on the page. The locator should be based on the current page html"
    "   'action' whose value represent some functionality allowed for usage on the element in the DOM."
    "   'data' whose value represents the value to use if needed and known."
    "All the selectors must be based on the current page html - last PAGE CHANGE content."
    "'speak' will contain a text message to send to the user. It should be used in cases when the user's intent is not clear or when it's not clear hwo to provide it."
    "And also when some required data is missing, for requesting it from the user"
    "In the process of conversation with a user the page html may change, or the browser my be directed to a new page/url."
    "In those cases you should try to continue your effort to help the user based on the new HTMl content and the latest user intent."
)
class Role:
    def __init__(self, name):
        self.name = name

    @property
    def cap_name(self):
        return self.name.upper()

User = Role("user")
System = Role("system")
ROLES = {"User": User, "System":System}


class Message:
    def __init__(self, role: Role, content):
        self.role = role if type(role) == str else role.name
        self.content = content

    @property
    def json(self):
        return {"role": self.role, "content": self.content}


class AIEngine(metaclass=Singleton):

    def __init__(self, instructions=SYSTEM_INSTRUCTIONS):
        self.conversation = []
        self.add_message("system", content=instructions)

    def get_conversation(self):
        return copy.deepcopy(self.conversation)

    def set_conversation(self, conversation: List[Dict[Any, Any]]):
        self.conversation = copy.deepcopy(conversation)

    def clear(self):
        self.conversation = []
        self.add_message("system", content=SYSTEM_INSTRUCTIONS)

    def add_message(self, role, content):
        self.conversation.append(Message(role, content).json)

    def respond(self):
        response = openai.ChatCompletion.create(
            model=settings.OPEN_API_MODEL,
            messages=self.conversation
        )
        return response["choices"][0]["message"]["content"]

