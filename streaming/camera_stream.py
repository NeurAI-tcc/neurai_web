import base64
import threading

import cv2
from asgiref.sync import async_to_sync


class CameraStream:
    def __init__(self, camera_id, endereco_ip, channel_layer):
        self.camera_id = str(camera_id)
        self.endereco_ip = endereco_ip
        self.channel_layer = channel_layer
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._capturar, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def _capturar(self):
        captura = cv2.VideoCapture(self.endereco_ip)
        try:
            if not captura.isOpened():
                self._enviar_status('camera_unavailable')
                return

            while not self.stop_event.is_set():
                sucesso, frame = captura.read()
                if not sucesso:
                    self._enviar_status('frame_unavailable')
                    break

                sucesso, buffer = cv2.imencode('.jpg', frame)
                if not sucesso:
                    continue

                frame_base64 = base64.b64encode(buffer).decode('ascii')
                async_to_sync(self.channel_layer.group_send)(
                    f'video_{self.camera_id}',
                    {'type': 'video_frame', 'frame': frame_base64},
                )
        finally:
            captura.release()

    def _enviar_status(self, status):
        async_to_sync(self.channel_layer.group_send)(
            f'video_{self.camera_id}',
            {'type': 'camera_status', 'status': status},
        )
