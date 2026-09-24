import json
from django.http import JsonResponse
from django.views import View
from django.shortcuts import render
from .models import Usuario, Alerta

# --- CONTROLLERS PARA O APLICATIVO FLUTTER (API REST) ---

class UsuarioPerfilAPI(View):
    def get(self, request, usuario_id):
        try:
            user = Usuario.objects.get(id=usuario_id)
            dados = {
                "id": str(user.id),
                "nome_completo": user.nome_completo,
                "email": user.email,
                "tipo_usuario": user.tipo_usuario,
                "perfil_crianca": user.perfil_crianca.to_mongo().to_dict() if user.perfil_crianca else None
            }
            return JsonResponse(dados, status=200)
        except Usuario.DoesNotExist:
            return JsonResponse({'erro': 'Usuário não encontrado'}, status=404)

class AlertasAPI(View):
    def get(self, request, responsavel_id):
        alertas = Alerta.objects(responsavel=responsavel_id).order_by('-timestamp')
        dados = [{"id": str(a.id), "tipo_crise": a.tipo_crise, "data": str(a.timestamp)} for a in alertas]
        return JsonResponse(dados, safe=False)

# --- CONTROLLERS PARA O PAINEL WEB (ADMIN) ---

class DashboardAdminView(View):
    def get(self, request):
        # Lógica para o painel de administrador na web
        responsaveis = Usuario.objects(tipo_usuario='Responsavel')
        total_responsaveis = responsaveis.count()
        
        contexto = {
            'total_clientes': total_responsaveis,
            'lista_responsaveis': responsaveis
        }
        # Retorna o template HTML (A View visual) do Django
        return render(request, 'admin_dashboard.html', contexto)