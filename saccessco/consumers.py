# saccessco/consumers.py
import asyncio
import json # Ensure json is imported
from channels.generic.websocket import AsyncWebsocketConsumer
import logging

from saccessco.validators import validate_ai_response

logger = logging.getLogger('saccessco')

class AiConsumer(AsyncWebsocketConsumer):
    GROUP_NAME_PREFIX = 'WEB_SOCKET_GROUP_NAME_'
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.group_name = f"{self.GROUP_NAME_PREFIX}{self.conversation_id}"

        print(f"--- AiConsumer: Received path in connect: {self.scope['path']} ---")
        print(f"--- AiConsumer: Connecting to group '{self.group_name}' for conversation ID: {self.conversation_id} ---")

        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        # ADD THIS LINE: Small delay after accepting the connection
        await asyncio.sleep(0.05) # Sleep for 50 milliseconds

        print(f"WebSocket connected for conversation ID: {self.conversation_id} to group: {self.group_name}")

    # This method handles messages received directly from the WebSocket client
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')

        logger.info(f"--- AiConsumer: Received RAW message from client: {text_data_json} ---")

        if message_type == 'client_hello':
            # Handle initial client hello (from Selenium test)
            client_message = text_data_json.get('message')
            logger.info(f"--- AiConsumer: Client 'hello' message received: {client_message} ---")
            # You might want to send a confirmation or initial AI message here
            # For example:
            # await self.send(text_data=json.dumps({"type": "server_ack", "message": "Received your hello!"}))
            logger.info("INFO: WebSocketAIReceiver connection established.")

        elif message_type == 'client_hello_manual': # NEW: Handle the manual client's hello
            client_message = text_data_json.get('message')
            logger.info(f"--- AiConsumer: Manual client 'hello' message received: {client_message} ---")
            # This message doesn't need a direct response for the test, it's just for confirmation.

        else:
            logger.info(f"--- AiConsumer: Received unexpected message from client: {text_data_json} ---")
            # Fallback for unhandled message types directly from WebSocket

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected for conversation ID: {self.conversation_id} from group: {self.group_name} with code {close_code}")
        # Leave group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def ai_response(self, event):
        ai_response_data = event
        if validate_ai_response(ai_response_data):
            logger.info(f"--- AiConsumer: Sending AI response to client: {ai_response_data} ---")
            await self.send(text_data=json.dumps(ai_response_data))