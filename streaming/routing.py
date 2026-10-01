from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/camera/(?P<camera_id>\d+)/$', consumers.MonitoramentoConsumer.as_asgi()),
    re_path(r'^ws/alertas/(?P<usuario_id>\d+)/$', consumers.AlertaConsumer.as_asgi()),
]