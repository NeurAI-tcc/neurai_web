import cv2
import base64
import asyncio
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import CameraUser

class VideoCameraConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.is_streaming = False
        self.video_task = None
        # Agora não iniciamos a câmara na ligação. Esperamos que o Flutter mande o IP.

    async def disconnect(self, close_code):
        self.is_streaming = False
        if self.video_task:
            self.video_task.cancel()

    # Função ativada quando o Flutter envia o IP
    async def receive(self, text_data):
        dados = json.loads(text_data)
        
        if 'ip_camera' in dados:
            ip_recebido = dados['ip_camera']
            
            # 1. Guarda/Atualiza no MongoDB
            await self.salvar_ip_banco(ip_recebido)
            
            # 2. Se já houver um vídeo a dar, cancela-o para mudar de câmara
            if self.is_streaming and self.video_task:
                self.is_streaming = False
                self.video_task.cancel()
                await asyncio.sleep(0.5)

            # 3. Inicia o fluxo de vídeo com o novo IP
            self.is_streaming = True
            self.video_task = asyncio.create_task(self.stream_camera(ip_recebido))

    @database_sync_to_async
    def salvar_ip_banco(self, ip):
        # Procura a primeira câmara cadastrada ou cria uma nova se o banco estiver vazio
        camera = CameraUser.objects.first()
        if not camera:
            camera = CameraUser(nome_paciente="Paciente Teste")
        
        camera.ip_camera = ip
        camera.save()

    async def stream_camera(self, camera_url):
        # Se o Flutter mandar "0", converte para número inteiro (webcam local)
        if camera_url == "0":
            camera_url = 0
            
        cap = cv2.VideoCapture(camera_url)

        while self.is_streaming:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame = cv2.resize(frame, (640, 480))
            
            # (Futuro código de rastreamento IA entra aqui)

            _, buffer = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')

            await self.send(text_data=json.dumps({
                'imagem_base64': frame_base64
            }))
            
            await asyncio.sleep(0.05)

        cap.release()