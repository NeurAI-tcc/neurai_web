from datetime import datetime
from decimal import Decimal

from django.contrib.auth.hashers import check_password, make_password
from mongoengine import (
    BooleanField,
    BinaryField,
    CASCADE,
    DateTimeField,
    DecimalField,
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
    foto_perfil_url = BinaryField()
    nome_completo = StringField(required=True)
    nome_social = StringField()
    data_nascimento = DateTimeField()
    sexo = StringField()

    diagnostico_principal = StringField()
    nivel_suporte = StringField()
    data_diagnostico = DateTimeField()
    laudo_url = BinaryField()

    condicoes = ListField(StringField())
    alergias = ListField(StringField())
    usa_medicamentos = BooleanField(default=False)
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

    foto_frente_url = BinaryField()
    foto_direita_url = BinaryField()
    foto_esquerda_url = BinaryField()
    foto_cima_url = BinaryField()
    foto_baixo_url = BinaryField()
    foto_sorrindo_url = BinaryField()


class Usuario(Document):
    TIPO_USUARIO = ('Responsavel', 'Admin')
    ASSINATURA_PENDENTE = 'Pendente de aprovação'
    ASSINATURA_APROVADA = 'Aprovada'
    ASSINATURA_RECUSADA = 'Recusada'
    STATUS_ASSINATURA = (
        ASSINATURA_PENDENTE,
        ASSINATURA_APROVADA,
        ASSINATURA_RECUSADA,
    )

    tipo_usuario = StringField(choices=TIPO_USUARIO, default='Responsavel', required=True)
    nome_completo = StringField(required=True, max_length=150)
    email = StringField(required=True, unique=True, max_length=254)
    senha = StringField(required=True, max_length=128)
    ip_camera = StringField()
    pagamento_conta = StringField()
    valor = FloatField()
    status_assinatura = StringField(
        choices=STATUS_ASSINATURA,
        default=ASSINATURA_PENDENTE,
    )
    valor_mensal = DecimalField(
        precision=2, rounding='ROUND_HALF_UP', default=Decimal('50.00'),
    )
    data_solicitacao = DateTimeField(default=datetime.utcnow)
    inicio_cobranca = DateTimeField()
    aprovada_em = DateTimeField()
    recusada_em = DateTimeField()
    aprovada_por = ReferenceField('Usuario')
    motivo_recusa = StringField()
    atualizada_em = DateTimeField(default=datetime.utcnow)
    perfil_crianca = EmbeddedDocumentField(PerfilCrianca)
    criado_em = DateTimeField(default=datetime.utcnow)

    meta = {'collection': 'Usuarios', 'indexes': ['email']}

    def definir_senha(self, senha):
        self.senha = make_password(senha)

    def verificar_senha(self, senha):
        return check_password(senha, self.senha)


class Pagamento(Document):
    PENDENTE = 'Pendente'
    PAGO = 'Pago'
    ATRASADO = 'Atrasado'
    STATUS = (PENDENTE, PAGO, ATRASADO)

    usuario = ReferenceField(Usuario, required=True)
    valor = DecimalField(
        precision=2, rounding='ROUND_HALF_UP', default=Decimal('50.00'),
        required=True,
    )
    mes_competencia = IntField(required=True, min_value=1, max_value=12)
    ano_competencia = IntField(required=True, min_value=2000)
    vencimento = DateTimeField(required=True)
    pago_em = DateTimeField()
    status = StringField(choices=STATUS, default=PENDENTE, required=True)
    criado_em = DateTimeField(default=datetime.utcnow)
    atualizado_em = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'Pagamentos',
        'indexes': [
            {
                'fields': ['usuario', 'ano_competencia', 'mes_competencia'],
                'unique': True,
            },
            {'fields': ['status', '-vencimento']},
            ['usuario', '-vencimento'],
        ],
    }


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