// saccessco/static/js/chrome_extension/backend_communicator.js

/**
 * Sends data to the backend and handles the initial response.
 * Expects the backend response to be JSON.
 *
 * @param {string} url - The backend endpoint URL.
 * @param {Object} data - The JSON payload to send.
 * @returns {Promise<Object|undefined>} A promise that resolves with the parsed JSON response
 * from the backend, or undefined if an error occurs.
 */
async function send(url, data) {
  if (!data) {
    console.error("ERROR: No data provided to send function. Aborting send.");
    return undefined; // Return undefined or null consistently on failure
  }

  // Robust check for window.configuration, DEBUG, and window.speechModule.speak
  console.log("INFO: Sending data:", data, "to URL:", url);
  if(window.configuration && window.configuration.DEBUG && window.speechModule && typeof window.speechModule.speak === 'function') {
      try {
          window.speechModule.speak("Sending: " + JSON.stringify(data) + " to: " + url);
      } catch (e) {
          console.error("ERROR: Error calling speechModule.speak:", e);
      }
  }

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });

    // Check if the HTTP response itself was successful (e.g., status 200-299)
    if (!response.ok) {
        console.error(`ERROR: HTTP error! status: ${response.status} for URL: ${url}`);
        // Attempt to parse JSON error body if available
        try {
            const errorBody = await response.json(); // Await the JSON parsing
            console.error("ERROR: Backend returned error body:", errorBody);
            return errorBody; // Return the error details from the backend
        } catch (jsonError) {
            console.error("ERROR: Could not parse error response as JSON:", jsonError, "Response text:", await response.text());
            return { error: `HTTP Error: ${response.status}`, details: response.statusText };
        }
    }

    // Await the JSON parsing of the successful response body
    let result = await response.json(); // <--- AWAIT the promise here
    console.log("INFO: Received successful response:", result);

    // Assuming your backend JSON response includes a 'status' key
    // if (result && result.status !== "success") {
    //   console.warn("WARNING: Backend response status is not 'success':", result);
    //   // You might want to handle non-success statuses differently
    // }

    return result; // Return the parsed JSON data

  } catch (error) {
    // This catch block handles network errors (e.g., server unreachable)
    // or errors thrown during the fetch process before a response is received.
    console.error("CRITICAL ERROR: Error sending data or receiving response (network/fetch error):", error);
    // Return undefined or a specific error object on fetch/network errors
    return undefined; // Or { error: "Network or Fetch error", details: error.message };
  }
}


/**
 * Sends a user prompt to the backend.
 * @param {string} text - The user's text prompt.
 * @returns {Promise<Object|undefined>} Promise resolving with backend response data.
 */
async function sendUserPrompt(text) {
    console.log("INFO: Sending user prompt:", text);
    // Ensure the payload structure matches what your Django UserPromptSerializer expects
    const payload = {
        'conversation_id': window.conversation_id, // ADDED: Ensure conversation_id is included
        'prompt': text,
    };
    console.log("DEBUG: sendUserPrompt payload:", payload);
    return await send(window.configuration.SACCESSCO_USER_PROMPT_URL, payload);
}

/**
 * Sends page change data to the backend.
 * @param {string} html - The HTML content of the page change.
 * @returns {Promise<Object|undefined>} Promise resolving with backend response data.
 */
async function sendPageChange(html) {
    console.log("INFO: Sending page change HTML length: " + html.length);
    // Ensure the payload structure matches what your Django PageChangeSerializer expects
    const payload = {
        'conversation_id' : window.conversation_id, // ADDED: Ensure conversation_id is included
        'html' : html
    };
    console.log("DEBUG: sendPageChange payload:", payload);
    return await send(window.configuration.SACCESSCO_PAGE_CHANGE_URL, payload);
}


// Expose functions globally.
window.backendCommunicatorModule = {
    send, // Expose the base send function if needed
    sendUserPrompt,
    sendPageChange,
};
