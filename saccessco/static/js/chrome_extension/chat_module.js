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
  let isListening = false;

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

    chatMessagesDiv = document.createElement('div');
    chatMessagesDiv.id = chatMessagesId;
    chatMessagesDiv.style.flexGrow = '1';
    chatMessagesDiv.style.overflowY = 'auto';
    chatMessagesDiv.style.marginBottom = '10px';
    chatContainer.appendChild(chatMessagesDiv);

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
    chatContainer.appendChild(resizeHandle);

    const inputArea = document.createElement('div');
    inputArea.style.display = 'flex';
    inputArea.style.alignItems = 'center';

    chatInput = document.createElement('input');
    chatInput.type = 'text';
    chatInput.id = chatInputId;
    chatInput.style.flexGrow = '1';
    chatInput.style.padding = '8px';
    chatInput.style.border = '1px solid #ddd';
    chatInput.style.borderRadius = '4px';

    sendButton = document.createElement('button');
    sendButton.id = chatButtonId;
    sendButton.textContent = 'Send';
    sendButton.style.padding = '8px 12px';
    sendButton.style.marginLeft = '5px';
    sendButton.style.border = 'none';
    sendButton.style.backgroundColor = '#007bff';
    sendButton.style.color = 'white';
    sendButton.style.borderRadius = '4px';
    sendButton.style.cursor = 'pointer';

    micButton = document.createElement('button');
    micButton.id = micButtonId;
    micButton.innerHTML = '🎤';
    micButton.title = 'Speak your message';
    micButton.style.padding = '8px 12px';
    micButton.style.marginLeft = '5px';
    micButton.style.border = '1px solid #ddd';
    micButton.style.backgroundColor = '#eee';
    micButton.style.color = '#333';
    micButton.style.borderRadius = '4px';
    micButton.style.cursor = 'pointer';

    inputArea.appendChild(chatInput);
    inputArea.appendChild(micButton);
    inputArea.appendChild(sendButton);
    chatContainer.appendChild(inputArea);

    document.body.appendChild(chatContainer);

    attachEventListeners();
  }

  function attachEventListeners() {
    if (chatContainer) {
        chatContainer.removeEventListener('mousedown', startDrag);
        chatContainer.addEventListener('mousedown', startDrag);
    }
    document.removeEventListener('mousemove', drag);
    document.removeEventListener('mouseup', endDrag);
    document.addEventListener('mousemove', drag);
    document.addEventListener('mouseup', endDrag);

    if (resizeHandle) {
        resizeHandle.removeEventListener('mousedown', startResize);
        resizeHandle.addEventListener('mousedown', startResize);
    }
    document.removeEventListener('mousemove', resize);
    document.removeEventListener('mouseup', endResize);
    document.addEventListener('mousemove', resize);
    document.addEventListener('mouseup', endResize);

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

  function setMicButtonState(listening) {
    isListening = listening;
    if (micButton) {
      if (listening) {
        micButton.style.backgroundColor = '#ffc107';
        micButton.style.color = 'black';
        micButton.textContent = '🔴';
        micButton.disabled = true;
        chatInput.disabled = true;
        sendButton.disabled = true;
      } else {
        micButton.style.backgroundColor = '#eee';
        micButton.style.color = '#333';
        micButton.innerHTML = '🎤';
        micButton.disabled = false;
        chatInput.disabled = false;
        sendButton.disabled = false;
      }
    }
  }

  async function handleMicButtonClick() {
    if (isListening) {
      console.log("ChatModule: Mic button clicked, already listening. Stopping.");
      if (window.speechModule && typeof window.speechModule.stopListening === 'function') {
        window.speechModule.stopListening();
      }
      setMicButtonState(false);
      return;
    }

    if (!window.speechModule || typeof window.speechModule.startListening !== 'function') {
      console.warn("ChatModule: window.speechModule.startListening is not available.");
      addMessage('System', 'Speech input not available.');
      return;
    }

    setMicButtonState(true);
    addMessage('System', 'Listening...');
    try {
      const transcript = await window.speechModule.startListening();
      setMicButtonState(false);

      if (transcript && transcript.length > 0) {
        chatInput.value = transcript;
        handleUserInput();
      } else {
        addMessage('System', 'No speech detected.');
      }
    } catch (error) {
      setMicButtonState(false);
      console.error("ChatModule: Speech recognition error:", error);
      addMessage('System', `Speech recognition error: ${error.message || error}`);
    }
  }

  function addMessage(sender, message) {
    if (!chatMessagesDiv) {
      // This path should ideally not be hit if initializeChatArea is called reliably
      // before addMessage, but as a safeguard.
      initializeChatArea();
    }
    const messageDiv = document.createElement('div');
    messageDiv.textContent = `${sender}: ${message}`;
    chatMessagesDiv.appendChild(messageDiv);
    chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight;
  }

  function handleUserInput() {
    if (chatInput && chatInput.value.trim() !== '') {
      const userMessage = chatInput.value.trim();
      addMessage('User', userMessage);
      chatInput.value = '';

      if (pendingConfirmationResolver) {
        const isConfirmed = userMessage.toLowerCase() === 'yes';
        pendingConfirmationResolver(isConfirmed);
        pendingConfirmationResolver = null;

        const event = new CustomEvent('saccessco:confirmationResolved', {
          detail: {
            userMessage: userMessage,
            isConfirmed: isConfirmed
          }
        });
        document.dispatchEvent(event);

      } else {
        const event = new CustomEvent('saccessco:userPromptSubmitted', {
          detail: {
            prompt: userMessage
          }
        });
        document.dispatchEvent(event);
      }
    }
  }

  function askConfirmation(prompt) {
    return new Promise((resolve) => {
      addMessage('Saccessco', prompt + " (Type 'yes' or 'no' or use mic)");
      pendingConfirmationResolver = resolve;
    });
  }

  // --- Drag and Resize functions ---
  function startDrag(e) {
    if (e.target === chatContainer && e.target.id !== resizeHandleId && e.buttons === 1) {
      isDragging = true;
      dragOffsetX = e.clientX - chatContainer.getBoundingClientRect().left;
      dragOffsetY = e.clientY - chatContainer.getBoundingClientRect().top;
      chatContainer.style.cursor = 'grabbing';
    }
  }

  function drag(e) {
    if (!isDragging) return;
    let newLeft = e.clientX - dragOffsetX;
    let newTop = e.clientY - dragOffsetY;

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const chatWidth = chatContainer.offsetWidth;
    const chatHeight = chatContainer.offsetHeight;

    if (newLeft < 0) newLeft = 0;
    if (newTop < 0) newTop = 0;
    if (newLeft + chatWidth > viewportWidth) newLeft = viewportWidth - chatWidth;
    if (newTop + chatHeight > viewportHeight) newTop = viewportHeight - chatHeight;

    chatContainer.style.left = newLeft + 'px';
    chatContainer.style.top = newTop + 'px';
    chatContainer.style.bottom = 'auto';
    chatContainer.style.right = 'auto';
  }

  function endDrag() {
    if (!isDragging) return;
    isDragging = false;
    if (chatContainer) {
        chatContainer.style.cursor = 'grab';
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
      e.stopPropagation();
    }
  }

  function resize(e) {
    if (!isResizing) return;
    const deltaX = e.clientX - resizeStartX;
    const deltaY = e.clientY - resizeStartY;

    const minWidth = 150;
    const minHeight = 100;

    const maxWidth = window.innerWidth - chatContainer.getBoundingClientRect().left - 20;
    const maxHeight = window.innerHeight - chatContainer.getBoundingClientRect().top - 20;

    let newWidth = initialWidth + deltaX;
    let newHeight = initialHeight + deltaY;

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
        chatContainer.style.cursor = 'grab';
    }
  }

  // Expose the module's functions
  window.chatModule = {
    initializeChatArea: initializeChatArea,
    addMessage: addMessage,
    askConfirmation: askConfirmation
  };

  // REMOVED: The automatic call to window.chatModule.initializeChatArea();
  // This module will now only define its API, and its UI will be initialized
  // explicitly by the tests or the main application when needed.

})(window);
