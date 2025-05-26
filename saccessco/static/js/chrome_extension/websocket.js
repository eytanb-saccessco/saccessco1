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
        // Ensure window.configuration and SACCESSCO_WEBSOCKET_URL exist
        if (!window.configuration || !window.configuration.SACCESSCO_WEBSOCKET_URL) {
            console.error("WebSocketAIReceiver: window.configuration.SACCESSCO_WEBSOCKET_URL is not defined.");
            // Handle this error appropriately, e.g., throw, or prevent connection
            // For now, we'll return to prevent further errors.
            return;
        }

        this.websocketUrl = window.configuration.SACCESSCO_WEBSOCKET_URL + "/" + window.conversation_id;
        console.log(`WebSocketAIReceiver: Constructed WebSocket URL: ${this.websocketUrl}`);


        this.socket = null; // Will hold the WebSocket instance
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10; // Maximum number of reconnection attempts
        this.reconnectDelay = 1000; // Initial delay in ms before attempting reconnect
        this.isClosingIntentionally = false; // Flag to prevent unwanted reconnects

        // Automatically try to connect when the instance is created
        this.connect();
    }
    handleAiMessage(message) {
        // This function expects a parsed JSON object, not a string that needs parsing.
        // It's called from onMessage after JSON.parse(event.data).
        const data = message; // 'message' is already the parsed object from onMessage
        console.log("AI response (parsed object):", data);

        if (data.speak !== null && data.speak !== undefined && data.speak.length > 0) {
            console.log("Speaking: " + data.speak);
            if (window.speechModule && typeof window.speechModule.speak === 'function') {
                window.speechModule.speak(data.speak);
            } else {
                console.warn("window.speechModule.speak is not available.");
            }
        }
        if (data.execute !== null && data.execute !== undefined && Array.isArray(data.execute) && data.execute.length > 0) {
            console.log("Executing: " + data.execute);
            if (window.pageManipulatorModule && typeof window.pageManipulatorModule.executePlan === 'function') {
                window.pageManipulatorModule.executePlan(data.execute);
            } else {
                console.warn("window.pageManipulatorModule.executePlan is not available.");
            }
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
            const data = JSON.parse(event.data); // Parse the incoming JSON string
            const messageType = data.type;

            // Check if the message type is 'ai_response'
            // The backend consumer now sends the structured AI object directly as the top-level message
            // based on the updated consumer (await self.send_json(ai_response)).
            // So, 'data' itself should be the structured object (e.g., {speak: "...", execute: [...]}).
            if (messageType === 'ai_response') { // This check is for messages wrapped with a 'type' key
                // If the backend sends {'type': 'ai_response', 'message': structured_object}
                // then you'd use data.message here.
                // But if it sends structured_object directly as the main payload,
                // then data itself is the structured object.
                // Based on previous consumer updates, the consumer sends the structured object directly.
                // So, we expect 'data' to be the structured object.
                // The 'type' check here is redundant if the consumer sends the raw structured object.
                // Let's assume the consumer sends the structured object directly.
                console.log('WebSocketAIReceiver: Received AI response message (structured).');
                this.handleAiMessage(data); // Pass the entire parsed object to handleAiMessage
            } else if (data.speak !== undefined || data.execute !== undefined) {
                 // This handles cases where the structured AI response is sent without a 'type' wrapper
                 // (e.g., if the consumer just does send_json(ai_response_object))
                 console.log('WebSocketAIReceiver: Received AI response message (structured, no explicit type).');
                 this.handleAiMessage(data);
            } else if (messageType === 'error' && data.message) {
                 // Optional: Handle error messages sent from the backend task/consumer
                 console.error('WebSocketAIReceiver: Received error message from backend:', data.message);
                 // Optional: Display this error to the user
            } else {
                console.warn('WebSocketAIReceiver: Received unexpected message type or format:', data);
            }

        } catch (error) {
            console.error('WebSocketAIReceiver: Failed to parse message data:', error, event.data);
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

// Expose the initializer globally.
// This allows your background.js or other parts of the extension to call it.
window.websocket = {
    initializeAIWebSocket
}
