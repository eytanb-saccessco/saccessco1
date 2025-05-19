import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer

WEB_SOCKET_GROUP_NAME = "ai_response"

class AiConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(
            WEB_SOCKET_GROUP_NAME,
            self.channel_name # Add the current consumer's channel to the group
        )

        # Accept the WebSocket connection
        await self.accept()
        print(f"WebSocket connected to conversation group: {WEB_SOCKET_GROUP_NAME}")

    async def disconnect(self, close_code):
        print(f"WebSocket disconnected from conversation group: {WEB_SOCKET_GROUP_NAME} with code {close_code}")
        # Leave the conversation group
        await self.channel_layer.group_discard(
            WEB_SOCKET_GROUP_NAME,
            self.channel_name
        )

    async def ai_response(self, message, **kwargs):
        """
        Handler for messages sent to the group with type 'ai_response'.
        Expected message structure from task: {'type': 'ai_response', 'message': 'AI text'}
        Receives 'message' as a keyword argument.
        """
        # The 'message' argument now contains the AI response string from the task.
        # **kwargs would contain any other keys sent by the task (e.g., 'error': True)

        if message is not None: # Check if the 'message' key was present
            print(f"Consumer received AI response from channel layer for group {WEB_SOCKET_GROUP_NAME}: {message}")

            # Send the AI response back to the client over the WebSocket
            # AsyncJsonWebsocketConsumer's send_json automatically handles json.dumps()
            # The frontend expects a JSON object with 'type' and 'message' keys.
            await self.send_json([message])
        else:
            print(f"Consumer received 'ai_response' message from channel layer without 'message' argument. Received kwargs: {kwargs}")
            # Optionally, send an error message back to the client
            # await self.send_json({'type': 'error', 'message': 'Received invalid message format from channel layer'})


