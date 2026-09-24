from mongoengine import Document, StringField

class CameraUser(Document):
    nome_paciente = StringField(required=True)
    ip_camera = StringField(required=True)
    
    meta = {'collection': 'cameras'}