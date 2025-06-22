// dom_manipulator.js

(function(window) {
  /**
   * ParameterManager class.
   * Manages parameters, retrieving them from an initial JSON object
   * or by prompting the user via `window.speechModule.askUserInput` if missing.
   */
  class ParameterManager {
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
      if (key in this._parameters && this._parameters[key] !== null && typeof this._parameters[key] !== 'undefined') {
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

  window.ParameterManager = ParameterManager;
  console.log("ParameterManager class loaded and attached to window.ParameterManager.");


  /**
   * Executes a dynamic JavaScript script string with provided parameters.
   * The script string should be the *body* of an async function, which will receive
   * a `params` object (an instance of ParameterManager) as its context.
   *
   * @param {string} scriptBodyString - The JavaScript code as a string,
   * representing the *body* of the function to execute.
   * Example: "const val = await params.get('key'); console.log(val);"
   * @param {object} initialParameters - A JSON object containing initial parameters for the script.
   */
  async function executeDynamicDomScript(scriptBodyString, initialParameters) {
      try {
          console.log("DOMManipulator: Executing dynamic DOM script.");

          // Create an instance of ParameterManager for the script to use.
          const paramManager = new ParameterManager(initialParameters);

          // Construct the full function string to be created by new Function().
          // This ensures 'params' is a direct argument to the evaluated code.
          const fullFunctionCode = `
              return (async function(params) {
                  try {
                      // The scriptBodyString is executed here.
                      // 'params' (which is the paramManager instance) is available in this scope.
                      ${scriptBodyString}
                      console.log("DOMManipulator: Dynamic DOM script execution completed successfully.");
                  } catch (e) {
                      console.error("DOMManipulator: Error during dynamic DOM script execution:", e);
                      if (window.chatModule && typeof window.chatModule.addMessage === 'function') {
                          window.chatModule.addMessage("Saccessco", "Error processing action: " + (e.message || "Unknown error during script execution."));
                      }
                  }
              }); // The parentheses ensure this is a function expression being returned
          `;

          // Create the dynamic function. It will take `paramManager` as its argument.
          // The `new Function()` creates a new function whose body is `fullFunctionCode`.
          // When called, `fullFunctionCode` returns the async IIFE which then executes `scriptBodyString`.
          const dynamicFunctionWrapper = new Function('paramManagerArg', fullFunctionCode);

          // Execute the dynamically created wrapper function, passing the ParameterManager instance.
          // This wrapper returns the actual async function that contains your script logic,
          // which is then immediately awaited.
          await dynamicFunctionWrapper()(paramManager); // Call wrapper, then call its return value with paramManager

      } catch (error) {
          console.error("DOMManipulator: Failed to create or execute initial dynamic function:", error);
          if (window.chatModule && typeof window.chatModule.addMessage === 'function') {
            window.chatModule.addMessage("Saccessco", "Failed to run action: " + (error.message || "Unknown error creating script."));
          }
      }
  }

  // Expose the module's main function
  window.domManipulatorModule = {
      executeDynamicDomScript
  };

  console.log("dom_manipulator.js module loaded and attached to window.domManipulatorModule.");

})(window);
