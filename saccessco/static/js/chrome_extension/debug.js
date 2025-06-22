// debug_message.js

(function(window) {
  const DEBUG_MESSAGE_CONTAINER_ID = 'debug-message-modal-container';
  const DEBUG_MESSAGE_OVERLAY_ID = 'debug-message-modal-overlay';
  const DEBUG_MESSAGE_DIALOG_ID = 'debug-message-modal-dialog';
  const DEBUG_MESSAGE_CONTENT_ID = 'debug-message-modal-content';
  const DEBUG_MESSAGE_STACK_ID = 'debug-message-modal-stack';
  const DEBUG_MESSAGE_CLOSE_BUTTON_ID = 'debug-message-modal-close-button';

  /**
   * Creates and displays a modal dialog with a custom message and a stack trace.
   * This function is intended for debugging purposes.
   *
   * @param {string} msg - The message to display in the modal.
   */
  function message(msg) {
     if (!window.configuration.DEBUG) {
         return;
     }
    // Remove any existing modal to prevent duplicates
    const existingModal = document.getElementById(DEBUG_MESSAGE_CONTAINER_ID);
    if (existingModal) {
      existingModal.remove();
    }

    // Create the main container for the modal (overlay + dialog)
    const modalContainer = document.createElement('div');
    modalContainer.id = DEBUG_MESSAGE_CONTAINER_ID;
    modalContainer.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 99999; /* Ensure it's on top of everything */
    `;

    // Create the overlay (darkens the background)
    const overlay = document.createElement('div');
    overlay.id = DEBUG_MESSAGE_OVERLAY_ID;
    overlay.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0, 0, 0, 0.7); /* Semi-transparent black */
    `;

    // Create the dialog box itself
    const dialog = document.createElement('div');
    dialog.id = DEBUG_MESSAGE_DIALOG_ID;
    dialog.style.cssText = `
      background-color: #fff;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
      max-width: 90%;
      width: 500px; /* Max width for readability */
      max-height: 80%; /* Limit height for scrollability */
      overflow-y: auto; /* Enable scrolling for long content */
      position: relative;
      font-family: 'Inter', sans-serif; /* Use Inter font */
      font-size: 14px;
      display: flex;
      flex-direction: column;
    `;

    // Add a close button
    const closeButton = document.createElement('button');
    closeButton.id = DEBUG_MESSAGE_CLOSE_BUTTON_ID;
    closeButton.textContent = '✖';
    closeButton.style.cssText = `
      position: absolute;
      top: 10px;
      right: 10px;
      background: none;
      border: none;
      font-size: 20px;
      cursor: pointer;
      color: #777;
      border-radius: 50%; /* Make it round */
      width: 30px;
      height: 30px;
      display: flex;
      justify-content: center;
      align-items: center;
      transition: background-color 0.2s, color 0.2s;
    `;
    closeButton.onmouseover = () => closeButton.style.backgroundColor = '#f0f0f0';
    closeButton.onmouseout = () => closeButton.style.backgroundColor = 'transparent';
    closeButton.onclick = () => modalContainer.remove();

    // Add modal title
    const title = document.createElement('h3');
    title.textContent = 'Debug Message';
    title.style.cssText = `
      margin-top: 0;
      margin-bottom: 15px;
      color: #333;
      text-align: center;
      font-size: 18px;
    `;

    // Add the custom message content
    const messageContent = document.createElement('p');
    messageContent.id = DEBUG_MESSAGE_CONTENT_ID;
    messageContent.textContent = msg;
    messageContent.style.cssText = `
      margin-bottom: 20px;
      color: #555;
      line-height: 1.5;
      word-wrap: break-word; /* Ensure long messages wrap */
      white-space: pre-wrap; /* Preserve whitespace and breaks */
      flex-shrink: 0; /* Don't shrink message content if stack is long */
    `;

    // Generate the stack trace
    // Create a new Error object to capture the current stack trace without throwing it.
    const stackTrace = new Error().stack;

    // Display the stack trace in a <pre> element for pre-formatted text
    const stackTracePre = document.createElement('pre');
    stackTracePre.id = DEBUG_MESSAGE_STACK_ID;
    stackTracePre.textContent = stackTrace || "Stack trace not available.";
    stackTracePre.style.cssText = `
      background-color: #f8f8f8;
      border: 1px solid #eee;
      padding: 10px;
      border-radius: 4px;
      overflow-x: auto; /* Enable horizontal scrolling for long lines */
      font-family: 'Consolas', 'Monaco', 'monospace'; /* Monospaced font for code */
      font-size: 12px;
      color: #333;
      flex-grow: 1; /* Allow stack trace to grow and take available space */
    `;

    // Append elements to the dialog
    dialog.appendChild(closeButton);
    dialog.appendChild(title);
    dialog.appendChild(messageContent);
    dialog.appendChild(stackTracePre);

    // Append overlay and dialog to the container, then container to body
    modalContainer.appendChild(overlay);
    modalContainer.appendChild(dialog);
    document.body.appendChild(modalContainer);

    // Optional: Add event listener to close modal when clicking outside of the dialog
    overlay.addEventListener('click', (event) => {
      // Check if the click was directly on the overlay, not on the dialog itself
      if (event.target.id === DEBUG_MESSAGE_OVERLAY_ID) {
        modalContainer.remove();
      }
    });

    // Optional: Add keyboard listener for 'Escape' key to close the modal
    const handleEscape = (event) => {
      if (event.key === 'Escape' || event.keyCode === 27) {
        modalContainer.remove();
        document.removeEventListener('keydown', handleEscape); // Clean up listener
      }
    };
    document.addEventListener('keydown', handleEscape);
  }

  // Expose the message function globally via window.debugMessage
  window.debug = {
    message: message
  };

  console.log("debug_message.js module loaded and attached to window.debugMessage.");

})(window);
