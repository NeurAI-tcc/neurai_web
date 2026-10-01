from django.contrib import admin
from .models import Usuario, TokenAcesso, Alerta

admin.site.register((Usuario, TokenAcesso, Alerta))
