import json
from datetime import datetime, timedelta
from uuid import uuid4

from django.contrib.auth.hashers import make_password
from django.test import TestCase
from channels.testing import WebsocketCommunicator

from .models import Alerta, Pagamento, TokenAcesso, Usuario
from .views import gerar_pagamentos_da_assinatura
from neurai_core.asgi import application


class BackendApiTests(TestCase):
	def setUp(self):
		identificador = uuid4().hex
		self.email = f'teste-{identificador}@example.com'
		self.usuario = Usuario.objects.create(
			nome_completo='Responsável Teste', email=self.email,
			ip_camera='192.168.0.50', senha=make_password('senha-segura'))
		self.token = TokenAcesso.objects.create(
			usuario=self.usuario, chave=f'token-de-teste-{identificador}')

	def auth(self):
		return {'HTTP_AUTHORIZATION': f'Bearer {self.token.chave}'}

	def test_cadastro_e_login(self):
		cadastro = self.client.post('/api/auth/cadastro/', data=json.dumps({
			'nome_completo': 'Novo Usuário', 'email': 'novo@example.com', 'senha': '123456'}),
			content_type='application/json')
		self.assertEqual(cadastro.status_code, 201)
		login = self.client.post('/api/auth/login/', data=json.dumps({
			'email': 'novo@example.com', 'senha': '123456'}), content_type='application/json')
		self.assertEqual(login.status_code, 200)
		self.assertTrue(login.json()['token'])

	def test_rotas_protegidas_e_dados_da_camera(self):
		self.assertEqual(self.client.get('/api/perfil/').status_code, 401)
		perfil = self.client.get('/api/perfil/', **self.auth())
		self.assertEqual(perfil.json()['email'], self.email)
		camera = self.client.get('/api/camera/', **self.auth())
		self.assertEqual(camera.json()['ip_camera'], '192.168.0.50')

	def test_alertas_do_responsavel(self):
		Alerta.objects.create(
			responsavel=self.usuario,
			tipo_crise='queda',
			timestamp=datetime(2026, 1, 1, 12, 0),
		)
		resposta = self.client.get('/api/alertas/', **self.auth())
		self.assertEqual(resposta.status_code, 200)
		self.assertEqual(resposta.json()[0]['tipo_crise'], 'queda')

	def test_dashboard(self):
		resposta = self.client.get('/')
		self.assertEqual(resposta.status_code, 200)
		self.assertContains(resposta, 'Responsável Teste')

	async def test_websocket_alertas_exige_token(self):
		communicator = WebsocketCommunicator(
			application, f'/ws/alertas/{self.usuario.id}/?token={self.token.chave}')
		conectado, _ = await communicator.connect()
		self.assertTrue(conectado)
		await communicator.disconnect()

	def test_assinatura_aprovada_gera_uma_cobranca_por_competencia(self):
		agora = datetime.utcnow()
		self.usuario.status_assinatura = Usuario.ASSINATURA_APROVADA
		self.usuario.inicio_cobranca = agora.replace(day=1)
		self.usuario.aprovada_em = agora
		self.usuario.save()

		gerar_pagamentos_da_assinatura(self.usuario, agora)
		gerar_pagamentos_da_assinatura(self.usuario, agora)

		self.assertEqual(Pagamento.objects(usuario=self.usuario).count(), 1)
		pagamento = Pagamento.objects.get(usuario=self.usuario)
		self.assertEqual(str(pagamento.valor), '50.00')

	def test_assinatura_recusada_nao_gera_cobranca(self):
		self.usuario.status_assinatura = Usuario.ASSINATURA_RECUSADA
		self.usuario.recusada_em = datetime.utcnow()
		self.usuario.save()

		self.assertEqual(gerar_pagamentos_da_assinatura(self.usuario), [])
		self.assertEqual(Pagamento.objects(usuario=self.usuario).count(), 0)

	def test_competencia_vencida_fica_atrasada(self):
		agora = datetime.utcnow()
		inicio = agora.replace(day=1) - timedelta(days=1)
		self.usuario.status_assinatura = Usuario.ASSINATURA_APROVADA
		self.usuario.inicio_cobranca = inicio
		self.usuario.aprovada_em = inicio
		self.usuario.save()

		gerar_pagamentos_da_assinatura(self.usuario, agora)

		pagamento_anterior = Pagamento.objects(
			usuario=self.usuario,
			ano_competencia=inicio.year,
			mes_competencia=inicio.month,
		).first()
		self.assertEqual(pagamento_anterior.status, Pagamento.ATRASADO)
