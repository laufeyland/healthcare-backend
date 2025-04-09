import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
import healthapp.routing  # Import your routing file

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),  # For regular HTTP requests
    "websocket": AuthMiddlewareStack(
        URLRouter(
            healthapp.routing.websocket_urlpatterns  # Your WebSocket routes
        )
    ),
})
