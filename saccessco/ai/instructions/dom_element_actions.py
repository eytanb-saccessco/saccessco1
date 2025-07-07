ACTIONS = ["typeInto", "click", "focusElement", "scrollTo", "checkCheckbox", "checkRadioButton",
                             "selectOptionByValue", "selectOptionByIndex", "submitForm", "enter"]
DOM_ELEMENT_ACTIONS = """
Available DOM Element Actions:

1. typeInto: (Synonyms: enterValue, setValue)
Purpose: Types a given data string into an HTML <input>, <textarea>, or contenteditable element.
Usage (in plan): {"action": "typeInto", "selector": "#myInput", "data": "Some text"}

2. click:
Purpose: Simulates a click event on an element.
Usage (in plan): {"action": "click", "selector": "#myButton", "data": null}

3. scrollTo:
Purpose: Scrolls the element into the view of the browser window.
Usage (in plan): {"action": "scrollTo", "selector": "#sectionId", "data": null}

4. checkCheckbox:
Purpose: Sets the checked property of a checkbox element.
Usage (in plan): {"action": "checkCheckbox", "selector": "[name='myCheckbox']", "data": true} (or false to uncheck)

5. checkRadioButton:
Purpose: Sets the checked property of a radio button element.
Usage (in plan): {"action": "checkRadioButton", "selector": "[name='myRadio'][value='option1']", "data": true}

6. selectOptionByValue:
Purpose: Selects an option in a <select> element by its value attribute.
Usage (in plan): {"action": "selectOptionByValue", "selector": "#mySelect", "data": "optionValue"}

7. selectOptionByIndex:
Purpose: Selects an option in a <select> element by its index.
Usage (in plan): {"action": "selectOptionByIndex", "selector": "#mySelect", "data": 2} (for the third option, as index is 0-based)

8. enter:
Purpose: Simulates an "Enter" keypress on an element.
Usage (in plan): {"action": "enter", "selector": "#searchField", "data": null}

9. focusElement:
Purpose: Sets focus on the specified element.
Usage (in plan): {"action": "focusElement", "selector": "#myInput", "data": null}

10. submitForm:
Purpose: Dispatches a submit event on a form, or on a button/input within a form.
Usage (in plan): {"action": "submitForm", "selector": "#myForm", "data": null} (or {"selector": "#submitButton", "data": null} if the button is within the form)
"""