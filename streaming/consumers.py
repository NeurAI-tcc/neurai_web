import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from mongoengine.errors import ValidationError
from .models import Camera, TokenAcesso
from .camera_stream import CameraStream

class MonitoramentoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.usuario = await self.usuario_por_token()
        camera_id = self.scope['url_route']['kwargs'].get('camera_id')
        if self.usuario is None:
            await self.close(code=4401)
            return
        camera = await self.camera_por_id(camera_id) if camera_id else await self.camera_do_usuario()
        if camera is None or camera.responsavel.id != self.usuario.id:
            await self.close(code=4403)
            return
        self.camera_id = str(camera.id)
        self.camera_ip = camera.endereco_ip
        self.room_group_name = f'video_{self.camera_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        self.camera_stream = CameraStream(
            self.camera_id,
            self.camera_ip,
            self.channel_layer,
        )
        self.camera_stream.start()

    async def disconnect(self, close_code):
        if hasattr(self, 'camera_stream'):
            self.camera_stream.stop()
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def video_frame(self, event):
        await self.send(text_data=json.dumps({'type': 'video_frame', 'frame': event['frame']}))

    async def camera_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'camera_status',
            'status': event['status'],
        }))

    @database_sync_to_async
    def usuario_por_token(self):
        query = parse_qs(self.scope.get('query_string', b'').decode())
        chave = query.get('token', [''])[0]
        if not chave:
            headers = dict(self.scope.get('headers', []))
            authorization = headers.get(b'authorization', b'').decode()
            chave = authorization.removeprefix('Bearer ').strip()
        if not chave:
            return None
        try:
            return TokenAcesso.objects.get(chave=chave).usuario
        except (TokenAcesso.DoesNotExist, TokenAcesso.MultipleObjectsReturned):
            return None

    @database_sync_to_async
    def camera_por_id(self, camera_id):
        if not camera_id:
            return None
        try:
            return Camera.objects.get(id=camera_id)
        except (Camera.DoesNotExist, ValidationError):
            return None

    @database_sync_to_async
    def camera_do_usuario(self):
        return Camera.objects(responsavel=self.usuario).first()

class AlertaConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.usuario_id = self.scope['url_route']['kwargs']['usuario_id']
        self.usuario = await self.usuario_por_token()
        if self.usuario is None:
            await self.close(code=4401)
            return
        if str(self.usuario.id) != str(self.usuario_id):
            await self.close(code=4403)
            return
        self.room_group_name = f'alertas_{self.usuario_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def disparar_crise(self, event):
        await self.send(text_data=json.dumps({'type': 'alerta_crise', 'alerta': event['alerta']}))

    @database_sync_to_async
    def usuario_por_token(self):
        query = parse_qs(self.scope.get('query_string', b'').decode())
        chave = query.get('token', [''])[0]
        if not chave:
            headers = dict(self.scope.get('headers', []))
            authorization = headers.get(b'authorization', b'').decode()
            chave = authorization.removeprefix('Bearer ').strip()
        if not chave:
            return None
        try:
            return TokenAcesso.objects.get(chave=chave).usuario
        except (TokenAcesso.DoesNotExist, TokenAcesso.MultipleObjectsReturned):
            return None