import json
from channels.generic.websocket import AsyncWebsocketConsumer

class MonitoramentoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.camera_id = self.scope['url_route']['kwargs']['camera_id']
        self.room_group_name = f'video_{self.camera_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def video_frame(self, event):
        await self.send(text_data=json.dumps({'type': 'video_frame', 'frame': event['frame']}))

class AlertaConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.usuario_id = self.scope['url_route']['kwargs']['usuario_id']
        self.room_group_name = f'alertas_{self.usuario_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def disparar_crise(self, event):
        await self.send(text_data=json.dumps({'type': 'alerta_crise', 'alerta': event['alerta']}))