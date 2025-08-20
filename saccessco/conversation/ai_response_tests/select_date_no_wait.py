from datetime import datetime

from saccessco.conversation.ai_response_tests.utils import BaseTest


class TestSelectDateNoWait(BaseTest):
       def get_test_response(self, **kwargs):
           date_str = kwargs.get("date", "22/10/2025")
           date_object = datetime.strptime(date_str, '%d/%m/%Y')
           formatted_date = date_object.strftime('%-d %B %Y.')
           month_name = date_object.strftime('%B')
           year = date_object.strftime('%Y')

           return {
             "execute": {
               "plan": [
                 {
                   "action": "click",
                   "selector": "[data-testid='depart-btn']",
                   "data": None
                 },
                 {
                   "action": "click",
                   "selector": f"[aria-label*='{formatted_date}']",
                   "data": None
                 }
               ],
               "parameters": {}
             },
             "speak": f"Running Test. Set the departure date to {formatted_date}"
           }
