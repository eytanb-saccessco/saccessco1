// content.js
const micButton = document.createElement("button");
micButton.id = "floating-mic-button";
micButton.classList.add("mic-inactive"); // Initial style (e.g., closed state)
// micButton.textContent = "🎤"; Initial icon for "closed" state
micButton.textContent = "💬"; // Changed to speech bubble for "hidden" state
document.body.appendChild(micButton);

// This ID is generated once when the extension is first loaded into the page.
// It's used for the WebSocket connection to identify the conversation.
window.conversation_id = crypto.randomUUID();

// Flag to ensure initial setup (WebSocket, change observer) runs only once.
let initialSetupDone = false;
// Flag to track the visibility state of the chat container.
let chatVisible = false;

// Add an event listener to the floating microphone button.
micButton.addEventListener("click", () => {
  window.speechModule.setUp();
  console.log("--DEBUG--: speech setUp called");
  window.chatModule.initializeChatArea();
  console.log("--DEBUG--: chat initializeChatArea called")
  // Get a reference to the chat container element.
  const chatContainer = document.getElementById('saccessco-chat-container');

  if (!chatContainer) {
    console.error("Chat container not found! Cannot toggle visibility.");
    return; // Exit if the chat container isn't in the DOM.
  }

  if (!chatVisible) {
    // If the chat is currently hidden, show it.
    chatContainer.style.display = 'block';
    micButton.textContent = "✖"; // Change button icon to indicate "open" or "close" action.
    chatVisible = true; // Update the visibility state.

    // Perform initial setup (WebSocket connection, change observer) only on the very first time
    // the chat container is made visible.
    if (!initialSetupDone) {
      try {
        console.log("Initial extension setup triggered. Conversation ID:", window.conversation_id);

        // Call setup functions from other modules.
        // Assuming 'changeObserver' module handles DOM observation.
        // The .then() is added to suppress unhandled promise rejection warnings in the console
        // if setupChangeObserver is an async function.
        if (window.changeObserver && typeof window.changeObserver.setupChangeObserver === 'function') {
            window.changeObserver.setupChangeObserver().then(() => console.log("Change observer setup complete."));
        } else {
            console.warn("changeObserver module or setupChangeObserver function not available.");
        }

        // Assuming 'websocket' module handles WebSocket initialization.
        if (window.websocket && typeof window.websocket.initializeAIWebSocket === 'function') {
            window.websocket.initializeAIWebSocket();
            console.log("AI WebSocket initialized.");
        } else {
            console.warn("websocket module or initializeAIWebSocket function not available.");
        }

        // Add a welcoming message to the chat if the chatModule is available.
        if (window.chatModule && typeof window.chatModule.addMessage === 'function') {
            window.chatModule.addMessage("Saccessco", "Welcome! The extension is now loaded.");
            window.speechModule.speak("Wellcome, this is Saccesco, How may I help you?")
        } else {
            console.warn("chatModule or addMessage function not available to send welcome message.");
        }

        initialSetupDone = true; // Mark initial setup as complete.

      } catch (error) {
        console.error("Error during initial extension setup:", error);
        // Display an error message in the chat if possible.
        if (window.chatModule && typeof window.chatModule.addMessage === 'function') {
            window.chatModule.addMessage("Saccessco", `Error loading extension: ${error.message || "Unknown error"}`);
        }
      }
    }
  } else {
    // If the chat is currently visible, hide it.
    chatContainer.style.display = 'none';
    micButton.textContent = "🎤"; // Revert button icon to "closed" state.
    chatVisible = false; // Update the visibility state.
  }
});

// --- REMOVED SPEECH-RELATED LOGIC ---
// The 'startListening' and 'stopListening' functions have been removed from this script.
// The button in content.js no longer directly controls speech recognition.
// Any speech listening or speaking functionality will now need to be initiated and managed
// by other modules (e.g., chat_module.js, speech.js) from within the visible chat interface.

// Removed direct assignment of window.speechModule.timeoutCallback and event listeners
// related to speech recognition 'end' events, as content.js is no longer responsible
// for managing the speech recognition state or button icon based on it.

console.log("Content script injected. Floating button now toggles extension (chat) visibility.");