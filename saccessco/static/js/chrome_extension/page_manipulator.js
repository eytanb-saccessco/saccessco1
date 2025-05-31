// pageManipulator/__main__.js
const from_user = "<<from user>>";
const no_confirm = "no confirm";

function handleFocus(el) {
  console.log("handleFocus, el: ", el);
  el.focus();
}

function handleEnter(el) {
  const enterEvent = new KeyboardEvent("keydown", {
    key: "Enter",
    code: "Enter",
    bubbles: true,
    cancelable: true
  });
  el.dispatchEvent(enterEvent);
}

/**
 * Sets the element's value and dispatches an "Enter" key event.
 * @param {HTMLElement} el
 * @param {string} data
 */
function handleEnterValue(el, data) {
  el.value = data;
  el.click();
  handleEnter(el);
}

function handleClick(el) {
  el.click();
}

function handleSubmit(el) {
    let formElement;
    if (el.tagName.toLowerCase() === "form") {
        formElement = el;
    } else {
        // If the element is not a form, try to find its closest form.
        formElement = el.closest("form");
    }

    if (formElement) {
        console.log(`Attempting native form submission for form:`, formElement);
        formElement.submit(); // <-- THIS IS THE KEY CHANGE
    } else {
        throw new Error("No form found to submit.");
    }
}
function handleSelectOption(el, data) {
  const optionsArray = Array.from(el.options);
  // If data is numeric, treat it as an index.
  if (!isNaN(data)) {
    const idx = Number(data);
    if (idx >= 0 && idx < optionsArray.length) {
      el.selectedIndex = idx;
    } else {
      throw new Error("Invalid option index: " + idx);
    }
  } else {
    // First, try to match the option's value exactly (case-insensitive).
    let option = optionsArray.find(opt => opt.value.toLowerCase() === data.toLowerCase());
    if (!option) {
      // If no exact value match is found, try to match based on the option's text.
      const lowerData = data.toLowerCase();
      option = optionsArray.find(opt => {
        const optText = opt.text.toLowerCase();
        // Check if either string contains the other.
        return optText.includes(lowerData) || lowerData.includes(optText);
      });
    }
    if (option) {
      el.value = option.value;
    } else {
      throw new Error("Option not found for value: " + data);
    }
  }
}

function handleCheck(el, data) {
  // For both checkbox and radio button, setting .checked = true will select it.
  // You can enhance this if you need to handle a "false" value.
  if (data.toString().toLowerCase() === "true") {
    el.checked = true;
  } else {
    el.checked = false;
  }
}

// Dictionary mapping actions to handler functions.
const actionHandlers = {
  focus: handleFocus,
  enter_value: handleEnterValue,
  enter_date: handleEnterValue, // assuming similar behavior
  click: handleClick,
  submit: handleSubmit,
  select_option: handleSelectOption,
  check: handleCheck,
  simulate_enter: handleEnter
  // add additional handlers as needed.
};

/**
 * Processes a single command that describes a DOM manipulation.
 * @param {Object} command - Contains action, element (a CSS selector), and data.
 * @returns {Promise<{status: string, error?: string}>} - Returns an object with status and optional error.
 */
async function processCommand(command) {
  // console.log("--DEBUG--: Current HTML:\n" + document.documentElement.outerHTML + "\n");
  console.log("--DEBUG--: Processing command: " + JSON.stringify(command));
  const { action, element: selector, data } = command;
  try {
    const el = document.querySelector(selector);
    if (!el) {
      console.error("Element not found: " + selector)
      return { status: "error", error: "Element not found" };
    }
    let finalData = data;

    // Example: Handle input fields (you can expand this logic as needed)
    if (action === "enter_value" || action === "enter_date") {
      if (el.tagName.toLowerCase() === "input") {
        const inputType = (el.getAttribute("type") || "").toLowerCase();
        const nameAttr = (el.getAttribute("name") || "").toLowerCase();
        const sensitive = (inputType === "password") ||
          (nameAttr.includes("password")) ||
          (nameAttr.includes("user")) ||
          (nameAttr.includes("code"));
        if (sensitive && data === from_user) {
          window.chatModule.addMessage("Saccessco", "Warning: This field is security-sensitive. Your input may be overheard. Please ensure no one else is listening. Type 'proceed' to continue automatically.");
          const confirmResponse = await window.chatModule.askConfirmation("Proceed automatically?");
          if (!confirmResponse.toLowerCase().includes("proceed")) {
            return { status: "error", error: "User did not confirm sensitive input." };
          }
          window.chatModule.addMessage("Saccessco", "Please spell your input letter by letter in the chat, with spaces between each letter.");
          finalData = await window.chatModule.askConfirmation("Spell your input now:");
          finalData = finalData.replace(/\s+/g, "");
        } else if (typeof data === "string" && data === from_user) {
          window.chatModule.addMessage("Saccessco", "Please provide the input value in the chat.");
          finalData = await window.chatModule.askConfirmation("Enter the value:");
        }
      }
    }

    // If the action requires confirmation (like clicking or submitting on a button).
    // if (["click", "submit"].includes(action) &&
    //   (el.tagName.toLowerCase() === "button" || el.tagName.toLowerCase() === "form") &&
    //   data !== no_confirm) {
    //   console.log("Asking user confirmation");
    //   const confirmation = await askUserConfirmation("Do you want me to perform this action automatically? (Type 'yes' or 'no')");
    //   if (confirmation !== true) {
    //     return { status: "error", error: "User chose manual action or declined." };
    //   }
    // }

    // Execute the command by dispatching it to the appropriate handler.
    const handler = actionHandlers[action];
    if (typeof handler !== "function") {
      const errorMessage = "Unknown action: " + action;
      console.error(errorMessage);
      return { status: "error", error: errorMessage };
    }
    try {
      console.log("Using handler: " + handler + "On data: " + finalData);
      handler(el, finalData);
    } catch (handlerError) {
       const errorMessage = "Handler execution failed: " + handlerError.message;
        console.error(errorMessage);
        return {status: "error", error: errorMessage}
    }
    return { status: "ok" };
  } catch (err) {
    const errorMessage = "Error processing command: " + err.message;
    console.error(errorMessage);
    return { status: "error", error: errorMessage };
  }
}

/**
 * Executes a plan of commands.
 * @param {Array<Object>} plan - An array of command objects.
 * @returns {Promise<{status: string, last_step: number, error_message: null, step_statuses: *[]}>}
 */
async function executePlan(plan) {
  console.log("--DEBUG--: start execution of plan: " + JSON.stringify(plan));
  let planStatus = {
    status: "running",
    last_step: -1,
    error_message: null,
    step_statuses: []
  };

  for (let i = 0; i < plan.length; i++) {
    const command = plan[i];
    const stepResult = await processCommand(command);
    planStatus.last_step = i;
    planStatus.step_statuses.push(stepResult.status);

    if (stepResult.status === "error") {
      planStatus.status = "failed";
      planStatus.error_message = stepResult.error;
      return planStatus;
    }
  }

  planStatus.status = "completed";
  return planStatus;
}

function isNegative(response) {
  return response.toLowerCase().includes("no");
}

/**
 * Asks the user for confirmation using both chat and speech modules.
 * @param {string} prompt - The question to ask the user.
 * @returns {Promise<boolean | null>} - A Promise that resolves with:
 * - true if the user confirms.
 * - false if the user declines.
 * - null if no response is received within the timeout.
 */
async function askUserConfirmation(prompt) {
  return new Promise(async (resolve) => {
    let resolved = false; // Flag to ensure we resolve only once

    // Function to handle a 'yes'/'no' response and resolve the promise
    const handleResponse = (response) => {
      if (!resolved) {
        resolved = true;
        resolve(response); // Resolve with the boolean value
      }
    };

    // --- Chat Confirmation ---
    let chatPromise;
    if (window.chatModule && typeof window.chatModule.askConfirmation === 'function') {
      chatPromise = window.chatModule.askConfirmation(prompt);
      chatPromise.then((chatResponse) => {
        if (chatResponse === true || chatResponse === false) {
          handleResponse(chatResponse); // Resolve with the chat response
        }
      });
    } else {
      console.warn("Chat module's askConfirmation is not available.");
    }

    // --- Speech Confirmation ---
    let speechPromise;
    if (window.speechModule && typeof window.speechModule.askConfirmation === 'function') {
      speechPromise = window.speechModule.askConfirmation(prompt);
      speechPromise.then((speechResponse) => {
        if (speechResponse === true || speechResponse === false) {
          handleResponse(speechResponse); // Resolve with the speech response
        }
      });
    } else {
      console.warn("Speech module's askConfirmation is not available.");
    }

    // --- Timeout ---
    const timeoutId = setTimeout(() => {
      if (!resolved) {
        resolved = true;
        resolve(null); // Resolve with null to indicate no response
      }
    }, 15000); // Adjust timeout as needed (milliseconds)
  });
}

// Optionally expose a global object for the page manipulator module.
window.pageManipulatorModule = {
  // actionHandlers,
  executePlan,
  // processCommand,
  // askUserConfirmation
};
