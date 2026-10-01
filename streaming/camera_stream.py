import threading

from asgiref.sync import async_to_sync

from .tracking import frame_para_base64, iniciar_rastreamento


class CameraStream:
    def __init__(self, camera_id, endereco_ip, channel_layer, usuario_id):
        self.camera_id = str(camera_id)
        self.endereco_ip = endereco_ip
        self.channel_layer = channel_layer
        self.usuario_id = str(usuario_id)
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._capturar, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def _capturar(self):
        try:
            iniciar_rastreamento(
                usuario_id=self.usuario_id,
                camera_id=self.camera_id,
                on_frame=self._enviar_frame,
                stop_event=self.stop_event,
            )
            self._enviar_status('tracking_stopped')
        except Exception as exc:
            self._enviar_status('tracking_error', str(exc))

    def _enviar_frame(self, frame, metadata):
        frame_base64 = frame_para_base64(frame)
        if frame_base64 is None:
            return
        async_to_sync(self.channel_layer.group_send)(
            f'video_{self.camera_id}',
            {
                'type': 'video_frame',
                'frame': frame_base64,
                'metadata': metadata,
            },
        )

    def _enviar_status(self, status, detalhe=None):
        async_to_sync(self.channel_layer.group_send)(
            f'video_{self.camera_id}',
            {
                'type': 'camera_status',
                'status': status,
                'detalhe': detalhe,
            },
        )
