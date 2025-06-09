// saccessco/static/js/chrome_extension/websocket.js

// Ensure this is at the top of the file or globally accessible
// This array will store raw WebSocket messages for testing.
if (!window.__receivedWebSocketMessages) {
    window.__receivedWebSocketMessages = [];
}

let aiWebSocketReceiver = null; // Declare globally or at the top of the module

function initializeAIWebSocket() {
    // Ensure only one instance is active at a time
    if (aiWebSocketReceiver) {
        aiWebSocketReceiver.close(); // Close existing connection if any
    }
    aiWebSocketReceiver = new WebSocketAIReceiver();
    window.aiWebSocketReceiver = aiWebSocketReceiver;
}

class WebSocketAIReceiver {
    constructor() {
        // Ensure window.configuration and SACCESSCO_WEBSOCKET_URL exist
        if (!window.configuration || !window.configuration.SACCESSCO_WEBSOCKET_URL) {
            console.error("WebSocketAIReceiver: window.configuration.SACCESSCO_WEBSOCKET_URL is not defined.");
            return; // Prevent further errors
        }

        let baseUrl = window.configuration.SACCESSCO_WEBSOCKET_URL;
        if (!baseUrl.endsWith('/')) {
          baseUrl += '/';
        }
        this.websocketUrl = baseUrl + window.conversation_id + "/";
        console.log("--DEBUG--: window.configuration.SACCESSCO_WEBSOCKET_URL: " + window.configuration.SACCESSCO_WEBSOCKET_URL);
        console.log("--DEBUG--:  window.conversation_id: " +  window.conversation_id);
        console.log(`WebSocketAIReceiver: Constructed WebSocket URL: ${this.websocketUrl}`);

        this.socket = null; // Will hold the WebSocket instance
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;
        this.isClosingIntentionally = false;

        // Automatically try to connect when the instance is created
        this.connect();
    }

    handleAiMessage(message) {
        const data = message;
        console.log("DEBUG: handleAiMessage called with parsed data:", data);

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
        console.log('--- CRITICAL DEBUG: WebSocketAIReceiver: Connecting');
        if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
            console.log("WebSocketAIReceiver: Socket already connected or connecting.");
            return;
        }

        this.isClosingIntentionally = false;
        console.log(`--- CRITICAL DEBUG: WebSocketAIReceiver: Attempting to connect to ${this.websocketUrl}`);
        this.socket = new WebSocket(this.websocketUrl);
        console.log('--- CRITICAL DEBUG: WebSocketAIReceiver: Socket created');

        // Assign Event Handlers
        this.socket.onopen = (event) => {
            console.log('--- CRITICAL DEBUG: WebSocketAIReceiver: Connection opened. ReadyState:', this.socket.readyState, event);
            this.reconnectAttempts = 0; // Reset reconnect attempts on successful connection

            // --- NEW: Send a message immediately upon connection ---
            const clientHelloMessage = {
                type: 'client_hello',
                message: 'Hello from browser client!'
            };
            this.socket.send(JSON.stringify(clientHelloMessage));
            console.log('--- CRITICAL DEBUG: WebSocketAIReceiver: Sent client_hello message.');
            // --- END NEW ---
        };

        console.log('--- CRITICAL DEBUG: WebSocketAIReceiver: Assigning onmessage handler');
        this.socket.onmessage = (event) => {
            console.log('--- CRITICAL DEBUG: WebSocketAIReceiver: RAW message received (onMessage handler FIRED!):', event.data);
            window.__receivedWebSocketMessages.push(event.data); // Store the raw message for Python to inspect

            try {
                const data = JSON.parse(event.data);
                const messageType = data.type;

                if (data.speak !== undefined || data.execute !== undefined) {
                     console.log('WebSocketAIReceiver: Received AI response message (structured, no explicit type).');
                     this.handleAiMessage(data);
                } else if (messageType === 'ai_response' && data.ai_response) {
                    console.log('WebSocketAIReceiver: Received AI response message (structured, with explicit type).');
                    this.handleAiMessage(data.ai_response);
                } else if (messageType === 'error' && data.message) {
                     console.error('WebSocketAIReceiver: Received error message from backend:', data.message);
                } else {
                    console.warn('WebSocketAIReceiver: Received unexpected message type or format:', data);
                }

            } catch (error) {
                console.error('--- CRITICAL DEBUG: WebSocketAIReceiver: Error in onMessage handler parsing/processing:', error, event.data);
            }
        };
        console.log('--- CRITICAL DEBUG: WebSocketAIReceiver: onmessage handler assigned.');

        this.socket.onclose = (event) => {
            console.log('--- CRITICAL DEBUG: WebSocketAIReceiver: Connection closed. Code:', event.code, 'Reason:', event.reason, 'Was Clean:', event.wasClean);
            if (!this.isClosingIntentionally && event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
                console.log(`--- CRITICAL DEBUG: WebSocketAIReceiver Attempting to reconnect in ${this.reconnectDelay}ms (Attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})...`);
                setTimeout(() => {
                    this.reconnectAttempts++;
                    this.connect();
                }, this.reconnectDelay);
            } else if (!this.isClosingIntentionally && event.code !== 1000) {
                console.error(`--- CRITICAL DEBUG: WebSocketAIReceiver Max reconnection attempts (${this.maxReconnectAttempts}) reached. Connection failed.`);
            }
        };
        this.socket.onerror = (event) => {
            console.error('--- CRITICAL DEBUG: WebSocketAIReceiver: Error occurred. ReadyState:', this.socket.readyState, event);
        };
        console.log('--- CRITICAL DEBUG: WebSocketAIReceiver: Socket initialized');

    }

    close() {
        this.isClosingIntentionally = true;
        if (this.socket && this.socket.readyState !== WebSocket.CLOSED) {
            console.log("WebSocketAIReceiver: Closing connection intentionally.");
            this.socket.close(1000, 'Client closing connection');
        }
    }
}

// Expose the initializer globally.
window.websocket = {
    initializeAIWebSocket
}