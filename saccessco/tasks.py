import logging
from typing import List, Dict, Any
from .ai import AIEngine # Adjust the import path as needed
from channels.layers import get_channel_layer
from .consumers import WEB_SOCKET_GROUP_NAME
import asyncio

logger = logging.getLogger("saccessco")

class AiResponse:
    def __init__(self, message):
        self.message = message

    @property
    def json(self):
        return {
            'type': 'ai_response', # Type for the frontend to identify the message
            'message': self.message
        }

async def ai_call(conversation: List[Dict[Any, Any]]):
    channel_layer = get_channel_layer() # Get channel layer instance early
    try:
        engine = AIEngine()
        engine.set_conversation(conversation)
        ai_response = engine.respond()
        if channel_layer:
            conversation_group_name = WEB_SOCKET_GROUP_NAME
            await channel_layer.group_send(
                conversation_group_name,
                ai_response
            )
        else:
            logger.error("Task: Channel layer is not configured or available. Could not send AI response.")

        # 5. Return the result (optional, but good practice for task results)
        return ai_response

    except Exception as e:
        # Log any errors that occur during the task execution
        logger.error("Error in Django-Q task process_conversation_and_send_response : {e}")
        raise e
