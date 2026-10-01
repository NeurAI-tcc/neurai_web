import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import TokenAcesso

class MonitoramentoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.camera_id = self.scope['url_route']['kwargs']['camera_id']
        self.usuario = await self.usuario_por_token()
        if not self.usuario or str(self.usuario.id) != str(self.camera_id):
            await self.close(code=4403)
            return
        self.room_group_name = f'video_{self.camera_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def video_frame(self, event):
        await self.send(text_data=json.dumps({'type': 'video_frame', 'frame': event['frame']}))

    @database_sync_to_async
    def usuario_por_token(self):
        chave = self.scope.get('query_string', b'').decode().removeprefix('token=').split('&')[0]
        try:
            return TokenAcesso.objects.get(chave=chave).usuario
        except (TokenAcesso.DoesNotExist, TokenAcesso.MultipleObjectsReturned):
            return None

class AlertaConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.usuario_id = self.scope['url_route']['kwargs']['usuario_id']
        self.usuario = await self.usuario_por_token()
        if not self.usuario or str(self.usuario.id) != str(self.usuario_id):
            await self.close(code=4403)
            return
        self.room_group_name = f'alertas_{self.usuario_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def disparar_crise(self, event):
        await self.send(text_data=json.dumps({'type': 'alerta_crise', 'alerta': event['alerta']}))

    @database_sync_to_async
    def usuario_por_token(self):
        chave = self.scope.get('query_string', b'').decode().removeprefix('token=').split('&')[0]
        try:
            return TokenAcesso.objects.get(chave=chave).usuario
        except (TokenAcesso.DoesNotExist, TokenAcesso.MultipleObjectsReturned):
            return None