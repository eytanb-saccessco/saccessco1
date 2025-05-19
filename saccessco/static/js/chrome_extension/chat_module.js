// chat_module.js

(function(window) {
  const chatContainerId = 'saccessco-chat-container';
  const chatInputId = 'saccessco-chat-input';
  const chatButtonId = 'saccessco-chat-button';
  const resizeHandleId = 'saccessco-chat-resize-handle';

  let chatContainer = null;
  let pendingConfirmationResolver = null;
  let isDragging = false;
  let dragOffsetX, dragOffsetY;
  let isResizing = false;
  let resizeStartX, resizeStartY, initialWidth, initialHeight;

  function initializeChatArea() {
    if (document.getElementById(chatContainerId)) {
      chatContainer = document.getElementById(chatContainerId);
      return;
    }

    chatContainer = document.createElement('div');
    chatContainer.id = chatContainerId;
    chatContainer.style.position = 'fixed';
    chatContainer.bottom = '80px'; // Adjust as needed
    chatContainer.left = '20px';
    chatContainer.zIndex = '10001';
    chatContainer.width = '300px';
    chatContainer.height = '300px';
    chatContainer.border = '1px solid #ccc';
    chatContainer.backgroundColor = '#f9f9f9';
    chatContainer.overflowY = 'auto';
    chatContainer.padding = '10px';
    chatContainer.fontFamily = 'Arial, sans-serif';
    chatContainer.fontSize = '14px';
    chatContainer.style.cursor = 'grab'; // Indicate draggable

    // Create resize handle
    const resizeHandle = document.createElement('div');
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
    inputArea.style.marginTop = '10px';

    const input = document.createElement('input');
    input.type = 'text';
    input.id = chatInputId;
    input.style.flexGrow = '1';
    input.style.padding = '8px';
    input.style.border = '1px solid #ddd';
    input.style.borderRadius = '4px';

    const sendButton = document.createElement('button');
    sendButton.id = chatButtonId;
    sendButton.textContent = 'Send';
    sendButton.style.padding = '8px 12px';
    sendButton.style.marginLeft = '5px';
    sendButton.style.border = 'none';
    sendButton.style.backgroundColor = '#007bff';
    sendButton.style.color = 'white';
    sendButton.style.borderRadius = '4px';
    sendButton.style.cursor = 'pointer';

    sendButton.addEventListener('click', handleUserInput);
    input.addEventListener('keypress', (event) => {
      if (event.key === 'Enter') {
        handleUserInput();
      }
    });

    inputArea.appendChild(input);
    inputArea.appendChild(sendButton);
    chatContainer.appendChild(inputArea);

    document.body.appendChild(chatContainer);

    // Add event listeners for dragging and resizing
    chatContainer.addEventListener('mousedown', startDrag);
    document.addEventListener('mousemove', drag);
    document.addEventListener('mouseup', endDrag);

    resizeHandle.addEventListener('mousedown', startResize);
    document.addEventListener('mousemove', resize);
    document.addEventListener('mouseup', endResize);
  }

  function addMessage(sender, message) {
    if (!chatContainer) {
      initializeChatArea();
    }
    const messageDiv = document.createElement('div');
    messageDiv.textContent = `${sender}: ${message}`;
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight; // Scroll to bottom
  }

  function handleUserInput() {
    const inputElement = document.getElementById(chatInputId);
    if (inputElement && inputElement.value.trim() !== '') {
      const userMessage = inputElement.value.trim();
      addMessage('User', userMessage);
      inputElement.value = ''; // Clear the input
      if (pendingConfirmationResolver) {
        let resp =  pendingConfirmationResolver(userMessage === 'yes');
        pendingConfirmationResolver = null; // Reset the resolver
        return resp;
      } else {
        window.backendCommunicatorModule.sendUserPrompt(userMessage);
      }
    }
  }

  function askConfirmation(prompt) {
    return new Promise((resolve) => {
      addMessage('Saccessco', prompt + " (Type 'yes' or 'no' to respond)");
      pendingConfirmationResolver = resolve;
    });
  }

  function startDrag(e) {
    if (e.target === chatContainer) {
      isDragging = true;
      dragOffsetX = e.clientX - chatContainer.getBoundingClientRect().left;
      dragOffsetY = e.clientY - chatContainer.getBoundingClientRect().top;
      chatContainer.style.cursor = 'grabbing';
    }
  }

  function drag(e) {
    if (!isDragging) return;
    chatContainer.style.left = e.clientX - dragOffsetX + 'px';
    chatContainer.style.top = e.clientY - dragOffsetY + 'px';
    chatContainer.style.bottom = 'auto'; // Ensure bottom doesn't interfere
    chatContainer.style.right = 'auto';  // Ensure right doesn't interfere
  }

  function endDrag() {
    if (!isDragging) return;
    isDragging = false;
    chatContainer.style.cursor = 'grab';
  }

  function startResize(e) {
    isResizing = true;
    resizeStartX = e.clientX;
    resizeStartY = e.clientY;
    initialWidth = chatContainer.offsetWidth;
    initialHeight = chatContainer.offsetHeight;
    chatContainer.style.cursor = 'nwse-resize';
  }

  function resize(e) {
    if (!isResizing) return;
    const deltaX = e.clientX - resizeStartX;
    const deltaY = e.clientY - resizeStartY;
    chatContainer.style.width = initialWidth + deltaX + 'px';
    chatContainer.style.height = initialHeight + deltaY + 'px';
  }

  function endResize() {
    if (!isResizing) return;
    isResizing = false;
    chatContainer.style.cursor = 'grab';
  }

  // Expose the module's functions
  window.chatModule = {
    initializeChatArea,
    addMessage,
    askConfirmation
  };

  // Initialize the chat area on load (but keep it hidden initially)
  initializeChatArea();
  if (chatContainer) {
    chatContainer.style.display = 'none';
  }
})(window);