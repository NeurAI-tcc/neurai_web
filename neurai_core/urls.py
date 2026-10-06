"""
URL configuration for neurai_core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from streaming import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/cadastro/', views.cadastro_api),
    path('api/auth/login/', views.login_api),
    path('api/perfil/', views.perfil_api),
    path('api/alertas/', views.alertas_api),
    path('api/camera/', views.camera_api),
    path('', views.DashboardAdminView.as_view(), name='dashboard'),
    path('login/', views.login_admin, name='login'),
    path('logout/', views.logout_admin, name='logout'),
    path('cadastro-admin/', views.cadastro_admin, name='cadastro_admin'),
    path('usuarios/', views.UsuariosAdminView.as_view(), name='usuarios'),
    path('assinantes/', views.AssinantesAdminView.as_view(), name='assinantes'),
    path('relatorios/', views.RelatoriosAdminView.as_view(), name='relatorios'),
    path('financeiro/', views.FinanceiroAdminView.as_view(), name='financeiro'),
    path('cadastros/', views.CadastrosAdminView.as_view(), name='cadastros'),
]
