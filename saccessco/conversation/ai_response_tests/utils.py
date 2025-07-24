import abc
import json
import re
import logging

logger = logging.getLogger("saccessco")

class BaseTest(abc.ABC):
    """
    Abstract Base Class for all test implementations.
    All test classes must inherit from this and implement get_test_response.
    """
    def __init__(self, test_name):
        self._test_name = test_name
        logger.info(f"Initialized BaseTest: {self._test_name}")

    @abc.abstractmethod
    def get_test_response(self, **kwargs):
        raise NotImplementedError()

def parse_test_prompt(prompt_string: str) -> tuple[str, dict]:
    """
    Parses a test prompt string of the pattern "<test name with spaces> <kwargs>"
    and returns the test name and a dictionary of kwargs.

    The kwargs part is expected to be a JSON string (e.g., '{"key": "value"}')
    and is optional. If not present, kwargs will be an empty dictionary.

    Args:
        prompt_string (str): The input string, e.g., "My Test Case {'key': 'value', 'num': 123}"
                             or "Another Test".

    Returns:
        tuple: A tuple containing:
               - str: The test name (can contain spaces).
               - dict: A dictionary of keyword arguments, or an empty dict if no kwargs
                       are provided or parsing fails.
    """
    if not isinstance(prompt_string, str) or not prompt_string.strip():
        # Handle empty or non-string input
        return "", {}

    # Trim leading/trailing whitespace from the entire prompt
    trimmed_prompt = prompt_string.strip()

    # Regex to capture everything before the LAST JSON-like object as test name,
    # and the JSON-like object itself as kwargs.
    # It looks for an optional JSON object at the end of the string.
    # (.*?) - non-greedy match for test name (anything until the JSON part)
    # \s* - optional whitespace
    # (\{.*\})? - optional JSON object (group 2)
    # \s*$  - optional whitespace at the end of the string
    match = re.match(r'(.*?)\s*(\{.*\})?\s*$', trimmed_prompt)

    if not match:
        # This case should ideally not be hit for valid non-empty strings
        # given the regex, but as a safeguard, return the whole string as test name.
        logger.warning(f"Regex did not match expected pattern for: '{trimmed_prompt}'. Treating whole string as test name.")
        return trimmed_prompt, {}

    test_name = match.group(1).strip() # Capture group 1 (test name part) and strip its whitespace
    kwargs_string = match.group(2)      # Capture group 2 (kwargs JSON string, or None)

    kwargs_dict = {}
    if kwargs_string:
        try:
            # json.loads requires double quotes for string keys/values.
            # If the input uses single quotes, replace them for compatibility.
            # This is a common workaround if input is not strictly JSON compliant
            # but aims to be JSON-like. For strict JSON, ensure input uses double quotes.
            if "'" in kwargs_string and '"' not in kwargs_string:
                 kwargs_string = kwargs_string.replace("'", '"')

            kwargs_dict = json.loads(kwargs_string)
            if not isinstance(kwargs_dict, dict):
                # If json.loads returns something other than a dict (e.g., a list, string, number)
                logger.info(f"Warning: Kwargs string '{kwargs_string}' was parsed but is not a dictionary. Returning empty dict.")
                kwargs_dict = {}
        except json.JSONDecodeError as e:
            logger.info(f"Warning: Could not parse kwargs string '{kwargs_string}' as JSON: {e}. Returning empty dict.")
            kwargs_dict = {}
        except Exception as e:
            logger.info(f"An unexpected error occurred during kwargs parsing: {e}. Returning empty dict.")
            kwargs_dict = {}

    return test_name, kwargs_dict

