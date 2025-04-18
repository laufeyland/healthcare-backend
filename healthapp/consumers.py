from channels.generic.websocket import AsyncWebsocketConsumer
import json
import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import AuthenticationFailed


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract token from query string or header (whichever is used)
        token = self.scope.get('query_params', {}).get('token') or self.scope.get('headers', {}).get(b'authorization')

        if token:
            token = token.decode('utf-8').split(' ')[1] if isinstance(token, bytes) else token  # Clean up token if it's in 'Bearer' format

        # If there's no token, reject the connection
        if not token:
            await self.close()
            return

        # Validate token and attach user to the scope
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user = await database_sync_to_async(User.objects.get)(id=payload['user_id'])  # Assuming you store user_id in the JWT
            self.scope['user'] = user
        except jwt.ExpiredSignatureError:
            await self.close()
            return
        except jwt.InvalidTokenError:
            await self.close()
            return

        # If user is authenticated, allow connection
        if self.scope['user'].is_anonymous:
            await self.close()
            return {'error': 'User not authenticated'}

        # Accept the WebSocket connection if everything is fine
        await self.accept()

        # Add the user to the notification group
        await self.channel_layer.group_add(
            "notifications",  # Group name
            self.channel_name
        )

    async def disconnect(self, close_code):
        # Remove from the group when disconnected
        await self.channel_layer.group_discard(
            "notifications",
            self.channel_name
        )

    async def receive(self, text_data):
        # Handle incoming messages (if needed)
        pass

    async def send_notification(self, event):
        # Send notification to WebSocket
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))
