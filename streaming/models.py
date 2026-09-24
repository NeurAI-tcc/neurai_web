from mongoengine import Document, EmbeddedDocument, StringField, EmailField, BooleanField, DateTimeField, EmbeddedDocumentField, ReferenceField, ListField, DictField

# 1. Transformamos a Criança em um EmbeddedDocument
class Crianca(EmbeddedDocument):
    nome_completo = StringField(required=True)
    nome_social = StringField()
    data_nascimento = DateTimeField()
    sexo = StringField()
    
    # Informações Clínicas
    diagnostico_principal = StringField()
    nivel_suporte = StringField()
    data_diagnostico = DateTimeField()
    arquivo_laudo = StringField() 
    alergias = ListField(StringField())
    medicamentos = ListField(DictField()) 
    possui_crises_epileticas = BooleanField(default=False)
    frequencia_crises = StringField()
    
    # Perfil Comportamental
    atividades_favoritas = ListField(StringField())
    principais_gatilhos = ListField(StringField())
    ajuda_acalmar = ListField(StringField())
    forma_comunicacao = StringField()
    
    # Rotina Estruturada
    rotina = DictField() 
    seletividade_alimentar = BooleanField(default=False)
    info_importantes = StringField()
    
    # Imagens para o InsightFace
    fotos = DictField()

# 2. O Usuário agora contém a Criança
class Usuario(Document):
    meta = {'collection': 'usuarios'}
    tipo_usuario = StringField(choices=['Responsavel', 'Admin'], default='Responsavel')
    nome_completo = StringField(required=True)
    email = EmailField(required=True, unique=True)
    senha = StringField(required=True)
    ip_camera = StringField()
    
    # Dados financeiros visíveis apenas para o Admin
    pagamento_conta = StringField() 
    valor = StringField()
    
    # É aqui que a mágica acontece: o perfil da criança fica embutido no responsável.
    # Se o usuário for Admin, basta não preencher este campo no momento de salvar.
    perfil_crianca = EmbeddedDocumentField(Crianca)

# 3. Os alertas referenciam a conta do Usuário (Responsável)
class Alerta(Document):
    meta = {'collection': 'alertas'}
    # Como a criança agora vive dentro do usuário, o alerta aponta para a conta principal
    responsavel = ReferenceField(Usuario, required=True)
    timestamp = DateTimeField(required=True)
    tipo_crise = StringField(required=True)
    falso_positivo = BooleanField(default=False)