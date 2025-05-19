// backend_communicator.js
/**
 * Sends data to the backend and handles the initial response.
 * Expects the backend response to be:
 * { "status": "accepted", "task_id": "<the_id>" }
 * Then calls the pollTaskResult function to poll for the final result.
 *
 * @param {string} url - The backend endpoint URL.
 * @param {Object} data - The JSON payload to send.
 */

async function send(url, data) {
  if (!data) {
    console.log("No data provided. Aborting send.");
    return;
  }

  if(window.configuration.DEBUG) {
    window.speechModule.speak("Sending: " + JSON.stringify(data) + " to: " + url);
  }
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });

    let result = await response.json();  // Await the parsed JSON object
    if (result.status !== "success") {
      console.log("Error send result: " + JSON.stringify(result));
    }
    return result;
  } catch (error) {
    console.error("Error sending data:", error);
  }
}


async function sendUserPrompt(text) {
    let result = await send(window.configuration.SACCESSCO_USER_PROMPT_URL, {'text': text});
    return result;
}

async function sendPageChange(url, html) {
    let result = await send(window.configuration.SACCESSCO_PAGE_CHANGE_URL, {'url': url, 'html': html});
    return result;
}


// Expose functions globally.
window.backendCommunicatorModule = {
    sendUserPrompt,
    sendPageChange,
    getConversationId,
    removeConversationId
};