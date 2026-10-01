import json

from django.test import TestCase
from channels.testing import WebsocketCommunicator

from .models import Usuario, TokenAcesso, Alerta
from neurai_core.asgi import application


class BackendApiTests(TestCase):
	def setUp(self):
		self.usuario = Usuario.objects.create(
			nome_completo='Responsável Teste', email='teste@example.com', ip_camera='192.168.0.50')
		self.usuario.definir_senha('senha-segura')
		self.usuario.save()
		self.token = TokenAcesso.objects.create(usuario=self.usuario, chave='token-de-teste')

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
		self.assertEqual(perfil.json()['email'], 'teste@example.com')
		camera = self.client.get('/api/camera/', **self.auth())
		self.assertEqual(camera.json()['ip_camera'], '192.168.0.50')

	def test_alertas_do_responsavel(self):
		Alerta.objects.create(responsavel=self.usuario, tipo_crise='queda', timestamp='2026-01-01T12:00:00Z')
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
