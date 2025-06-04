// saccessco/static/js/chrome_extension/page_manipulator.js - Executes specific actions on the web page.
// Part of the AI's response in the User Prompt Flow.

(function(window) {

    /**
     * Finds an HTML element using a CSS selector.
     * @param {string} selector - The CSS selector for the element.
     * @returns {HTMLElement|null} The found element or null if not found.
     */
    function findElement(selector) {
        if (!selector) {
            console.error("PageManipulator: findElement called with undefined or null selector.");
            return null;
        }
        const element = document.querySelector(selector);
        if (!element) {
            console.warn(`PageManipulator: Element with selector "${selector}" not found.`);
        }
        return element;
    }

    /**
     * Types a given value into an input field or contenteditable element.
     * @param {string} selector - The CSS selector for the input element.
     * @param {string} value - The value to type.
     * @returns {Object} An object with success status and an error message if applicable.
     */
    function type(selector, value) {
        const element = findElement(selector);
        if (!element) {
            return { success: false, error: `Element with selector "${selector}" not found for 'type' action.` };
        }

        if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
            element.value = value;
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
            console.log(`PageManipulator: Typed "${value}" into "${selector}".`);
            return { success: true };
        } else if (element.isContentEditable) {
            element.textContent = value;
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
            console.log(`PageManipulator: Set content of editable element "${selector}" to "${value}".`);
            return { success: true };
        } else {
            return { success: false, error: `Element "${selector}" is not an input, textarea, or contenteditable for 'type' action.` };
        }
    }

    /**
     * Clicks an HTML element.
     * @param {string} selector - The CSS selector for the element to click.
     * @returns {Object} An object with success status and an error message if applicable.
     */
    function click(selector) {
        const element = findElement(selector);
        if (!element) {
            return { success: false, error: `Element with selector "${selector}" not found for 'click' action.` };
        }
        try {
            element.click();
            console.log(`PageManipulator: Clicked element "${selector}".`);
            return { success: true };
        } catch (e) {
            return { success: false, error: `Error clicking element "${selector}": ${e.message}` };
        }
    }

    /**
     * Scrolls an element or the window into view.
     * @param {string} selector - The CSS selector for the element to scroll to.
     * @param {string} behavior - 'auto', 'smooth', or 'instant'.
     * @returns {Object} An object with success status and an error message if applicable.
     */
    function scrollToElement(selector, behavior = 'smooth') {
        const element = findElement(selector);
        if (!element) {
            return { success: false, error: `Element with selector "${selector}" not found for 'scroll_to' action.` };
        }
        try {
            element.scrollIntoView({ behavior: behavior, block: 'center' });
            console.log(`PageManipulator: Scrolled to element "${selector}" with behavior "${behavior}".`);
            return { success: true };
        } catch (e) {
            return { success: false, error: `Error scrolling to element "${selector}": ${e.message}` };
        }
    }

    /**
     * Checks/unchecks a checkbox.
     * @param {string} selector - The CSS selector for the checkbox.
     * @param {boolean} checked - True to check, false to uncheck.
     * @returns {Object} An object with success status and an error message if applicable.
     */
    function checkCheckbox(selector, checked) {
        const element = findElement(selector);
        if (!element || element.type !== 'checkbox') {
            return { success: false, error: `Element "${selector}" is not a checkbox or not found.` };
        }
        try {
            element.checked = checked;
            element.dispatchEvent(new Event('change', { bubbles: true }));
            console.log(`PageManipulator: ${checked ? 'Checked' : 'Unchecked'} checkbox "${selector}".`);
            return { success: true };
        } catch (e) {
            return { success: false, error: `Error checking checkbox "${selector}": ${e.message}` };
        }
    }

    /**
     * Selects a radio button.
     * @param {string} selector - The CSS selector for the radio button.
     * @returns {Object} An object with success status and an error message if applicable.
     */
    function checkRadioButton(selector) {
        const element = findElement(selector);
        if (!element || element.type !== 'radio') {
            return { success: false, error: `Element "${selector}" is not a radio button or not found.` };
        }
        try {
            element.checked = true;
            element.dispatchEvent(new Event('change', { bubbles: true }));
            console.log(`PageManipulator: Checked radio button "${selector}".`);
            return { success: true };
        } catch (e) {
            return { success: false, error: `Error checking radio button "${selector}": ${e.message}` };
        }
    }

    /**
     * Selects an option in a <select> element by value.
     * @param {string} selector - The CSS selector for the <select> element.
     * @param {string} value - The value of the option to select.
     * @returns {Object} An object with success status and an error message if applicable.
     */
    function selectOptionByValue(selector, value) {
        const selectElement = findElement(selector);
        if (!selectElement || selectElement.tagName !== 'SELECT') {
            return { success: false, error: `Element "${selector}" is not a select element or not found.` };
        }
        try {
            selectElement.value = value;
            selectElement.dispatchEvent(new Event('change', { bubbles: true }));
            console.log(`PageManipulator: Selected option with value "${value}" in "${selector}".`);
            return { success: true };
        } catch (e) {
            return { success: false, error: `Error selecting option by value in "${selector}": ${e.message}` };
        }
    }

    /**
     * Selects an option in a <select> element by index.
     * @param {string} selector - The CSS selector for the <select> element.
     * @param {number} index - The index of the option to select.
     * @returns {Object} An object with success status and an error message if applicable.
     */
    function selectOptionByIndex(selector, index) {
        const selectElement = findElement(selector);
        if (!selectElement || selectElement.tagName !== 'SELECT') {
            return { success: false, error: `Element "${selector}" is not a select element or not found.` };
        }
        if (index < 0 || index >= selectElement.options.length) {
            return { success: false, error: `Index "${index}" out of bounds for select element "${selector}".` };
        }
        try {
            selectElement.selectedIndex = index;
            selectElement.dispatchEvent(new Event('change', { bubbles: true }));
            console.log(`PageManipulator: Selected option at index "${index}" in "${selector}".`);
            return { success: true };
        } catch (e) {
            return { success: false, error: `Error selecting option by index in "${selector}": ${e.message}` };
        }
    }

    /**
     * Simulates pressing the Enter key on an element.
     * @param {string} selector - The CSS selector for the element.
     * @returns {Object} An object with success status and an error message if applicable.
     */
    function simulateEnter(selector) {
        const element = findElement(selector);
        if (!element) {
            return { success: false, error: `Element with selector "${selector}" not found for 'simulate_enter' action.` };
        }
        try {
            const event = new KeyboardEvent('keypress', {
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true,
                cancelable: true
            });
            element.dispatchEvent(event);
            console.log(`PageManipulator: Simulated Enter keypress on "${selector}".`);
            return { success: true };
        } catch (e) {
            return { success: false, error: `Error simulating Enter on "${selector}": ${e.message}` };
        }
    }

    /**
     * Focuses on an element.
     * @param {string} selector - The CSS selector for the element to focus.
     * @returns {Object} An object with success status and an error message if applicable.
     */
    function focusElement(selector) {
        const element = findElement(selector);
        if (!element) {
            return { success: false, error: `Element with selector "${selector}" not found for 'focus' action.` };
        }
        if (typeof element.focus === 'function') {
            element.focus();
            console.log(`PageManipulator: Focused on element "${selector}".`);
            return { success: true };
        } else {
            return { success: false, error: `Element "${selector}" cannot be focused.` };
        }
    }

    /**
     * Submits a form or a button within a form.
     * @param {string} selector - The CSS selector for the form or a button/input within a form.
     * @returns {Object} An object with success status and an error message if applicable.
     */
    function submitForm(selector) {
        let element = findElement(selector);
        let formElement = null;

        if (!element) {
            return { success: false, error: `Element with selector "${selector}" not found for 'submit_form' action.` };
        }

        if (element.tagName === 'FORM') {
            formElement = element;
        } else if (element.form) { // If it's an input/button inside a form
            formElement = element.form;
        }

        if (!formElement) {
            return { success: false, error: `No form found to submit for selector "${selector}".` };
        }

        try {
            // Dispatch a submit event. The HTML's onsubmit handler should prevent default.
            const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
            const defaultPrevented = !formElement.dispatchEvent(submitEvent);

            if (defaultPrevented) {
                console.log(`PageManipulator: Form submit event dispatched and default prevented for selector "${selector}".`);
                return { success: true };
            } else {
                // If the default was not prevented, it means the form might actually submit.
                console.warn(`PageManipulator: Form submit event for "${selector}" was not prevented by handler. Actual submission may occur.`);
                return { success: true };
            }
        } catch (e) {
            return { success: false, error: `Error dispatching submit event for selector "${selector}": ${e.message}` };
        }
    }

    /**
     * Executes a plan of actions on the page.
     * This is called by websocket.js as part of the AI's 'execute' command.
     * @param {Array<Object>} plan - An array of action objects.
     * Each object should have at least 'action' (e.g., 'type', 'click')
     * and 'selector'. Other properties like 'value' are action-specific.
     * @returns {Promise<Object>} A promise that resolves with an object containing
     * an overall status ('completed' or 'failed') and an array of individual action results.
     */
    async function executePlan(plan) {
        const individualActionResults = [];
        let overallStatus = "completed"; // Assume success unless an action fails

        try {
            if (!Array.isArray(plan)) {
                console.error("PageManipulator: executePlan received a non-array plan:", plan);
                return {
                    status: "failed",
                    results: [{ success: false, error: "Invalid plan: not an array." }]
                };
            }

            for (const action of plan) {
                let actionResult = { success: true, error: '' }; // Initialize as success for each action
                const currentSelector = action.selector || action.element;

                console.log("PageManipulator: Executing action:", action);

                // Handle sensitive/user input first, before attempting the action
                if (action.is_sensitive || action.from_user_input) {
                    if (!window.chatModule || typeof window.chatModule.askConfirmation !== 'function') {
                        actionResult = { success: false, error: "chatModule.askConfirmation is not available for sensitive/user input." };
                    } else {
                        const confirmationPrompt = action.is_sensitive ?
                            `This action involves sensitive data (e.g., password). Do you want to proceed?` :
                            `Please provide the value for ${currentSelector}:`;

                        const confirmationResponse = await window.chatModule.askConfirmation(confirmationPrompt);

                        if (action.is_sensitive) {
                            if (confirmationResponse === false) { // Explicitly check for false for denial
                                actionResult = { success: false, error: "Confirmation denied for sensitive input." };
                            } else {
                                // If confirmed (true or any other truthy value), proceed with the original action
                                console.log("PageManipulator: Sensitive input confirmed. Proceeding with action.");
                            }
                        } else if (action.from_user_input) {
                            if (typeof confirmationResponse === 'string' && confirmationResponse.length > 0) {
                                action.data = confirmationResponse; // Update action data with user's input
                                console.log(`PageManipulator: User provided input for ${currentSelector}: "${confirmationResponse}".`);
                            } else {
                                actionResult = { success: false, error: "User input not provided or invalid." };
                            }
                        }
                    }
                }

                // Only proceed with the actual action if the previous step (confirmation/user input) was successful
                if (actionResult.success) { // Check if actionResult is still successful
                    try {
                        switch (action.action) {
                            case 'type':
                            case 'enter_value':
                                actionResult = type(currentSelector, action.value || action.data);
                                break;
                            case 'click':
                                actionResult = click(currentSelector);
                                break;
                            case 'scroll_to':
                                actionResult = scrollToElement(currentSelector, action.behavior);
                                break;
                            case 'check_checkbox':
                                actionResult = checkCheckbox(currentSelector, action.checked);
                                break;
                            case 'check_radio':
                                actionResult = checkRadioButton(currentSelector);
                                break;
                            case 'select_option_by_value':
                                actionResult = selectOptionByValue(currentSelector, action.value);
                                break;
                            case 'select_option_by_index':
                                actionResult = selectOptionByIndex(currentSelector, action.index);
                                break;
                            case 'simulate_enter':
                                actionResult = simulateEnter(currentSelector);
                                break;
                            case 'focus':
                                actionResult = focusElement(currentSelector);
                                break;
                            case 'submit_form':
                                actionResult = submitForm(currentSelector);
                                break;
                            default:
                                actionResult = { success: false, error: `Unknown action type: ${action.action}` };
                                console.warn(actionResult.error);
                                break;
                        }
                    } catch (e) {
                        actionResult = { success: false, error: `Error executing action ${action.action} on ${currentSelector}: ${e.message}` };
                        console.error(actionResult.error, e);
                    }
                }

                individualActionResults.push({
                    action: action.action,
                    selector: currentSelector,
                    value: action.value || action.data,
                    success: actionResult.success,
                    error: actionResult.error
                });

                if (!actionResult.success) {
                    overallStatus = "failed"; // If any action fails, the whole plan fails
                }

                // Add a small delay between actions to allow page to react
                if (action.delay && typeof action.delay === 'number') {
                    await new Promise(resolve => setTimeout(resolve, action.delay));
                } else {
                    await new Promise(resolve => setTimeout(resolve, 50)); // Default small delay
                }
            }
            console.log("PageManipulator: Plan execution finished. Overall status:", overallStatus, "Results:", individualActionResults);
            return {
                status: overallStatus,
                results: individualActionResults
            };
        } catch (topLevelError) {
            console.error("PageManipulator: Top-level error during plan execution:", topLevelError);
            return {
                status: "failed",
                results: individualActionResults.length > 0 ? individualActionResults : [{ success: false, error: `Top-level execution error: ${topLevelError.message}` }]
            };
        }
    }

    // Expose functions to the global window object
    window.pageManipulatorModule = {
        executePlan,
        // Expose individual functions for testing/mocking purposes if needed
        findElement,
        type,
        click,
        scrollToElement,
        checkCheckbox,
        checkRadioButton,
        selectOptionByValue,
        selectOptionByIndex,
        simulateEnter,
        focusElement,
        submitForm
    };

    console.log("Page Manipulator module loaded.");

})(window);
