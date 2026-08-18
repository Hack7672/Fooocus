import http.client
import json
import threading
import unittest

from mente_zero.core.models import Plano
from mente_zero.webapp import criar_servidor


class TestWebapp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.servidor = criar_servidor(Plano.PRO, porta=0)
        cls.porta = cls.servidor.server_address[1]
        cls.thread = threading.Thread(target=cls.servidor.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()

    def _req(self, metodo, caminho, corpo=None):
        conexao = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=5)
        headers = {"Content-Type": "application/json"} if corpo is not None else {}
        conexao.request(metodo, caminho, json.dumps(corpo) if corpo is not None else None, headers)
        resposta = conexao.getresponse()
        dados = resposta.read()
        conexao.close()
        return resposta.status, dados

    def test_pagina_inicial(self):
        status, corpo = self._req("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"MENTE ZERO", corpo)

    def test_estado_inicial(self):
        status, corpo = self._req("GET", "/api/estado")
        self.assertEqual(status, 200)
        estado = json.loads(corpo)
        self.assertEqual(estado["plano"], "pro")
        self.assertIn("ivd", estado)
        self.assertIn("simulador_perda", estado)
        self.assertIn("aviso", estado["simulador_perda"])

    def test_uso_compulsivo_gera_intervencao(self):
        status, corpo = self._req(
            "POST", "/api/evento", {"modo": "compulsivo", "segundos": 600}
        )
        self.assertEqual(status, 200)
        dados = json.loads(corpo)
        self.assertTrue(dados["intervencoes"])
        self.assertGreater(dados["estado"]["ivd"], 25.0)
        # destrava o stopper para os demais testes
        self._req("POST", "/api/stopper", {"aceitou": True})

    def test_ciclo_de_exercicio(self):
        status, corpo = self._req("POST", "/api/exercicio", {})
        self.assertEqual(status, 200)
        exercicio = json.loads(corpo)
        self.assertIn("enunciado", exercicio)

        status, corpo = self._req(
            "POST", "/api/responder", {"resposta": "chute errado", "tempo_s": 3.0}
        )
        self.assertEqual(status, 200)
        resultado = json.loads(corpo)
        self.assertIn("correto", resultado)
        self.assertIn("gabarito", resultado)

    def test_responder_sem_exercicio_pendente(self):
        self._req("POST", "/api/exercicio", {})
        self._req("POST", "/api/responder", {"resposta": "x", "tempo_s": 1.0})
        status, corpo = self._req("POST", "/api/responder", {"resposta": "x", "tempo_s": 1.0})
        self.assertEqual(status, 200)
        self.assertIn("erro", json.loads(corpo))

    def test_acesso_consome_moeda(self):
        status, corpo = self._req(
            "POST", "/api/acesso", {"app": "instagram", "minutos_exercicio": 0}
        )
        self.assertEqual(status, 200)
        dados = json.loads(corpo)
        self.assertIn("liberado", dados)
        self.assertIn("preco_min", dados)

    def test_rota_desconhecida(self):
        status, _ = self._req("GET", "/api/nada")
        self.assertEqual(status, 404)
        status, _ = self._req("POST", "/api/nada", {})
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
