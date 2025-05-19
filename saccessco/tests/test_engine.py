import json

from django.test import TestCase

from saccessco.ai import AIEngine, User, System
from saccessco.utils.html import get_rendered_html
from .fixture import SKYSCANNER_HTML


class TestSingleton(TestCase):
    def test_singleton(self):
        a = AIEngine()
        b = AIEngine()
        self.assertEqual(a, b)


class TestAIEngine(TestCase):
    def setUp(self):
        self.html = get_rendered_html("https://www.skyscanner.co.il/")
        self.user_prompt = "I want to fly from Tel Aviv to Madrid, depart July 4th, return August 20th"
        self.engine = AIEngine()
        self.engine.add_message(System, f"PAGE CHANGE\n{self.html}")
        self.engine.add_message(User, self.user_prompt)

    def tearDown(self):
        self.engine.clear()

    def test_page_change(self):
        result_str = self.engine.respond()
        result = json.loads(result_str)
        if any(sub in result["speak"] for sub in ["captcha", "CAPTCHA"]):
            self.engine.add_message(User, "close captcha")
            # self.engine.add_message(System, f"PAGE CHANGE\n{SKYSCANNER_HTML}")
            print(self.engine.respond())
            self.engine.add_message(User, "Continue please")
        print(self.engine.respond())