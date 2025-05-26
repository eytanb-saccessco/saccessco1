import json

from django.test import TestCase

from saccessco.ai import AIEngine, User, Model
from saccessco.utils.html import get_rendered_html


class TestAIEngine(TestCase):
    def setUp(self):
        self.html = get_rendered_html("https://www.skyscanner.co.il/")
        self.user_prompt = "I want to fly from Tel Aviv to Madrid, depart July 4th, return August 20th"
        self.engine = AIEngine()

    def test_page_change(self):
        result_str = self.engine.respond(Model, f"PAGE CHANGE\n{self.html}")
        print(result_str)

    def test_user_prompt(self):
        page_change_result = self.engine.respond(Model, f"PAGE CHANGE\n{self.html}")
        self.engine.add_message_to_history(Model, page_change_result)
        user_prompt_result = self.engine.respond(User, "Close the captcha")
        print(user_prompt_result)