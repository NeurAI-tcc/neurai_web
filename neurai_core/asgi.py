import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neurai_core.settings')
django_asgi_app = get_asgi_application()

import streaming.routing # type: ignore

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            streaming.routing.websocket_urlpatterns
        )
    ),
})