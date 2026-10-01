import json
import secrets
from functools import wraps

from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.shortcuts import render

from .models import Usuario, TokenAcesso, Alerta, Camera


def serializar_usuario(usuario):
    perfil = None
    if usuario.perfil_crianca is not None:
        perfil = json.loads(usuario.perfil_crianca.to_json())
    return {
        'id': str(usuario.id), 'nome_completo': usuario.nome_completo,
        'email': usuario.email, 'tipo_usuario': usuario.tipo_usuario,
        'ip_camera': usuario.ip_camera, 'perfil_crianca': perfil,
    }


def ler_json(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        raise ValueError('JSON inválido')


def autenticado(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        valor = request.headers.get('Authorization', '')
        chave = valor.removeprefix('Bearer ').strip()
        try:
            request.usuario = TokenAcesso.objects.get(chave=chave).usuario
        except (TokenAcesso.DoesNotExist, TokenAcesso.MultipleObjectsReturned):
            return JsonResponse({'erro': 'Token ausente ou inválido'}, status=401)
        return view(request, *args, **kwargs)
    return wrapper


@csrf_exempt
def login_api(request):
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método não permitido'}, status=405)
    try:
        dados = ler_json(request)
        usuario = Usuario.objects.get(email=dados.get('email', '').lower())
    except (ValueError, Usuario.DoesNotExist):
        return JsonResponse({'erro': 'E-mail ou senha inválidos'}, status=401)
    if not usuario.verificar_senha(dados.get('senha', '')):
        return JsonResponse({'erro': 'E-mail ou senha inválidos'}, status=401)
    token = TokenAcesso.objects(usuario=usuario).first()
    if token is None:
        token = TokenAcesso(usuario=usuario, chave=secrets.token_urlsafe(32))
    else:
        token.chave = secrets.token_urlsafe(32)
    token.save()
    return JsonResponse({'token': token.chave, 'usuario': serializar_usuario(usuario)})


@csrf_exempt
def cadastro_api(request):
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método não permitido'}, status=405)
    try:
        dados = ler_json(request)
        email = dados['email'].lower().strip()
        if not dados.get('nome_completo') or len(dados.get('senha', '')) < 6:
            raise ValueError('nome_completo e senha com no mínimo 6 caracteres são obrigatórios')
        if Usuario.objects(email=email).first() is not None:
            return JsonResponse({'erro': 'E-mail já cadastrado'}, status=409)
        usuario = Usuario(nome_completo=dados['nome_completo'], email=email,
                          ip_camera=dados.get('ip_camera'),
                          perfil_crianca=dados.get('perfil_crianca'))
        usuario.senha = make_password(dados['senha'])
        usuario.save()
    except (KeyError, ValueError):
        return JsonResponse({'erro': 'Dados de cadastro inválidos'}, status=400)
    return JsonResponse(serializar_usuario(usuario), status=201)


@autenticado
def perfil_api(request):
    return JsonResponse(serializar_usuario(request.usuario))


@autenticado
def alertas_api(request):
    alertas = Alerta.objects(responsavel=request.usuario).order_by('-timestamp')[:100]
    return JsonResponse([{'id': str(a.id), 'tipo_crise': a.tipo_crise,
                          'timestamp': a.timestamp.isoformat(),
                          'falso_positivo': a.falso_positivo,
                          'detalhes': a.detalhes} for a in alertas], safe=False)


@autenticado
@csrf_exempt
def camera_api(request):
    if request.method == 'GET':
        camera = Camera.objects(responsavel=request.usuario).first()
        if camera is None:
            return JsonResponse({'camera': None})
        return JsonResponse({
            'camera': {
                'id': str(camera.id),
                'endereco_ip': camera.endereco_ip,
                'nome_camara': camera.nome_camara,
                'localizacao': camera.localizacao,
                'modelo': camera.modelo,
            },
            'websocket': f'/ws/camera/{camera.id}/',
        })

    if request.method != 'POST':
        return JsonResponse({'erro': 'Método não permitido'}, status=405)
    try:
        dados = ler_json(request)
        endereco_ip = dados['endereco_ip'].strip()
        nome_camara = dados.get('nome_camara', 'Câmera principal').strip()
        if not endereco_ip or not nome_camara:
            raise ValueError
    except (KeyError, AttributeError, ValueError):
        return JsonResponse({'erro': 'endereco_ip e nome_camara são obrigatórios'}, status=400)

    camera = Camera.objects(responsavel=request.usuario).first()
    if camera is None:
        camera = Camera(responsavel=request.usuario, endereco_ip=endereco_ip,
                        nome_camara=nome_camara)
    else:
        camera.endereco_ip = endereco_ip
        camera.nome_camara = nome_camara
    camera.localizacao = dados.get('localizacao', camera.localizacao)
    camera.modelo = dados.get('modelo', camera.modelo)
    camera.save()

    request.usuario.ip_camera = endereco_ip
    request.usuario.save()
    return JsonResponse({
        'camera': {
            'id': str(camera.id),
            'endereco_ip': camera.endereco_ip,
            'nome_camara': camera.nome_camara,
        },
        'websocket': f'/ws/camera/{camera.id}/',
    }, status=201)


class DashboardAdminView(View):
    def get(self, request):
        responsaveis = Usuario.objects(tipo_usuario='Responsavel').order_by('nome_completo')
        return render(request, 'admin_dashboard.html', {'total_clientes': responsaveis.count(),
                                                         'lista_responsaveis': responsaveis})