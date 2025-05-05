import os
import django
 

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import healthapp.routing 
from healthapp.middlewares.jwt_auth_middleware import JWTAuthMiddleware

application = ProtocolTypeRouter({
    "http": get_asgi_application(),  
    "websocket": 
        URLRouter(
            healthapp.routing.websocket_urlpatterns,
        )
    ,
})
