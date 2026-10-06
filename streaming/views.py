import json
import secrets
from functools import wraps

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator

from .models import Usuario, TokenAcesso, Alerta, Camera, Relatorio


def serializar_usuario(usuario):
    perfil = None
    if usuario.perfil_crianca is not None:
        perfil = json.loads(usuario.perfil_crianca.to_json())
    return {
        'id': str(usuario.id), 'nome_completo': usuario.nome_completo,
        'email': usuario.email, 'tipo_usuario': usuario.tipo_usuario,
        'ip_camera': usuario.ip_camera, 'perfil_crianca': perfil,
    }


def serializar_rastreamento(usuario):
    camera = Camera.objects(responsavel=usuario).first()
    if camera is None:
        return {'camera': None, 'perfil_carregado': usuario.perfil_crianca is not None}
    return {
        'camera': {
            'id': str(camera.id),
            'endereco_ip': camera.endereco_ip,
            'nome_camara': camera.nome_camara,
        },
        'perfil_carregado': usuario.perfil_crianca is not None,
        'websocket': f'/ws/camera/{camera.id}/',
    }


def contexto_admin():
    usuarios = list(Usuario.objects.order_by('-criado_em'))
    cameras = list(Camera.objects.order_by('-id'))
    alertas = list(Alerta.objects.order_by('-timestamp'))
    tokens = list(TokenAcesso.objects)
    relatorios = list(Relatorio.objects.order_by('-data_geracao'))
    perfis_completos = sum(1 for usuario in usuarios if usuario.perfil_crianca is not None)
    receita = sum((usuario.valor or 0) for usuario in usuarios)
    return {
        'admin_name': 'Administrador',
        'usuarios': usuarios,
        'cameras': cameras,
        'alertas': alertas,
        'tokens': tokens,
        'relatorios': relatorios,
        'total_usuarios': len(usuarios),
        'usuarios_ativos': len(tokens),
        'total_cameras': len(cameras),
        'perfis_completos': perfis_completos,
        'perfis_pendentes': max(len(usuarios) - perfis_completos, 0),
        'receita': receita,
        'total_alertas': len(alertas),
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


def administrador(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        usuario_id = request.session.get('admin_usuario_id')
        if not usuario_id:
            return redirect(f'/login/?next={request.path}')
        try:
            usuario = Usuario.objects.get(id=usuario_id, tipo_usuario='Admin')
        except (Usuario.DoesNotExist, ValueError):
            request.session.pop('admin_usuario_id', None)
            return redirect(f'/login/?next={request.path}')
        request.admin_usuario = usuario
        return view(request, *args, **kwargs)
    return wrapper


def destino_admin(valor):
    if valor and valor.startswith('/') and not valor.startswith('//'):
        return valor
    return '/'


def login_admin(request):
    if request.session.get('admin_usuario_id'):
        return redirect(destino_admin(request.GET.get('next')))

    erro = None
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        senha = request.POST.get('senha', '')
        try:
            usuario = Usuario.objects.get(email=email, tipo_usuario='Admin')
        except (Usuario.DoesNotExist, ValueError):
            usuario = None

        if usuario is not None and usuario.verificar_senha(senha):
            request.session['admin_usuario_id'] = str(usuario.id)
            return redirect(destino_admin(request.POST.get('next')))
        erro = 'E-mail ou senha inválidos.'

    return render(request, 'login.html', {
        'erro': erro,
        'next': request.GET.get('next', ''),
    })


def logout_admin(request):
    request.session.pop('admin_usuario_id', None)
    return redirect('/login/')


def cadastro_admin(request):
    erro = None
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip().lower()
        codigo = request.POST.get('codigo_admin', '')
        senha = request.POST.get('senha', '')
        confirmar_senha = request.POST.get('confirmar_senha', '')

        if not settings.ADMIN_REGISTRATION_CODE:
            erro = 'O cadastro administrativo está temporariamente indisponível.'
        elif codigo != settings.ADMIN_REGISTRATION_CODE:
            erro = 'Código de administrador inválido.'
        elif not nome or not email or len(senha) < 8:
            erro = 'Preencha os campos obrigatórios e use uma senha com no mínimo 8 caracteres.'
        elif senha != confirmar_senha:
            erro = 'As senhas não conferem.'
        elif Usuario.objects(email=email).first() is not None:
            erro = 'Este e-mail já está cadastrado.'
        else:
            usuario = Usuario(
                nome_completo=nome,
                email=email,
                tipo_usuario='Admin',
            )
            usuario.senha = make_password(senha)
            usuario.save()
            return redirect('/login/')

    return render(request, 'cadastro_admin.html', {'erro': erro})


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
    return JsonResponse({
        'token': token.chave,
        'usuario': serializar_usuario(usuario),
        'rastreamento': serializar_rastreamento(usuario),
    })


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


@method_decorator(administrador, name='dispatch')
class DashboardAdminView(View):
    def get(self, request):
        return render(request, 'dashboard.html', contexto_admin())


@method_decorator(administrador, name='dispatch')
class AdminTemplateView(View):
    template_name = None

    def get(self, request):
        return render(request, self.template_name, contexto_admin())


class UsuariosAdminView(AdminTemplateView):
    template_name = 'usuarios.html'


class AssinantesAdminView(AdminTemplateView):
    template_name = 'assinantes.html'


class RelatoriosAdminView(AdminTemplateView):
    template_name = 'relatorios.html'


class FinanceiroAdminView(AdminTemplateView):
    template_name = 'financeiro.html'


class CadastrosAdminView(AdminTemplateView):
    template_name = 'cadastros.html'