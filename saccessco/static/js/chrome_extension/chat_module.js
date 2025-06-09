// chat_module.js

(function(window) {
  const chatContainerId = 'saccessco-chat-container';
  const chatInputId = 'saccessco-chat-input';
  const chatButtonId = 'saccessco-chat-button';
  const micButtonId = 'saccessco-mic-button';
  const resizeHandleId = 'saccessco-chat-resize-handle';
  const chatMessagesId = 'saccessco-chat-messages';

  let chatContainer = null;
  let chatMessagesDiv = null;
  let chatInput = null;
  let sendButton = null;
  let micButton = null;
  let resizeHandle = null;
  let pendingConfirmationResolver = null;
  let isDragging = false;
  let dragOffsetX, dragOffsetY;
  let isResizing = false;
  let resizeStartX, resizeStartY, initialWidth, initialHeight;
  let isListening = false; // Internal state for chat_module's mic button

  // Define chatModule functions
  function initializeChatArea() {
    // Only create elements if they don't already exist
    if (document.getElementById(chatContainerId)) {
      chatContainer = document.getElementById(chatContainerId);
      chatMessagesDiv = document.getElementById(chatMessagesId);
      chatInput = document.getElementById(chatInputId);
      sendButton = document.getElementById(chatButtonId);
      micButton = document.getElementById(micButtonId);
      resizeHandle = document.getElementById(resizeHandleId);
      attachEventListeners(); // Re-attach listeners in case of re-initialization
      return;
    }

    // Create main chat container
    chatContainer = document.createElement('div');
    chatContainer.id = chatContainerId;
    chatContainer.style.position = 'fixed';
    chatContainer.style.bottom = '80px';
    chatContainer.style.left = '20px';
    chatContainer.style.zIndex = '10001';
    chatContainer.style.width = '300px';
    chatContainer.style.height = '300px';
    chatContainer.style.border = '1px solid #ccc';
    chatContainer.style.backgroundColor = '#f9f9f9';
    chatContainer.style.padding = '10px';
    chatContainer.style.fontFamily = 'Arial, sans-serif';
    chatContainer.style.fontSize = '14px';
    chatContainer.style.cursor = 'grab';
    chatContainer.style.display = 'flex';
    chatContainer.style.flexDirection = 'column';
    chatContainer.style.borderRadius = '8px'; // Added rounded corners

    // Chat messages display area
    chatMessagesDiv = document.createElement('div');
    chatMessagesDiv.id = chatMessagesId;
    chatMessagesDiv.style.flexGrow = '1';
    chatMessagesDiv.style.overflowY = 'auto';
    chatMessagesDiv.style.marginBottom = '10px';
    chatMessagesDiv.style.paddingRight = '5px'; // Prevent scrollbar overlap with content
    chatContainer.appendChild(chatMessagesDiv);

    // Resize handle
    resizeHandle = document.createElement('div');
    resizeHandle.id = resizeHandleId;
    resizeHandle.style.position = 'absolute';
    resizeHandle.style.bottom = '0';
    resizeHandle.style.right = '0';
    resizeHandle.style.width = '15px';
    resizeHandle.style.height = '15px';
    resizeHandle.style.backgroundColor = '#ddd';
    resizeHandle.style.border = '1px solid #ccc';
    resizeHandle.style.cursor = 'nwse-resize';
    resizeHandle.style.borderRadius = '0 0 8px 0'; // Match container corners
    chatContainer.appendChild(resizeHandle);

    // Input area container (flex for alignment)
    const inputArea = document.createElement('div');
    inputArea.style.display = 'flex';
    inputArea.style.alignItems = 'center';

    // Chat input field
    chatInput = document.createElement('input');
    chatInput.type = 'text';
    chatInput.id = chatInputId;
    chatInput.style.flexGrow = '1';
    chatInput.style.padding = '8px';
    chatInput.style.border = '1px solid #ddd';
    chatInput.style.borderRadius = '4px';
    chatInput.style.marginRight = '5px'; // Spacing for buttons

    // Microphone button
    micButton = document.createElement('button');
    micButton.id = micButtonId;
    micButton.innerHTML = '🎤'; // Default icon
    micButton.title = 'Toggle speech input';
    micButton.style.padding = '8px 12px';
    micButton.style.border = 'none'; // No border for cleaner look
    micButton.style.backgroundColor = '#007bff'; // Blue for active state
    micButton.style.color = 'white';
    micButton.style.borderRadius = '4px';
    micButton.style.cursor = 'pointer';
    micButton.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)'; // Added shadow
    micButton.style.transition = 'background-color 0.2s, transform 0.1s'; // Smooth transitions
    micButton.addEventListener('mousedown', (e) => e.target.style.transform = 'scale(0.95)');
    micButton.addEventListener('mouseup', (e) => e.target.style.transform = 'scale(1)');
    micButton.addEventListener('mouseleave', (e) => e.target.style.transform = 'scale(1)');


    // Send button
    sendButton = document.createElement('button');
    sendButton.id = chatButtonId;
    sendButton.textContent = 'Send';
    sendButton.style.padding = '8px 12px';
    sendButton.style.marginLeft = '5px';
    sendButton.style.border = 'none';
    sendButton.style.backgroundColor = '#28a745'; // Green for send
    sendButton.style.color = 'white';
    sendButton.style.borderRadius = '4px';
    sendButton.style.cursor = 'pointer';
    sendButton.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)'; // Added shadow
    sendButton.style.transition = 'background-color 0.2s, transform 0.1s';
    sendButton.addEventListener('mousedown', (e) => e.target.style.transform = 'scale(0.95)');
    sendButton.addEventListener('mouseup', (e) => e.target.style.transform = 'scale(1)');
    sendButton.addEventListener('mouseleave', (e) => e.target.style.transform = 'scale(1)');


    inputArea.appendChild(chatInput);
    inputArea.appendChild(micButton); // Mic button added before send button
    inputArea.appendChild(sendButton);
    chatContainer.appendChild(inputArea);

    document.body.appendChild(chatContainer);

    attachEventListeners();
  }

  function attachEventListeners() {
    // Event listeners for dragging chat window
    if (chatContainer) {
      chatContainer.removeEventListener('mousedown', startDrag);
      chatContainer.addEventListener('mousedown', startDrag);
    }
    document.removeEventListener('mousemove', drag);
    document.removeEventListener('mouseup', endDrag);
    document.addEventListener('mousemove', drag);
    document.addEventListener('mouseup', endDrag);

    // Event listeners for resizing chat window
    if (resizeHandle) {
      resizeHandle.removeEventListener('mousedown', startResize);
      resizeHandle.addEventListener('mousedown', startResize);
    }
    document.removeEventListener('mousemove', resize);
    document.removeEventListener('mouseup', endResize);
    document.addEventListener('mousemove', resize);
    document.addEventListener('mouseup', endResize);

    // Event listeners for chat input and send button
    if (sendButton) {
      sendButton.removeEventListener('click', handleUserInput);
      sendButton.addEventListener('click', handleUserInput);
    }
    if (chatInput) {
      chatInput.removeEventListener('keypress', handleInputKeypress);
      chatInput.addEventListener('keypress', handleInputKeypress);
    }
    if (micButton) {
      micButton.removeEventListener('click', handleMicButtonClick);
      micButton.addEventListener('click', handleMicButtonClick);
    }
  }

  function handleInputKeypress(event) {
    if (event.key === 'Enter') {
      handleUserInput();
    }
  }

  /**
   * Sets the visual state of the microphone button and related input elements.
   * @param {boolean} listening - True if speech recognition is active, false otherwise.
   */
  function setMicButtonState(listening) {
    isListening = listening; // Update internal state
    if (micButton) {
      if (listening) {
        micButton.style.backgroundColor = '#dc3545'; // Red for recording
        micButton.style.color = 'white';
        micButton.textContent = '🔴'; // Recording icon
        micButton.disabled = false; // Keep mic button enabled to stop listening
        chatInput.disabled = true; // Disable text input
        sendButton.disabled = true; // Disable send button
      } else {
        micButton.style.backgroundColor = '#007bff'; // Blue for ready state
        micButton.style.color = 'white';
        micButton.textContent = '🎤'; // Microphone icon
        micButton.disabled = false;
        chatInput.disabled = false;
        sendButton.disabled = false;
      }
    }
  }

  /**
   * Handles the click event for the microphone button.
   * Toggles speech recognition on/off.
   */
  function handleMicButtonClick() {
    if (!window.speechModule || typeof window.speechModule.listen !== 'function' || typeof window.speechModule.stopListening !== 'function') {
      console.warn("ChatModule: window.speechModule or its listen/stopListening functions are not available.");
      addMessage('System', 'Speech input not available. Please check extension setup.');
      return;
    }

    if (isListening) {
      // If currently listening, stop listening
      console.log("ChatModule: Mic button clicked, stopping listening.");
      window.speechModule.stopListening();
      setMicButtonState(false); // Reset button state immediately
    } else {
      // If not listening, start listening
      console.log("ChatModule: Mic button clicked, starting listening.");
      setMicButtonState(true);
      addMessage('System', 'Listening...');

      // Call speechModule.listen with a callback for the transcript and a timeout callback
      window.speechModule.listen(
        (transcript) => {
          // This callback is executed when speech.js detects a final transcript
          console.log("ChatModule: Speech transcript received:", transcript);
          setMicButtonState(false); // Stop listening and reset button state

          if (transcript && transcript.length > 0) {
            chatInput.value = transcript; // Put transcribed text into input field
            handleUserInput(); // Treat it as if the user typed and pressed Send
          } else {
            addMessage('System', 'No clear speech detected.');
          }
        },
        () => {
          // This callback is executed if speech.js reports a timeout
          console.log("ChatModule: Speech listening timed out.");
          setMicButtonState(false); // Reset button state
          addMessage('System', 'Listening timed out. Please try again.');
        }
      );
    }
  }

  /**
   * Adds a new message to the chat display.
   * @param {string} sender - The sender of the message (e.g., "User", "Saccessco").
   * @param {string} message - The message content.
   */
  function addMessage(sender, message) {
    if (!chatMessagesDiv) {
      console.warn("Chat messages div not found when trying to add message. Initializing chat area.");
      initializeChatArea(); // Ensure chat area is initialized if addMessage is called too early
    }
    const messageDiv = document.createElement('div');
    messageDiv.textContent = `${sender}: ${message}`;
    // Basic styling for messages
    if (sender === 'User') {
        messageDiv.style.textAlign = 'right';
        messageDiv.style.backgroundColor = '#e0f7fa'; // Light blue for user
        messageDiv.style.margin = '5px 0 5px auto';
        messageDiv.style.padding = '8px';
        messageDiv.style.borderRadius = '10px 10px 0 10px';
        messageDiv.style.maxWidth = '80%';
    } else {
        messageDiv.style.textAlign = 'left';
        messageDiv.style.backgroundColor = '#fff3e0'; // Light orange for system
        messageDiv.style.margin = '5px auto 5px 0';
        messageDiv.style.padding = '8px';
        messageDiv.style.borderRadius = '10px 10px 10px 0';
        messageDiv.style.maxWidth = '80%';
    }
    chatMessagesDiv.appendChild(messageDiv);
    // Scroll to the bottom to show the newest message
    chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight;
  }

  /**
   * Handles user input from the text field or simulated from speech.
   * Dispatches a custom event for backend communication.
   */
  function handleUserInput() {
    if (chatInput && chatInput.value.trim() !== '') {
      const userMessage = chatInput.value.trim();
      addMessage('User', userMessage); // Display user message in chat
      chatInput.value = ''; // Clear input field

      if (pendingConfirmationResolver) {
        // If a confirmation is pending, resolve it
        const isConfirmed = userMessage.toLowerCase() === 'yes'; // Simplified check
        pendingConfirmationResolver(isConfirmed);
        pendingConfirmationResolver = null; // Clear resolver

        // Dispatch an event to notify other modules (if needed)
        const event = new CustomEvent('saccessco:confirmationResolved', {
          detail: {
            userMessage: userMessage,
            isConfirmed: isConfirmed
          }
        });
        document.dispatchEvent(event);

      } else {
        // Otherwise, send the general user prompt to the backend
        // Assuming backendCommunicatorModule exists and has sendUserPrompt
        if (window.backendCommunicatorModule && typeof window.backendCommunicatorModule.sendUserPrompt === 'function') {
            window.backendCommunicatorModule.sendUserPrompt(userMessage);
        } else {
            console.warn("backendCommunicatorModule or sendUserPrompt not available to send message.");
            addMessage('System', 'Backend communication module not ready.');
        }

        // Dispatch an event for user prompt submission
        const event = new CustomEvent('saccessco:userPromptSubmitted', {
          detail: {
            prompt: userMessage
          }
        });
        document.dispatchEvent(event);
      }
    }
  }

  /**
   * Prompts the user for a yes/no confirmation.
   * @param {string} prompt - The question to ask the user.
   * @returns {Promise<boolean|null>} Resolves with true for 'yes', false for 'no', null for timeout/unrecognized.
   */
  function askConfirmation(prompt) {
    return new Promise((resolve) => {
      // Store the resolver so handleUserInput can resolve it later
      pendingConfirmationResolver = resolve;
      // Display the prompt in the chat
      addMessage('Saccessco', prompt + " (Type 'yes' or 'no' or use mic)");
    });
  }

  // --- Drag and Resize functions ---
  function startDrag(e) {
    // Only drag if left mouse button is pressed and not on resize handle
    if (e.target === chatContainer && e.buttons === 1) {
      if (e.target.id === resizeHandleId) return; // Prevent drag on resize handle

      isDragging = true;
      // Calculate offset from mouse to element's top-left corner
      dragOffsetX = e.clientX - chatContainer.getBoundingClientRect().left;
      dragOffsetY = e.clientY - chatContainer.getBoundingClientRect().top;
      chatContainer.style.cursor = 'grabbing';
      e.preventDefault(); // Prevent default browser drag behavior
    }
  }

  function drag(e) {
    if (!isDragging) return;
    // Calculate new position based on mouse movement and initial offset
    let newLeft = e.clientX - dragOffsetX;
    let newTop = e.clientY - dragOffsetY;

    // Get viewport dimensions
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const chatWidth = chatContainer.offsetWidth;
    const chatHeight = chatContainer.offsetHeight;

    // Constrain position within viewport boundaries
    if (newLeft < 0) newLeft = 0;
    if (newTop < 0) newTop = 0;
    if (newLeft + chatWidth > viewportWidth) newLeft = viewportWidth - chatWidth;
    if (newTop + chatHeight > viewportHeight) newTop = viewportHeight - chatHeight;

    // Apply new position
    chatContainer.style.left = newLeft + 'px';
    chatContainer.style.top = newTop + 'px';
    // Ensure bottom/right are auto if top/left are being set, for consistency
    chatContainer.style.bottom = 'auto';
    chatContainer.style.right = 'auto';
  }

  function endDrag() {
    if (!isDragging) return;
    isDragging = false;
    if (chatContainer) {
        chatContainer.style.cursor = 'grab'; // Revert cursor
    }
  }

  function startResize(e) {
    if (e.target.id === resizeHandleId && e.buttons === 1) {
      isResizing = true;
      resizeStartX = e.clientX;
      resizeStartY = e.clientY;
      initialWidth = chatContainer.offsetWidth;
      initialHeight = chatContainer.offsetHeight;
      chatContainer.style.cursor = 'nwse-resize';
      e.stopPropagation(); // Stop event propagation to prevent drag
    }
  }

  function resize(e) {
    if (!isResizing) return;
    const deltaX = e.clientX - resizeStartX;
    const deltaY = e.clientY - resizeStartY;

    const minWidth = 150;
    const minHeight = 100;
    const maxWidth = window.innerWidth - chatContainer.getBoundingClientRect().left - 20; // 20px padding from right edge
    const maxHeight = window.innerHeight - chatContainer.getBoundingClientRect().top - 20; // 20px padding from bottom edge

    let newWidth = initialWidth + deltaX;
    let newHeight = initialHeight + deltaY;

    // Apply min/max constraints
    if (newWidth < minWidth) newWidth = minWidth;
    if (newHeight < minHeight) newHeight = minHeight;
    if (newWidth > maxWidth) newWidth = maxWidth;
    if (newHeight > maxHeight) newHeight = maxHeight;

    chatContainer.style.width = newWidth + 'px';
    chatContainer.style.height = newHeight + 'px';
  }

  function endResize() {
    if (!isResizing) return;
    isResizing = false;
    if (chatContainer) {
        chatContainer.style.cursor = 'grab'; // Revert cursor
    }
  }

  // Expose the module's functions globally
  window.chatModule = {
    initializeChatArea: initializeChatArea,
    addMessage: addMessage,
    askConfirmation: askConfirmation
  };

  // REMOVED: The automatic call to window.chatModule.initializeChatArea();
  // This module will now only define its API, and its UI will be initialized
  // explicitly by the tests or the main application (e.g., content.js) when needed.

  console.log("--DEBUG--: chatModule attached to window.");

})(window);
