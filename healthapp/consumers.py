from channels.generic.websocket import AsyncWebsocketConsumer
import json

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Adding the WebSocket connection to a group
        await self.channel_layer.group_add(
            "notifications",  # Group name (you can call this anything)
            self.channel_name  
        )
        if self.scope['user'].is_anonymous:
            # Reject the connection if the user is not authenticated
            await self.close()
            return {'error': 'User not authenticated'}
        await self.accept()  

    async def disconnect(self, close_code):
        # Removing from the group on disconnect
        await self.channel_layer.group_discard(
            "notifications",
            self.channel_name
        )

    
    async def receive(self, text_data):
        pass

    
    async def send_notification(self, event):
        message = event['message']  
        await self.send(text_data=json.dumps({
            'message': message
        }))
