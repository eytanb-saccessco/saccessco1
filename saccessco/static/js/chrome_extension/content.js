// content.js
const micButton = document.createElement("button");
micButton.id = "floating-mic-button";
micButton.classList.add("mic-inactive"); // Initial style
micButton.textContent = "🎤";
document.body.appendChild(micButton);

let isListening = false;
let initialSetupDone = false;
let chatVisible = false; // Track chat visibility

micButton.addEventListener("click", () => {
  const chatContainer = document.getElementById('saccessco-chat-container');

  if (!initialSetupDone) {
    try {
      window.backendCommunicatorModule.getConversationId().then((conversationId) => {
        console.log("Old conversation id is: " + conversationId);
      });
      window.backendCommunicatorModule.removeConversationId();
      console.log("Conversation id removed");
      window.changeObserver.setupChangeObserver();
      console.log("Initial setup done and backend notified with location.");
      window.chatModule.addMessage("Saccessco", "Ready to listen."); // Use chat module
      window.speechModule.speak("Saccessco is ready to listen.");
      if (chatContainer) {
        chatContainer.style.display = 'block'; // Show chat on first click
        chatVisible = true;
      }
      initialSetupDone = true;
      startListening(); // Start listening immediately after first click
    } catch (error) {
      console.error("Initial setup error:");
      window.speechModule.speak("Saccessco encountered an issue during setup.");
      window.chatModule.addMessage("Saccessco", "Encountered an issue during setup, error: " + error); // Use chat module
    }
  } else {
    // Toggle listening on subsequent clicks
    if (!isListening) {
      startListening();
    } else {
      stopListening();
    }
  }

  // Ensure chat remains open after the first click
  if (chatContainer && !chatVisible) {
    chatContainer.style.display = 'block';
    chatVisible = true;
  }
});

function startListening() {
  if (!isListening) {
    isListening = true;
    micButton.classList.remove("mic-inactive");
    micButton.classList.add("mic-active");
    micButton.textContent = "👂"; // Change icon to indicate listening
    window.speechModule.listen((userSaid) => {
      console.log("User said: " + userSaid);
      window.chatModule.addMessage("User", userSaid); // Display user speech in chat
      window.backendCommunicatorModule.sendUserPrompt(userSaid);
      window.speechModule.speak(`User said: ${userSaid}`);
      stopListening(); // Stop listening after processing a statement
    });
  }
}

function stopListening() {
  if (isListening) {
    isListening = false;
    window.speechModule.stopListening();
    micButton.classList.remove("mic-active");
    micButton.classList.add("mic-inactive");
    micButton.textContent = "🎤"; // Revert icon
  }
}
// Set the timeout callback to update the button style on timeout
if (window.speechModule) {
  window.speechModule.timeoutCallback = stopListening;
} else {
  console.warn("Speech module not immediately available to set timeout callback.");
  setTimeout(() => {
    if (window.speechModule) {
      window.speechModule.timeoutCallback = stopListening;
    }
  }, 100); // Try after a short delay
}
// Attach a listener to the speech module's onend event to update the button state on timeout
//if (window.speechModule && window.speechModule.recognition) {
//  window.speechModule.recognition.addEventListener('end', () => {
//    // This listener will be called when speech recognition stops for any reason,
//    // including the timeout in speech.js or an explicit stopListening() call.
//    // We only need to update the button state if we were actively listening.
//    if (isListening) {
//      stopListening();
//    }
//  });
//} else {
//  console.warn("Speech recognition object not immediately available to attach 'end' listener.");
//  setTimeout(() => {
//    if (window.speechModule && window.speechModule.recognition && isListening) {
//      window.speechModule.recognition.addEventListener('end', () => {
//        stopListening();
//      });
//    }
//  }, 1000);
//}
console.log("Content script injected.");