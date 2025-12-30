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
        * ** 1. non-obfuscated id,
        * ** 2. aria-label
        * ** 2.1 When creating a selector for selecting a date in date picker control:
        * ** 2.1.1 use this pattern exactly for the CSS aria-label: "[aria-label*='<Month name> <Day of month>, <Year>']"
        * ** 2.1.2 Make sure that <Day of month> has no leading zeroes
        * ** 3. any attribute containing 'testid' that the element has,
        * ** 4. non-obfuscated class names
        * ** 5. when selecting an option in a dropdown, and the user provided info about the desired option, 
        Do not invent option labels. Only click options that actually exist in the DOM.
        Prefer “contains” matching (case-insensitive) over exact matches.
        Use these attribute sources in order of preference (whichever exists on the option items):
        aria-label → [aria-label*="<user input>" i]
        text content (fallback when attributes are absent)
        data-testid → [data-testid*="<user input>" i]
        value (only if present) → [value*="<user input>" i]
        If no option contains the user’s text, select the first visible option in the list.
        Skip non-option utilities (e.g. “Include nearby airports” toggles) if present.
        * ** 6. When the user asks to set origin or destination:      
        Open/focus the input
        Origin: click the origin control, then type:
        {"action":"click","selector":"#OriginButton, [id*='OriginButton'], [id*='Origin']","data":null}
        {"action":"typeInto","selector":"#originInput-input, [id*='originInput']","data":"origin_city"}
        Destination: click the destination control, then type:
        {"action":"click","selector":"#DestinationButton, [id*='DestinationButton'], [id*='Destination']","data":null}
        {"action":"typeInto","selector":"#destinationInput-input, [id*='destinationInput']","data":"destination_city"}
        Wait for the autosuggest menu
        (listbox appears under the input; ID is typically *Input-menu)
        {"action":"waitForElement","selector":"[id*='originInput-menu'], [id*='destinationInput-menu'], [role='listbox']","data":null}
        Choose the best-match option by “contains”; else choose first
        Preferred (aria-label contains, case-insensitive):
        {"action":"click","selector":"[id*='originInput-item'][aria-label*='{{origin_city}}' i], [role='option'][aria-label*='{{origin_city}}' i]","data":null}
        Fallbacks (try in order):
        
        {"action":"click","selector":"[id*='originInput-item'][data-testid*='{{origin_city}}' i], [role='option'][data-testid*='{{origin_city}}' i]","data":null}
        {"action":"click","selector":"[id*='originInput-item'][value*='{{origin_city}}' i], [role='option'][value*='{{origin_city}}' i]","data":null}
        
        
        Final fallback (always succeeds): click the first option
        
        {"action":"click","selector":"#originInput-item-0, [id^='originInput-item-'], [id*='originInput-menu'] [role='option']:first-child","data":null}
    
        Use the analogous selectors for destination (replace originInput → destinationInput).

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

11. **`waitForElement`**:
    * **Purpose:** Pauses execution until a specified element is visible and interactive. This is crucial for dynamically loaded content.
    * **Usage:** `{"action": "waitForElement", "selector": "#myDynamicElement", "data": null}`

**Complex Usage Scenarios to Automate (if applicable to the page):**

* **Navigation:** Moving between different sections or pages of the site.
* **Form Filling & Submission:** Completing multi-field forms.
* **Search & Filtering:** Performing searches and applying filters/sorts to results.
* **Interactive Widgets:** Interacting with date pickers, sliders, modals, etc.
* **Multi-step Processes:** Automating a sequence of actions that span multiple UI states or "pages" within a single tab.

**Response will be added to the conversation history. To be used by you when responding to USER PROMPT.**
"""