let aiWebSocketReceiver = null;

function initializeAIWebSocket() {
    // Ensure only one instance is active at a time
    if (aiWebSocketReceiver) {
        aiWebSocketReceiver.close(); // Close existing connection if any
    }
    aiWebSocketReceiver = new WebSocketAIReceiver();
}

class WebSocketAIReceiver {
    constructor() {
        this.websocketUrl = window.configuration.SACCESSCO_WEBSOCKET_URL;

        this.socket = null; // Will hold the WebSocket instance
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10; // Maximum number of reconnection attempts
        this.reconnectDelay = 1000; // Initial delay in ms before attempting reconnect
        this.isClosingIntentionally = false; // Flag to prevent unwanted reconnects

        // Automatically try to connect when the instance is created
        this.connect();
    }
    handleAiMessage(message) {
        const data = JSON.parse(message);
        console.log("AI response: " + data);
        if (data.speak !== null && data.speak !== undefined && data.speak.length > 0) {
            console.log("Speaking: " + data.speak);
            window.speechModule.speak(data.speak);
        }
        if (data.execute !== null && data.execute !== undefined && Array.isArray(data.execute) && data.execute.length > 0) {
            console.log("Executing: " + data.execute);
            window.pageManipulatorModule.executePlan(data.execute);
        }
    }
    /**
     * Establishes the WebSocket connection.
     */
    connect() {
        if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
            console.log("WebSocketAIReceiver: Socket already connected or connecting.");
            return;
        }

        this.isClosingIntentionally = false; // Reset intentional close flag
        console.log(`WebSocketAIReceiver: Attempting to connect to ${this.websocketUrl}`);
        this.socket = new WebSocket(this.websocketUrl);

        // --- Assign Event Handlers ---
        this.socket.onopen = (event) => this.onOpen(event);
        this.socket.onmessage = (event) => this.onMessage(event);
        this.socket.onclose = (event) => this.onClose(event);
        this.socket.onerror = (event) => this.onError(event);
    }

    onOpen(event) {
        console.log('WebSocketAIReceiver: Connection opened.', event);
        this.reconnectAttempts = 0; // Reset reconnect attempts on successful connection
    }

    onMessage(event) {
        // console.log('WebSocketAIReceiver: Raw message received:', event.data);

        try {
            const data = JSON.parse(event.data);
            const messageType = data.type;

            // Check if the message type is 'ai_response'
            if (messageType === 'ai_response') {
                // The AI response content is expected in the 'message' key
                const aiResponseContent = data.message;

                // Check if the 'message' property exists and is not null/undefined
                if (aiResponseContent !== undefined && aiResponseContent !== null) {
                    console.log('WebSocketAIReceiver: Received AI response message.');

                    this.handleAiMessage(aiResponseContent);
                } else {
                     console.warn('WebSocketAIReceiver: Received ai_response message but missing "message" content.', data);
                     // Optional: Call error callback or handle this case
                }
            } else if (messageType === 'error' && data.message) {
                 // Optional: Handle error messages sent from the backend task/consumer
                 console.error('WebSocketAIReceiver: Received error message from backend:', data.message);
                 // Optional: Display this error to the user
            }
            // Handle other message types if necessary

        } catch (error) {
            console.error('WebSocketAIReceiver: Failed to parse message data:', error, event.data);
            if (this.onErrorCallback) {
                 this.onErrorCallback(error); // Call optional user-provided error callback
            }
        }
    }

    onClose(event) {
        console.log('WebSocketAIReceiver: Connection closed.', event);

        // Only attempt to reconnect if the close was NOT intentional and max attempts not reached
        if (!this.isClosingIntentionally && event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            console.log(`WebSocketAIReceiver: Attempting to reconnect in ${this.reconnectDelay}ms (Attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})...`);
            setTimeout(() => {
                this.reconnectAttempts++;
                this.connect(); // Try to reconnect
            }, this.reconnectDelay);
            // Optional: Increase reconnectDelay exponentially or with jitter
            // this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000); // Max delay 30 seconds
        } else if (!this.isClosingIntentionally && event.code !== 1000) {
            console.error(`WebSocketAIReceiver: Max reconnection attempts (${this.maxReconnectAttempts}) reached. Connection failed.`);
            // Notify the user or application state of the permanent failure
        }
        // If code is 1000 or isClosingIntentionally is true, it was a clean or intentional close, no need to reconnect automatically
    }

    onError(event) {
        console.error('WebSocketAIReceiver: Error occurred:', event);
    }

    close() {
        this.isClosingIntentionally = true; // Set flag before closing
        if (this.socket && this.socket.readyState !== WebSocket.CLOSED) {
            console.log("WebSocketAIReceiver: Closing connection intentionally.");
            // Use code 1000 for a clean closure
            this.socket.close(1000, 'Client closing connection');
        }
    }
}

// --- How to use this module in your HTML/JS ---
/*
// 1. Determine the WebSocket URL that maps to your AiConsumer.
// Based on your fixed group name "ai", your routing.py might have something like:
// re_path(r'ws/ai/$', consumers.AiConsumer.as_asgi()),
// So the URL would be:
const websocketProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
const websocketHost = window.location.host; // e.g., 'localhost:8000' or 'yourdomain.com'
const websocketUrl = `${websocketProtocol}${websocketHost}/ws/ai/`; // Adjust path if needed

// 2. Define the callback function that handles the received AI response string
function handleReceivedAIResponse(aiResponseString) {
    console.log("Frontend: Received AI response:", aiResponseString);
    // --- Update your UI here with the received AI response ---
    const chatArea = document.getElementById('chat-display'); // Assuming you have a div with this ID
    if (chatArea) {
        const aiMessageElement = document.createElement('div');
        // Be cautious with innerHTML if the response could contain malicious HTML/JS
        // aiMessageElement.innerHTML = aiResponseString; // Use with caution! Sanitize HTML!
        aiMessageElement.textContent = aiResponseString; // Safer for plain text
        aiMessageElement.classList.add('ai-message'); // Add CSS class for styling
        chatArea.appendChild(aiMessageElement);
        chatArea.scrollTop = chatArea.scrollHeight; // Scroll to bottom
    } else {
        console.error("Frontend: Chat display area not found (element with ID 'chat-display').");
    }
}

// 3. (Optional) Define callbacks for other events
function handleWebSocketError(error) {
    console.error("Frontend: WebSocket encountered an error:", error);
    // Display an error message to the user
}

function handleWebSocketClose(event) {
    console.log("Frontend: WebSocket connection closed:", event);
    // Update UI to show connection status (e.g., "Disconnected")
    if (!event.wasClean) {
        // Handle unexpected closure (reconnection logic is in the class)
        console.log("Frontend: WebSocket connection closed unexpectedly.");
    }
}

function handleWebSocketOpen(event) {
     console.log("Frontend: WebSocket connection opened successfully.");
     // Update UI to show connection status (e.g., "Connected")
}


// 4. Create an instance of the receiver when your page/component loads
let aiWebSocketReceiver = null;

// Call this function when your page is ready to start the WebSocket connection
function initializeAIWebSocket() {
    // Ensure only one instance is active at a time
    if (aiWebSocketReceiver) {
        aiWebSocketReceiver.close(); // Close existing connection if any
    }
    aiWebSocketReceiver = new WebSocketAIReceiver(
        websocketUrl,
        handleReceivedAIResponse,
        handleWebSocketError,     // Optional error callback
        handleWebSocketClose,     // Optional close callback
        handleWebSocketOpen       // Optional open callback
    );
}

// Example: Call initializeAIWebSocket() when your page or application starts
// window.onload = initializeAIWebSocket; // Simple example for a full page load


// 5. Remember to close the connection when it's no longer needed
// (e.g., when the user navigates away from the chat page, logs out, or the component unmounts)
// if (aiWebSocketReceiver) {
//     aiWebSocketReceiver.close();
// }

 */

window.websocke = {

};