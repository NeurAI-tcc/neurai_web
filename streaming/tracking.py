import base64
from dataclasses import dataclass
from urllib.request import urlopen

import cv2
import numpy as np
from mongoengine.errors import DoesNotExist, ValidationError

from .models import Camera, PerfilCrianca, Usuario


@dataclass
class ContextoRastreamento:
    usuario: Usuario
    camera: Camera
    perfil: PerfilCrianca


def buscar_usuario_para_rastreamento(usuario_id=None, email=None):
    """Busca o usuário no MongoDB por ObjectId ou e-mail."""
    if not usuario_id and not email:
        raise ValueError("Informe usuario_id ou email")

    try:
        if usuario_id:
            return Usuario.objects.get(id=usuario_id)
        return Usuario.objects.get(email=email.strip().lower())
    except (DoesNotExist, ValidationError) as exc:
        raise LookupError("Usuário não encontrado") from exc


def buscar_contexto_rastreamento(usuario_id=None, email=None, camera_id=None):
    """Carrega usuário, perfil da criança e câmera autorizada."""
    usuario = buscar_usuario_para_rastreamento(usuario_id=usuario_id, email=email)

    if usuario.perfil_crianca is None:
        raise ValueError("Usuário não possui perfil da criança")

    try:
        if camera_id:
            camera = Camera.objects.get(id=camera_id, responsavel=usuario)
        else:
            camera = Camera.objects.get(responsavel=usuario)
    except (Camera.DoesNotExist, ValidationError) as exc:
        raise LookupError("Câmera não encontrada para este usuário") from exc

    return ContextoRastreamento(
        usuario=usuario,
        camera=camera,
        perfil=usuario.perfil_crianca,
    )


def normalizar_embedding(embedding):
    norma = np.linalg.norm(embedding)
    return embedding / norma if norma else None


def maior_face(faces):
    return max(
        faces,
        key=lambda face: (face.bbox[2] - face.bbox[0]) *
        (face.bbox[3] - face.bbox[1]),
    )


def carregar_imagem(caminho_ou_url):
    if not caminho_ou_url:
        return None

    try:
        if caminho_ou_url.startswith(('http://', 'https://')):
            with urlopen(caminho_ou_url, timeout=10) as resposta:
                image_array = np.asarray(bytearray(resposta.read()), dtype='uint8')
            return cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        return cv2.imread(caminho_ou_url)
    except (OSError, ValueError):
        return None


def extrair_embedding_face(app, frame, box):
    altura, largura = frame.shape[:2]
    x1, y1, x2, y2 = box
    largura_box = x2 - x1
    altura_box = y2 - y1
    margem_x = int(largura_box * 0.15)

    crop_x1 = max(0, x1 - margem_x)
    crop_x2 = min(largura, x2 + margem_x)
    crop_y1 = max(0, y1)
    crop_y2 = min(altura, y1 + int(altura_box * 0.55))
    crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]

    if crop.size == 0:
        return None

    faces = app.get(crop)
    if not faces:
        return None

    return normalizar_embedding(maior_face(faces).embedding)


def iniciar_rastreamento(
    usuario_id=None,
    email=None,
    camera_id=None,
    on_frame=None,
    stop_event=None,
):
    """Rastreia a criança do perfil do usuário na câmera vinculada.

    ``on_frame`` recebe ``(frame, metadata)`` para publicação no WebSocket.
    O servidor não usa ``cv2.imshow``; o encerramento pode ser solicitado
    configurando ``stop_event``.
    """
    contexto = buscar_contexto_rastreamento(
        usuario_id=usuario_id,
        email=email,
        camera_id=camera_id,
    )

    try:
        from insightface.app import FaceAnalysis
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError(
            'Instale insightface e ultralytics para iniciar o rastreamento'
        ) from exc

    app = FaceAnalysis(name='buffalo_s', providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(160, 160))

    referencias = []
    campos_fotos = (
        'foto_frente_url', 'foto_sorrindo_url', 'foto_direita_url',
        'foto_esquerda_url', 'foto_cima_url', 'foto_baixo_url',
    )
    for campo in campos_fotos:
        imagem = carregar_imagem(getattr(contexto.perfil, campo, None))
        if imagem is None:
            continue
        faces = app.get(imagem)
        if faces:
            embedding = normalizar_embedding(maior_face(faces).embedding)
            if embedding is not None:
                referencias.append(embedding)

    if not referencias:
        raise ValueError('Nenhuma foto facial válida no perfil da criança')

    yolo = YOLO('yolov8n.pt')
    captura = cv2.VideoCapture(contexto.camera.endereco_ip)
    if not captura.isOpened():
        captura.release()
        raise ConnectionError(
            f'Não foi possível abrir a câmera em {contexto.camera.endereco_ip}'
        )

    stop_event = stop_event or __import__('threading').Event()
    target_id = None
    target_embedding = None
    target_lost_frames = 0
    frame_count = 0
    verified_tracks = {}

    try:
        while not stop_event.is_set():
            sucesso, frame = captura.read()
            if not sucesso:
                break

            frame_count += 1
            results = yolo.track(
                frame,
                classes=[0],
                persist=True,
                conf=0.35,
                iou=0.5,
                verbose=False,
            )[0]

            boxes = results.boxes
            active_ids = set()
            if boxes is not None and boxes.id is not None:
                active_ids = set(boxes.id.cpu().numpy().astype(int))

            if target_id is not None:
                target_lost_frames = 0 if target_id in active_ids else target_lost_frames + 1

            verified_tracks = {
                track_id: data for track_id, data in verified_tracks.items()
                if frame_count - data['last_seen'] <= 90
            }

            if boxes is not None and boxes.id is not None:
                detected_boxes = boxes.xyxy.cpu().numpy().astype(int)
                track_ids = boxes.id.cpu().numpy().astype(int)
                altura, largura = frame.shape[:2]

                for box, track_id in zip(detected_boxes, track_ids):
                    x1, y1, x2, y2 = box
                    box = (
                        max(0, x1), max(0, y1),
                        min(largura, x2), min(altura, y2),
                    )
                    track_data = verified_tracks.get(track_id)
                    if track_data:
                        track_data['last_seen'] = frame_count

                    target_missing = target_id is None or target_id not in active_ids
                    should_recognize = (
                        track_data is None or
                        (track_id == target_id and frame_count % 10 == 0) or
                        (track_id != target_id and target_missing and frame_count % 5 == 0)
                    )

                    if should_recognize:
                        current_embedding = extrair_embedding_face(app, frame, box)
                        is_target = False
                        face_hidden = current_embedding is None

                        if current_embedding is not None:
                            reference_score = max(
                                np.dot(reference, current_embedding)
                                for reference in referencias
                            )
                            target_score = (
                                np.dot(target_embedding, current_embedding)
                                if target_embedding is not None else -1.0
                            )
                            is_target = reference_score >= 0.55 or target_score >= 0.58

                            if is_target:
                                target_id = track_id
                                target_lost_frames = 0
                                target_embedding = normalizar_embedding(
                                    current_embedding if target_embedding is None else
                                    target_embedding * 0.8 + current_embedding * 0.2
                                )
                            elif track_id == target_id:
                                target_id = None

                        verified_tracks[track_id] = {
                            'is_target': is_target,
                            'last_seen': frame_count,
                            'face_hidden': face_hidden,
                        }

                    track_data = verified_tracks.get(track_id, {})
                    if track_data.get('is_target') or track_id == target_id:
                        color = (0, 0, 255) if track_data.get('face_hidden') else (0, 255, 0)
                        cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, 2)

            if target_lost_frames > 150:
                target_id = None
                target_lost_frames = 0

            if on_frame:
                on_frame(frame, {
                    'usuario_id': str(contexto.usuario.id),
                    'camera_id': str(contexto.camera.id),
                    'target_id': target_id,
                })
    finally:
        captura.release()


def frame_para_base64(frame):
    sucesso, buffer = cv2.imencode('.jpg', frame)
    if not sucesso:
        return None
    return base64.b64encode(buffer).decode('ascii')
