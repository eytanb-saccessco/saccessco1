import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
import logging

logger = logging.getLogger("saccessco")

class AiConsumer(AsyncJsonWebsocketConsumer):
    # Class-level constant for the group name prefix
    GROUP_NAME_PREFIX = "WEB_SOCKET_GROUP_NAME_"

    # REMOVED custom __init__ method.
    # The base AsyncJsonWebsocketConsumer will handle setting self.scope.

    async def connect(self):
        # Now, self.scope is guaranteed to be available when connect is called.
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f"{self.GROUP_NAME_PREFIX}{self.conversation_id}"

        logger.info(f"--- AiConsumer: Received path in connect: {self.scope['path']} ---")
        logger.info(f"--- AiConsumer: Connecting to group '{self.conversation_group_name}' for conversation ID: {self.conversation_id} ---")

        # Add the consumer's channel to the dynamically named group
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )

        # Accept the WebSocket connection
        await self.accept()
        logger.info(f"WebSocket connected for conversation ID: {self.conversation_id} to group: {self.conversation_group_name}")

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected for conversation ID: {self.conversation_id} from group: {self.conversation_group_name} with code {close_code}")
        # Leave the dynamically named conversation group
        await self.channel_layer.group_discard(
            self.conversation_group_name,
            self.channel_name
        )

    async def ai_response(self, event):
        """
        Handler for messages sent to the group with type 'ai_response'.
        The 'event' dictionary contains the payload sent by group_send.
        Expected 'event' structure from task: {'type': 'ai_response', 'ai_response': { ... structured_object ... }}
        """
        # self.conversation_id is available here because it was set in connect().
        ai_response_object = event.get('ai_response')

        if ai_response_object is not None:
            logger.info(f"Consumer received AI response from channel layer for conversation ID {self.conversation_id}: {ai_response_object}")

            # Send the AI response object back to the client over the WebSocket.
            # send_json automatically handles json.dumps().
            await self.send_json(ai_response_object)
        else:
            logger.error(f"Consumer received 'ai_response' message from channel layer without 'ai_response' payload. Received event: {event}")
            await self.send_json({'type': 'error', 'message': 'Invalid AI response format received from server.'})