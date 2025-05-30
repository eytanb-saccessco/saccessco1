# test_manual_websocket_client.py
import websocket
import json
import time
import threading
import os
import django

# --- Django Channels Setup ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saccessco.settings')
django.setup()
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# --- End Django Channels Setup ---

# --- Configuration ---
SERVER_URL = "ws://localhost:8081/ws/saccessco/ai/test_ai_response_conv/"
CONVERSATION_ID = "test_ai_response_conv"


# --- End Configuration ---

def on_message(ws, message):
    print(f"\n--- MANUAL CLIENT: Received message: {message}")
    try:
        data = json.loads(message)
        print(f"--- MANUAL CLIENT: Parsed data: {data}")
    except json.JSONDecodeError:
        print("--- MANUAL CLIENT: Could not decode JSON.")


def on_error(ws, error):
    print(f"\n--- MANUAL CLIENT: ERROR: {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"\n--- MANUAL CLIENT: Connection Closed. Code: {close_status_code}, Reason: {close_msg}")


def on_open(ws):
    print("--- MANUAL CLIENT: Connection Opened. Sending initial 'client_hello_manual' message.")
    client_hello_message = {"type": "client_hello_manual", "message": "Hello from manual Python client!"}
    ws.send(json.dumps(client_hello_message))
    print(f"--- MANUAL CLIENT: Sent: {json.dumps(client_hello_message)}")

    def trigger_backend_response():
        time.sleep(1)
        print("\n--- MANUAL CLIENT: Attempting to trigger backend AI response via Django Channels layer...")

        channel_layer_in_thread = get_channel_layer()  # Get channel layer within the thread

        if channel_layer_in_thread:
            print(f"--- MANUAL CLIENT: Channel layer (in thread) obtained: {type(channel_layer_in_thread)} ---")
            # For Redis, it might show something like <class 'channels_redis.core.RedisChannelLayer'>
            # For InMemory, it might show <class 'channels.layers.InMemoryChannelLayer'>

            group_name = f"WEB_SOCKET_GROUP_NAME_{CONVERSATION_ID}"
            ai_response_payload = {
                "speak": "Hello from the AI model (Manual Test)!",
                "execute": [{"action": "log", "value": "Manual test received by browser (hopefully!)"}]
            }
            try:
                print(f"--- MANUAL CLIENT: Calling group_send to group '{group_name}' with type 'ai_response'...")
                # The group_send method itself doesn't return anything useful
                # in a synchronous context, but any exceptions will be caught.
                async_to_sync(channel_layer_in_thread.group_send)(
                    group_name,
                    {
                        "type": "ai_response",
                        "ai_response": ai_response_payload
                    }
                )
                print(f"--- MANUAL CLIENT: group_send call completed. (Doesn't guarantee delivery, only enqueuing).")
            except Exception as e:
                print(f"--- MANUAL CLIENT: ERROR during group_send call: {e}")
        else:
            print("--- MANUAL CLIENT: ERROR: Channel layer NOT available in trigger_backend_response thread.")

    threading.Thread(target=trigger_backend_response).start()


if __name__ == "__main__":
    # Optional: Enable trace for extremely verbose client-side WebSocket logging
    # websocket.enableTrace(True)

    # Verify channel layer availability in the main thread context too
    main_channel_layer = get_channel_layer()
    if main_channel_layer:
        print(f"--- MANUAL CLIENT: Main thread channel layer available: {type(main_channel_layer)} ---")
    else:
        print("--- MANUAL CLIENT: Main thread channel layer NOT available. This is a problem. ---")

    print(f"--- MANUAL CLIENT: Attempting to connect to: {SERVER_URL}")

    ws_app = websocket.WebSocketApp(
        SERVER_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    ws_app.run_forever()