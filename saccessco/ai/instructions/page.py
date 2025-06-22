PAGE_INSTRUCTIONS = (
    "# Page Change Instructions\n\n"
    "* When receiving a page change html\n"
    "Please describe:\n"
    "1. All identifiable interactive functionalities for an end-user.\n"
    "2. A JavaScript DOM manipulation script to simulate a user interaction.\n"
    "2.1 The JavaScript part should include a object at the top, listing the data needed to perform the action\n"
    "2.2 If a value for a given parameter can be deduced from the conversation or the user prompt:\n"
    "2.3 The parameters object should contain tha value, otherwise the value should be null\n"
    "2.2 The script does not need to contain code fro prompting the user for missing parameters values\n"
    "2.2.2 The functionality is provided by a wrapper class the wraps the parameters object\n"
    "2.2.3 And exposes a get function that hides that complexity\n"
)