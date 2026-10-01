from datetime import datetime

from django.contrib.auth.hashers import check_password, make_password
from mongoengine import (
    BooleanField,
    CASCADE,
    DateTimeField,
    DictField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentField,
    FloatField,
    IntField,
    ListField,
    ReferenceField,
    StringField,
)


class PerfilCrianca(EmbeddedDocument):
    foto_perfil_url = StringField()
    nome_completo = StringField(required=True)
    nome_social = StringField()
    data_nascimento = DateTimeField()
    sexo = StringField()

    diagnostico_principal = StringField()
    nivel_suporte = StringField()
    data_diagnostico = DateTimeField()
    laudo_url = StringField()

    condicoes = ListField(StringField())
    alergias = ListField(StringField())
    medicacoes = ListField(DictField())
    possui_crises_epilepticas = BooleanField(default=False)
    frequencia_crises = StringField()

    atividades_favoritas = ListField(StringField())
    gatilhos = ListField(StringField())
    o_que_ajuda_acalmar = ListField(StringField())
    comunicacao = StringField()

    horario_acordar = StringField()
    horario_dormir = StringField()
    possui_sonecas = BooleanField(default=False)
    alimentacao = ListField(StringField())
    seletividade_alimentar = BooleanField(default=False)
    atividades = ListField(StringField())

    observacoes = StringField()
    contato_emergencia = StringField()
    relacao_com_crianca = StringField()

    foto_frente_url = StringField()
    foto_direita_url = StringField()
    foto_esquerda_url = StringField()
    foto_cima_url = StringField()
    foto_baixo_url = StringField()
    foto_sorrindo_url = StringField()


class Usuario(Document):
    TIPO_USUARIO = ('Responsavel', 'Admin')

    tipo_usuario = StringField(choices=TIPO_USUARIO, default='Responsavel', required=True)
    nome_completo = StringField(required=True, max_length=150)
    email = StringField(required=True, unique=True, max_length=254)
    senha = StringField(required=True, max_length=128)
    ip_camera = StringField()
    pagamento_conta = StringField()
    valor = FloatField()
    perfil_crianca = EmbeddedDocumentField(PerfilCrianca)
    criado_em = DateTimeField(default=datetime.utcnow)

    meta = {'collection': 'usuarios', 'indexes': ['email']}

    def definir_senha(self, senha):
        self.senha = make_password(senha)

    def verificar_senha(self, senha):
        return check_password(senha, self.senha)


class TokenAcesso(Document):
    usuario = ReferenceField(Usuario, required=True, unique=True, reverse_delete_rule=CASCADE)
    chave = StringField(required=True, unique=True, max_length=128)
    criado_em = DateTimeField(default=datetime.utcnow)

    meta = {'collection': 'tokens_acesso', 'indexes': ['chave', 'usuario']}


class Camera(Document):
    responsavel = ReferenceField(Usuario, required=True, reverse_delete_rule=CASCADE)
    endereco_ip = StringField(required=True)
    nome_camara = StringField(required=True)
    localizacao = StringField()
    modelo = StringField()

    meta = {'collection': 'cameras', 'indexes': ['responsavel']}


class Alerta(Document):
    responsavel = ReferenceField(Usuario, required=True, reverse_delete_rule=CASCADE)
    camara = ReferenceField(Camera, reverse_delete_rule=CASCADE)
    timestamp = DateTimeField(required=True, default=datetime.utcnow)
    tipo_crise = StringField(required=True, max_length=100)
    falso_positivo = BooleanField(default=False)
    detalhes = DictField(default=dict)
    nivel_confianca_ia = FloatField(min_value=0, max_value=1)
    video_clip_url = StringField()

    meta = {'collection': 'alertas', 'indexes': ['-timestamp', 'responsavel', 'camara']}


class Relatorio(Document):
    responsavel = ReferenceField(Usuario, required=True, reverse_delete_rule=CASCADE)
    mes_referencia = StringField(required=True)
    data_geracao = DateTimeField(default=datetime.utcnow)
    total_crises_mes = IntField(default=0, min_value=0)
    gatilhos_mais_frequentes = ListField(DictField())
    horario_pico_crises = StringField()

    meta = {'collection': 'relatorios', 'indexes': ['responsavel', 'mes_referencia']}