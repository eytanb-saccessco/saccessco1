import json
from jsonschema import validate, ValidationError
import logging

logger = logging.getLogger("saccessco")

# Define the JSON schema as a Python dictionary
# This is the schema previously generated for the AI Response structure.
ai_response_schema = {
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AI Response Schema",
  "description": "Schema for AI-generated responses, including execution plans and speech output.",
  "type": "object",
  "required": ["type", "ai_response"],
  "properties": {
    "type": {
      "type": "string",
      "description": "Indicates the overall type of the AI response.",
      "enum": ["ai_response"]
    },
    "ai_response": {
      "type": "object",
      "description": "Contains the detailed AI response, which can include an execution plan and speech.",
      "properties": {
        "execute": {
          "type": "object",
          "description": "An optional block detailing a plan for DOM manipulation and associated parameters.",
          "required": ["plan", "parameters"],
          "properties": {
            "plan": {
              "type": "array",
              "description": "A list of DOM manipulation actions to be executed sequentially.",
              "items": {
                "type": "object",
                "description": "An individual DOM manipulation action.",
                "required": ["selector", "action", "data"],
                "properties": {
                  "selector": {
                    "type": "string",
                    "description": "A CSS selector string targeting the DOM element for the action."
                  },
                  "action": {
                    "type": "string",
                    "description": "The type of action to perform on the selected element.",
                    "enum": ["typeInto", "click", "scrollTo", "checkCheckbox", "checkRadioButton",
                             "selectOptionByValue", "selectOptionByIndex", "enter", "focusElement", "submitForm", "waitForElement"]

                  },
                  "data": {
                    "description": "Data associated with the action (e.g., value for 'set_value', or null if not applicable).",
                    "oneOf": [
                      { "type": "string" },
                      { "type": "number" },
                      { "type": "boolean" },
                      { "type": "null" },
                      { "type": "array" },
                      { "type": "object" }
                    ]
                  }
                },
                "additionalProperties": False
              },
              "minItems": 0
            },
            "parameters": {
              "type": "object",
              "description": "A JSON object containing parameters that might be required by actions in the plan (e.g., values to prompt user for if missing).",
              "patternProperties": {
                "^[a-zA-Z_][a-zA-Z0-9_]*$": {
                  "description": "Value for a specific parameter.",
                  "oneOf": [
                    { "type": "string" },
                    { "type": "number" },
                    { "type": "boolean" },
                    { "type": "array" },
                    { "type": "object" },
                    { "type": "null" }
                  ]
                }
              },
              "additionalProperties": True, # Allow other properties not explicitly listed
              "minProperties": 0
            }
          },
          "additionalProperties": False
        },
        "speak": {
          "type": "string",
          "description": "An optional string containing text for the AI to speak."
        }
      },
      "additionalProperties": False
    }
  },
  "additionalProperties": False
}

def validate_ai_response(data: dict) -> bool:
    """
    Validates a given JSON object against the AI response schema.

    Args:
        data: The JSON object (as a Python dictionary) to validate.

    Returns:
        True if the data is valid, False otherwise. Prints validation errors if invalid.
    """
    try:
        validate(instance=data, schema=ai_response_schema)
        logger.info("Validation successful: Data conforms to the schema.")
        return True
    except ValidationError as e:
        logger.error(f"Validation Error: {e.message}")
        logger.info(f"Path: {list(e.path)}")
        logger.info(f"Validator: {e.validator} with value {e.validator_value}")
        return False
    except json.JSONDecodeError as e:
        logger.error(f"JSON Decode Error: Input is not a valid JSON object. {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during validation: {e}")
        return False
