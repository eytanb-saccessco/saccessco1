// saccessco/static/js/chrome_extension/page_manipulator.js - Executes specific actions on the web page.
// Part of the AI's response in the User Prompt Flow.

(function(window) {

  class parameterManager {
    /**
     * Initializes the ParameterManager with an optional JSON object of initial parameters.
     * @param {object} [initialParams={}] - An optional JSON object containing
     * initial key-value pairs for parameters.
     */
    constructor(initialParams = {}) {
      if (typeof initialParams !== 'object' || initialParams === null) {
        console.warn("ParameterManager: initialParams provided is not a valid object. Initializing with empty parameters.");
        this._parameters = {};
      } else {
        this._parameters = { ...initialParams };
      }
      console.log("ParameterManager initialized with parameters:", this._parameters);
    }

    /**
     * Retrieves the value for a given parameter key.
     * If the key exists in the initialized parameters and its value is not null/undefined,
     * it returns that value. Otherwise, it calls `window.speechModule.askUserInput`
     * to prompt the user for the value.
     *
     * @param {string} key - The name of the parameter to retrieve.
     * @param {string} [promptMessage] - Optional. The message to display to the user if prompting is needed.
     * Defaults to "Please provide the value for [key]".
     * @param {boolean} [isSensitive=false] - Optional. Indicates if the user's input is sensitive
     * (e.g., password), which might affect how `askUserInput` handles it (e.g., masked input).
     * @returns {Promise<any|null>} A Promise that resolves with the parameter's value,
     * or `null` if the parameter is not found and the user cancels/does not provide input,
     * or if `window.speechModule.askUserInput` is not available.
     */
    async get(key, promptMessage, isSensitive = false) {
      if (key == null || key === 'undefined')  {
          return null;
      }

      if (key in this._parameters) {
        console.log(`ParameterManager: Found '${key}' in internal parameters.`);
        return this._parameters[key];
      }

      console.log(`ParameterManager: '${key}' not found or is null/undefined. Attempting to prompt user.`);

      if (!window.speechModule || typeof window.speechModule.askUserInput !== 'function') {
        console.error(`ParameterManager: window.speechModule.askUserInput is not available. Cannot prompt user for '${key}'.`);
        return null;
      }

      try {
        const defaultPrompt = `Please provide the value for ${key}:`;
        const finalPromptMessage = promptMessage || defaultPrompt;

        const userInput = await window.speechModule.askUserInput(finalPromptMessage, isSensitive);

        if (userInput === null || typeof userInput === 'undefined' || (typeof userInput === 'string' && userInput.trim() === '')) {
          const cancellationMessage = `Input for '${key}' was not provided or cancelled. Action may be incomplete.`;
          console.warn(`ParameterManager: ${cancellationMessage}`); // Log the warning
          // --- FIX: Add message to chat module on cancellation ---
          if (window.chatModule && typeof window.chatModule.addMessage === 'function') {
              window.chatModule.addMessage("Saccessco", cancellationMessage);
          }
          // ----------------------------------------------------
          return null; // User cancelled or provided no input
        } else {
          console.log(`ParameterManager: User provided input for '${key}'. Storing it for future reference.`);
          this._parameters[key] = userInput;
          return userInput;
        }
      } catch (error) {
        console.error(`ParameterManager: Error while prompting user for '${key}':`, error);
        // Also send an error message to chat if the prompt itself failed
        if (window.chatModule && typeof window.chatModule.addMessage === 'function') {
            window.chatModule.addMessage("Saccessco", `Error retrieving input for '${key}': ${error.message || 'Unknown error.'}`);
        }
        return null;
      }
    }

    /**
     * Sets a parameter's value directly.
     * @param {string} key - The name of the parameter to set.
     * @param {any} value - The value to set for the parameter.
     */
    set(key, value) {
      this._parameters[key] = value;
      console.log(`ParameterManager: Parameter '${key}' set to:`, value);
    }

    /**
     * Returns a copy of all current parameters managed by the instance.
     * @returns {object} A shallow copy of the internal parameters object.
     */
    getAll() {
      return { ...this._parameters };
    }
  }

  // --- Mock window.speechModule.askUserInput for demonstration/testing ---
  if (!window.speechModule || typeof window.speechModule.askUserInput !== 'function') {
    window.speechModule = window.speechModule || {};
    window.speechModule.askUserInput = async (message, sensitive = false) => {
      console.log(`(MOCK) SpeechModule asked for input: "${message}" (Sensitive: ${sensitive})`);
      return new Promise(resolve => {
        const mockInput = prompt(`(MOCK UI) ${message}\n(Type 'null' to simulate no input/cancel)`);
        if (mockInput === 'null') {
          resolve(null);
        } else {
          resolve(mockInput);
        }
      });
    };
    console.log("Mock window.speechModule.askUserInput initialized for demonstration.");
  }

    const pageManipulator = {

        /**
         * Finds an HTML element using a CSS selector, scrolls it into view,
         * and waits until it is visible and interactive, or a timeout occurs.
         * This is an internal helper function.
         *
         * @param {string} selector - The CSS selector for the element.
         * @param {number} [timeoutMs=10000] - Maximum time to wait for the element to be visible in milliseconds.
         * @param {number} [checkIntervalMs=100] - How often to check for the element's visibility in milliseconds.
         * @returns {Promise<HTMLElement|null>} A Promise that resolves with the found and visible element,
         * or `null` if the timeout is reached or the selector is invalid.
         */
        _findElementAndAssertVisible: async (selector, timeoutMs = 10000, checkIntervalMs = 100) => {
            if (!selector || typeof selector !== 'string') {
                console.error("PageManipulator: _findElementAndAssertVisible called with invalid or null selector.");
                if (window.chatModule && typeof window.chatModule.addMessage === 'function') {
                    window.chatModule.addMessage("Saccessco", `Error finding element: Invalid selector provided.`);
                }
                return null;
            }

            console.log("Checking if date selector: " + selector);
            if(window.skyscannerDates.isDateSelector(selector)) {
                return window.skyscannerDates.scrollToDate(selector);
            }
            console.log("Selector: " + selector + " Not date!");

            const startTime = Date.now();

            return new Promise(resolve => {
                const intervalId = setInterval(async () => { // Made async to await scrollIntoView and setTimeout
                    const element = document.querySelector(selector);

                    if (element) {
                        // Scroll the element into view first
                        // Using 'center' block for better visibility, 'nearest' for inline
                        element.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' });
                        // Add a small delay to allow the scroll to complete and render
                        await new Promise(r => setTimeout(r, 100)); // Wait 100ms after scrolling

                        // Check for visibility
                        const style = window.getComputedStyle(element);
                        const isVisible = element.offsetWidth > 0 &&
                                          element.offsetHeight > 0 &&
                                          style.display !== 'none' &&
                                          style.visibility !== 'hidden' &&
                                          parseFloat(style.opacity) > 0;

                        if (isVisible) {
                            clearInterval(intervalId);
                            const duration = Date.now() - startTime;
                            console.log(`PageManipulator: _findElementAndAssertVisible found and element "${selector}" visible in ${duration}ms.`);
                            window.debug.message(`Element "${selector}" found and visible in ${duration}ms.`);
                            resolve(element);
                            return;
                        }
                    }

                    if (Date.now() - startTime >= timeoutMs) {
                        clearInterval(intervalId);
                        const errorMsg = `PageManipulator: _findElementAndAssertVisible timed out waiting for element "${selector}" to be visible after ${timeoutMs}ms.`;
                        console.warn(errorMsg);
                        if (window.chatModule && typeof window.chatModule.addMessage === 'function') {
                            window.chatModule.addMessage("Saccessco", `Element not found or visible: ${selector}.`);
                        }
                        resolve(null);
                    }
                }, checkIntervalMs);
            });
        },

        // Public action methods

        /**
         * Waits for a given DOM element (identified by selector) to become visible and interactive,
         * or until a timeout occurs. This function is designed to be used as an action in the plan.
         *
         * @param {string} selector - The CSS selector for the element to wait for.
         * @param {null} data - This parameter is always null for this action.
         * @returns {Promise<{success: boolean, error?: string}>} A Promise that resolves with a success status,
         * or rejects if the timeout is reached.
         */
        waitForElement: async (selector, data) => {
            try {
                // This function already uses _findElementAndAssertVisible internally,
                // which now includes scrolling.
                const element = await pageManipulator._findElementAndAssertVisible(selector);
                if (element) {
                    console.log(`PageManipulator: Successfully waited for element "${selector}".`);
                    return { success: true };
                } else {
                    return { success: false, error: `waitForElement: Element "${selector}" not found or visible after timeout.` };
                }
            } catch (e) {
                return { success: false, error: `waitForElement: Error during wait for element "${selector}": ${e.message}` };
            }
        },

        typeInto: (element, data) => {
            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                element.value = data
                element.dispatchEvent(new Event('input', {bubbles: true}));
                element.dispatchEvent(new Event('change', {bubbles: true}));
                console.log(`PageManipulator: Typed "${data}" into "${element}".`);
                return {success: true};
            } else if (element.isContentEditable) {
                element.textContent = data;
                element.dispatchEvent(new Event('input', {bubbles: true}));
                element.dispatchEvent(new Event('change', {bubbles: true}));
                console.log(`PageManipulator: Set content of editable element "${element}" to "${data}".`);
                return {success: true};
            } else {
                return {
                    success: false,
                    error: `Element "${element}" is not an input, textarea, or contenteditable for 'type' action.`
                };
            }
        },

        enterValue: this.typeInto,
        setValue: this.typeInto,

        click: (element, data) => {
            try {
                element.click();
                console.log(`PageManipulator: Clicked element "${element}".`);
                return {success: true};
            } catch (e) {
                return {success: false, error: `Error clicking element "${element}": ${e.message}`};
            }
        },

        scrollTo: (element, data) => {
            try {
                // This action explicitly scrolls to an element.
                // The _findElementAndAssertVisible already ensures elements are in view for other actions.
                element.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' });
                console.log(`PageManipulator: Scrolled to element "${element}"`);
                return {success: true};
            } catch (e) {
                return {success: false, error: `Error scrolling to element "${element}": ${e.message}`};
            }
        },

        checkCheckbox: (element, data = true) => {
            if (!element || element.type !== 'checkbox') {
                return {success: false, error: `Element is not a checkbox or not found.`};
            }
            try {
                element.checked = data;
                element.dispatchEvent(new Event('change', {bubbles: true}));
                console.log(`PageManipulator: ${data ? 'Checked' : 'Unchecked'} checkbox "${element}".`);
                return {success: true};
            } catch (e) {
                return {success: false, error: `Error checking checkbox "${element}": ${e.message}`};
            }
        },

        checkRadioButton: (element, data = true) => {
            if (!element || element.type !== 'radio') {
                return {success: false, error: `Element is not a radio button or not found.`};
            }
            try {
                element.checked = data;
                element.dispatchEvent(new Event('change', {bubbles: true}));
                console.log(`PageManipulator: Checked radio button "${element}".`);
                return {success: true};
            } catch (e) {
                return {success: false, error: `Error checking radio button "${element}": ${e.message}`};
            }
        },

        selectOptionByValue: (element, data) => {
            if (!element || element.tagName !== 'SELECT') {
                return {success: false, error: `Element "${element}" is not a select element or not found.`};
            }
            try {
                element.value = data;
                element.dispatchEvent(new Event('change', {bubbles: true}));
                console.log(`PageManipulator: Selected option with value "${data}" in "${element}".`);
                return {success: true};
            } catch (e) {
                return {success: false, error: `Error selecting option by value in "${element}": ${e.message}`};
            }
        },

        selectOptionByIndex: (element, data) => {
            if (!element || element.tagName !== 'SELECT') {
                return {success: false, error: `Element "${element}" is not a select element or not found.`};
            }
            const index = parseInt(data);
            if (isNaN(index) || index < 0 || index >= element.options.length) {
                return {success: false, error: `Index "${data}" is invalid or out of bounds for select element "${element}".`};
            }
            try {
                element.selectedIndex = index;
                element.dispatchEvent(new Event('change', {bubbles: true}));
                console.log(`PageManipulator: Selected option at index "${index}" in "${element}".`);
                return {success: true};
            } catch (e) {
                return {success: false, error: `Error selecting option by index in "${element}": ${e.message}`};
            }
        },

        enter: (element, data) => {
            if (!element) {
                return {
                    success: false,
                    error: `Element not found for 'enter' action.`
                };
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
                console.log(`PageManipulator: Simulated Enter keypress on "${element}".`);
                return {success: true};
            } catch (e) {
                return {success: false, error: `Error simulating Enter on "${element}": ${e.message}`};
            }
        },

        focusElement: (element, data) => {
            if (!element) {
                return {success: false, error: `Element not found for 'focusElement' action.`};
            }
            if (typeof element.focus === 'function') {
                element.focus();
                console.log(`PageManipulator: Focused on element "${element}".`);
                return {success: true};
            } else {
                return {success: false, error: `Element "${element}" cannot be focused.`};
            }
        },

        submitForm: (element, data) => {
            let formElement = null;

            if (element.tagName === 'FORM') {
                formElement = element;
            } else if (element.form) {
                formElement = element.form;
            }

            if (!formElement) {
                return {success: false, error: `No form found to submit for element "${element}".`};
            }

            try {
                const submitEvent = new Event('submit', {bubbles: true, cancelable: true});
                const defaultPrevented = !formElement.dispatchEvent(submitEvent);

                if (defaultPrevented) {
                    console.log(`PageManipulator: Form submit event dispatched and default prevented for form "${formElement}".`);
                    return {success: true};
                } else {
                    console.warn(`PageManipulator: Form submit event for "${formElement}" was not prevented by handler. Actual submission may occur.`);
                    return {success: true};
                }
            } catch (e) {
                return {
                    success: false,
                    error: `Error dispatching submit event for form "${formElement}": ${e.message}`
                };
            }
        },

        async executePlan(plan, parameters){
            window.debug.message("Executing Plan: " + JSON.stringify(plan) + " with parameters: " + JSON.stringify(parameters))
            const individualActionResults = [];
            let overallStatus = "completed";

            try {
                if (!Array.isArray(plan)) {
                    console.error("PageManipulator: executePlan received a non-array plan:", plan);
                    return {
                        status: "failed",
                        results: [{success: false, error: "Invalid plan: not an array."}]
                    };
                }
                const params = new parameterManager(parameters);

                for (const step of plan) {
                    let actionResult = {success: true, error: ''};
                    let element = null;
                    let data = null;

                    console.log("PageManipulator: Executing action:", step.action, "on selector:", step.selector);

                    // For 'waitForElement' action, we only need to wait for the element
                    // The _findElementAndAssertVisible function now includes scrolling and waiting.
                    // So, for all actions, we first call _findElementAndAssertVisible.
                    element = await this._findElementAndAssertVisible(step.selector);
                    if (!element) {
                        actionResult = { success: false, error: `Element "${step.selector}" not found or visible after timeout for action "${step.action}".` };
                    } else {
                        // Only get data if it's needed for the action
                        if (step.data !== null && step.data !== undefined) {
                            data = await params.get(step.data);
                        }

                        const actionFunction = this[step.action];
                        if (typeof actionFunction === 'function') {
                            window.debug.message("Going to execute: " + step.action + " on: " + step.selector +" with data: " + data);
                            // Pass the found element directly to the action function
                            actionResult = actionFunction(element, data);
                        } else {
                            actionResult = { success: false, error: `Unknown action: ${step.action}` };
                        }
                    }

                    window.debug.message("Step: action: " + step.action + ", selector: " + step.selector + ", data: " + data + ", result: " + JSON.stringify(actionResult));

                    individualActionResults.push({
                        action: step.action,
                        selector: step.selector,
                        value: data,
                        success: actionResult.success,
                        error: actionResult.error
                    });

                    if (!actionResult.success) {
                        overallStatus = "failed";
                        window.debug.message("Failed plan step: " + JSON.stringify(individualActionResults.at(-1)));
                        break;
                    }

                    // Add a small delay between actions to allow page to react
                    if (actionResult.success) {
                        await new Promise(resolve => setTimeout(resolve, 50));
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
                    results: individualActionResults.length > 0 ? individualActionResults : [{
                        success: false,
                        error: `Top-level execution error: ${topLevelError.message}`
                    }]
                };
            }
        },
    }

    // Expose functions to the global window object
    window.pageManipulatorModule = pageManipulator;

    console.log("Page Manipulator module loaded.");

})(window);
