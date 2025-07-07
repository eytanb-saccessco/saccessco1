# from saccessco.ai.instructions.dom_element_actions import DOM_ELEMENT_ACTIONS
#
# PAGE_INSTRUCTIONS = (
#     "# Page Change Instructions\n\n"
#     "* When receiving a page change html\n"
#     "** ensure to:\n"
#     "1. Prioritize core, universal functionalities: Search, navigation, login/logout, primary content consumption (like playing a video), and content creation (uploading) will be explicitly looked for.\n"
#     "2. Thoroughly analyze interactive elements: I will pay closer attention to common input fields, buttons, and links that suggest primary user actions.\n"
#     "3. Cross-reference with common web patterns: I will use my knowledge of typical website layouts and functionalities to ensure no obvious user interaction is missed.\n"
#     "Please create:\n"
#     "1. Description for all different functions a user can use the page for.\n"
#     "2. For each function available to end user of the page:\n"
#     "2.1 Create a dom manipulation plan consisted of:\n"
#     "2.2.1 A list of manipulation steps. Each step should be a json object with the following keys:\n"
#     "2.2.2.2 'action' - with a value - the name of one of the DOM Element Actions described in:\n"
#     f"\t{DOM_ELEMENT_ACTIONS}\n"
#     "2.2.2.3 'selector' - A CSS selector for an interactive element visible on the page\n"
#     "2.2.2.4 'data' - A name for a parameter to be used in the action, if needed otherwise null.\n "
#     "Produce a response with:\n"
#     "1. A list of all functions available for end user interacting with the current page.\n"
#     "1.1 For each function add a description that can be used to explain the function to an end user\n"
#     "1.2 For each function add the dom manipulation plan\n"
#     "The response will be added to the conversation history. To be used by you when responding to USER PRMPT\n"
# )

PAGE_INSTRUCTIONS = """
# Page Analysis and Automation Plan Request

**Objective:** Analyze the provided HTML content to identify all significant end-user functionalities and generate corresponding DOM manipulation plans for automation.

**Input:**
* The complete HTML content of a web page.
* (Optional, but recommended for specific scenarios) A specific complex user goal (e.g., "Log in to the site," "Add item to cart," "Filter products by price"). If provided, prioritize this goal and break it down into steps.

**Output Requirements:**

For each distinct function or complex usage scenario identified on the page (from an end-user perspective), please create the following:

1.  **Function Description:**
    * A concise, user-friendly description of what the end-user can achieve with this function.

2.  **DOM Manipulation Plan:**
    * A JSON object with the following structure:
        ```json
        {
          "execute": {
            "plan": [
              // List of manipulation steps
            ],
            "parameters": {
              // Key-value pairs for parameters used in the plan
            }
          },
          "speak": "A brief verbal confirmation/description of the action."
        }
        ```
    * **`plan`**: A list (array) of JSON objects, where each object represents a single manipulation step. Each step *must* conform to the following structure:
        ```json
        {
          "action": "{name_of_action}",
          "selector": "{css_selector_string}",
          "data": "{parameter_name_string_or_null}"
        }
        ```
        * **`action`**: The name of one of the **Available DOM Element Actions** listed below.
        * **`selector`**: A CSS selector string that precisely targets the interactive element visible on the page.
        * ** The selector should be based on: 
        * ** 1. aria-label, 
        * ** 2. any attribute containing 'testid', 
        * ** 3. non-obfuscated id, 
        * ** 4. non-obfuscated class names
        * **
        * **`data`**:
            * If the action requires a dynamic value (e.g., text to type, a value to select), this should be a **string representing the name of a parameter** that will be provided at execution time (e.g., `"username"`, `"search_query"`).
            * If the action does not require dynamic data (e.g., a simple click, scrolling), this should be `null`.

    * **`parameters`**: A JSON object containing key-value pairs. Each key *must* correspond to a `data` parameter name used in the `plan`. The value should be a **placeholder string or example value** that clearly indicates what kind of data is expected for that parameter (e.g., `"your_username_here"`, `"Bohemian Rhapsody by Queen"`).

**Available DOM Element Actions (and their usage in `plan` steps):**

1.  **`typeInto`**:
    * **Purpose:** Types a given data string into an HTML `<input>`, `<textarea>`, or `contenteditable` element.
    * **Usage:** `{"action": "typeInto", "selector": "#myInput", "data": "parameter_for_text_input"}`

2.  **`click`**:
    * **Purpose:** Simulates a click event on an element.
    * **Usage:** `{"action": "click", "selector": "#myButton", "data": null}`

3.  **`scrollTo`**:
    * **Purpose:** Scrolls the element into the view of the browser window.
    * **Usage:** `{"action": "scrollTo", "selector": "#sectionId", "data": null}`

4.  **`checkCheckbox`**:
    * **Purpose:** Sets the `checked` property of a checkbox element.
    * **Usage:** `{"action": "checkCheckbox", "selector": "[name='myCheckbox']", "data": "parameter_for_boolean_value"}` (e.g., `true` or `false`)

5.  **`checkRadioButton`**:
    * **Purpose:** Sets the `checked` property of a radio button element.
    * **Usage:** `{"action": "checkRadioButton", "selector": "[name='myRadio'][value='option1']", "data": "parameter_for_boolean_value"}`

6.  **`selectOptionByValue`**:
    * **Purpose:** Selects an option in a `<select>` element by its `value` attribute.
    * **Usage:** `{"action": "selectOptionByValue", "selector": "#mySelect", "data": "parameter_for_option_value"}`

7.  **`selectOptionByIndex`**:
    * **Purpose:** Selects an option in a `<select>` element by its index (0-based).
    * **Usage:** `{"action": "selectOptionByIndex", "selector": "#mySelect", "data": "parameter_for_option_index"}` (e.g., `0`, `1`, `2`)

8.  **`enter`**:
    * **Purpose:** Simulates an "Enter" keypress on an element. Useful for submitting forms or triggering search after typing.
    * **Usage:** `{"action": "enter", "selector": "#searchField", "data": null}`

9.  **`focusElement`**:
    * **Purpose:** Sets focus on the specified element.
    * **Usage:** `{"action": "focusElement", "selector": "#myInput", "data": null}`

10. **`submitForm`**:
    * **Purpose:** Dispatches a submit event on a form, or on a button/input within a form.
    * **Usage:** `{"action": "submitForm", "selector": "#myForm", "data": null}`

**Complex Usage Scenarios to Automate (if applicable to the page):**

* **Navigation:** Moving between different sections or pages of the site.
* **Form Filling & Submission:** Completing multi-field forms.
* **Search & Filtering:** Performing searches and applying filters/sorts to results.
* **Interactive Widgets:** Interacting with date pickers, sliders, modals, etc.
* **Multi-step Processes:** Automating a sequence of actions that span multiple UI states or "pages" within a single tab.

**Response will be added to the conversation history. To be used by you when responding to USER PROMPT.**
"""