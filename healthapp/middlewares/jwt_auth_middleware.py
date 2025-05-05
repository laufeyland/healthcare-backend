from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.tokens import UntypedToken
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import jwt
from django.conf import settings
from channels.exceptions import DenyConnection

User = get_user_model()

@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # Extract subprotocols
        subprotocols = scope.get("subprotocols", [])
        
        # Ensure there are at least two elements in the subprotocols list
        if len(subprotocols) < 2:
            print("⛔ No token found in subprotocols")
            raise DenyConnection("No token provided")
        
        token = subprotocols[1]  # The JWT token should be the second item
        print("🔐 Extracted token:", token)

        if not token:
            print("⛔ No token found")
            raise DenyConnection("No token provided")
        
        try:
            # Validate token
            validated_token = UntypedToken(token)
            decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user = await get_user(decoded["user_id"])
            print("👤 Loaded user:", user)
            
            # Assign user to scope
            scope["user"] = user
        except Exception as e:
            print("❌ Token validation failed:", str(e))
            scope["user"] = AnonymousUser()
        
        # Call the next middleware or consumer
        return await super().__call__(scope, receive, send)
