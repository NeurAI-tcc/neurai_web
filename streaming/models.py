from django.db import models
from django.contrib.auth.hashers import check_password, make_password


class Usuario(models.Model):
    TIPO_USUARIO = [('Responsavel', 'Responsável'), ('Admin', 'Administrador')]

    tipo_usuario = models.CharField(max_length=20, choices=TIPO_USUARIO, default='Responsavel')
    nome_completo = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    senha = models.CharField(max_length=128)
    ip_camera = models.GenericIPAddressField(null=True, blank=True)
    pagamento_conta = models.CharField(max_length=100, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    perfil_crianca = models.JSONField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def definir_senha(self, senha):
        self.senha = make_password(senha)

    def verificar_senha(self, senha):
        return check_password(senha, self.senha)


class TokenAcesso(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='token_acesso')
    chave = models.CharField(max_length=64, unique=True)
    criado_em = models.DateTimeField(auto_now_add=True)


class Alerta(models.Model):
    responsavel = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='alertas')
    timestamp = models.DateTimeField()
    tipo_crise = models.CharField(max_length=100)
    falso_positivo = models.BooleanField(default=False)
    detalhes = models.JSONField(default=dict, blank=True)