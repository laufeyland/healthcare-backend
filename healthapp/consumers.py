from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
import json

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        # Get the first offered subprotocol (e.g., "access_token")
        offered = self.scope.get("subprotocols", [])
        chosen_proto = offered[0] if offered else None

        if user and not isinstance(user, AnonymousUser) and user.is_authenticated:
            self.user_group_name = f"user_{user.id}"
            await self.channel_layer.group_add(self.user_group_name, self.channel_name)
            # Echo back the subprotocol so the browser handshake succeeds
            await self.accept(subprotocol=chosen_proto)
            print(f"✅ WebSocket accepted for {user} with subprotocol: {chosen_proto}")
        else:
            print("⛔ Unauthorized—closing connection")
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
        print(f"🧪 Disconnect with code: {close_code}")

    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message']
        }))
