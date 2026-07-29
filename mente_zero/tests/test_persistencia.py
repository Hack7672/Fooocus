import json
import unittest

from mente_zero.core.models import CategoriaApp, EventoUso, Plano
from mente_zero.core.motor import MotorMenteZero
from mente_zero.core.persistencia import EsquemaIncompativel, carregar, salvar


def passiva(t, **kwargs):
    padrao = dict(
        timestamp=t,
        app_id="feedapp",
        categoria=CategoriaApp.FEED_SOCIAL,
        duracao_s=5.0,
        distancia_scroll_px=6000.0,
        toques=0,
    )
    padrao.update(kwargs)
    return EventoUso(**padrao)


def aquecer(motor, amostras=40):
    for i in range(amostras):
        motor.processar(passiva(i * 5.0, abertura_app=(i == 0)))


class TestPersistencia(unittest.TestCase):
    def test_snapshot_e_json_serializavel(self):
        motor = MotorMenteZero(plano=Plano.PRO, semente=7)
        aquecer(motor)
        motor.solicitar_acesso("instagram")
        motor.proximo_exercicio()
        dados = salvar(motor)
        recuperado = json.loads(json.dumps(dados))
        self.assertEqual(recuperado["plano"], "pro")

    def test_roundtrip_preserva_estado_visivel(self):
        motor = MotorMenteZero(
            plano=Plano.FREE, apps_mapeados=frozenset({"reels"}), semente=3
        )
        aquecer(motor)
        motor.solicitar_acesso("instagram")
        motor.solicitar_acesso("instagram")
        exercicio = motor.proximo_exercicio()
        motor.responder_exercicio(exercicio, "errado", tempo_s=99.0)

        clone = carregar(json.loads(json.dumps(salvar(motor))))

        self.assertEqual(clone.plano, motor.plano)
        self.assertEqual(clone.apps_mapeados, motor.apps_mapeados)
        self.assertAlmostEqual(clone.ivd.valor, motor.ivd.valor)
        self.assertEqual(clone.banco.saldo, motor.banco.saldo)
        self.assertEqual(clone.escala.nivel, motor.escala.nivel)
        self.assertEqual(clone.escala.entregues_hoje, motor.escala.entregues_hoje)
        self.assertEqual(clone.stopper.estado, motor.stopper.estado)
        self.assertEqual(clone.intervencoes_hoje, motor.intervencoes_hoje)

    def test_clone_reage_igual_ao_original(self):
        motor = MotorMenteZero(plano=Plano.PRO, semente=11)
        aquecer(motor, 30)
        clone = carregar(salvar(motor))

        for i in range(30, 120):
            evento = passiva(i * 5.0)
            a = motor.processar(evento)
            b = clone.processar(evento)
            self.assertEqual(a.tipo, b.tipo, f"divergência no passo {i}")
            self.assertAlmostEqual(motor.ivd.valor, clone.ivd.valor)

    def test_escala_do_clone_gera_a_mesma_prova(self):
        motor = MotorMenteZero(plano=Plano.PRO, semente=42)
        motor.proximo_exercicio()
        clone = carregar(salvar(motor))
        for _ in range(5):
            self.assertEqual(motor.proximo_exercicio().id, clone.proximo_exercicio().id)

    def test_versao_desconhecida_e_rejeitada(self):
        motor = MotorMenteZero()
        dados = salvar(motor)
        dados["versao"] = 99
        with self.assertRaises(EsquemaIncompativel):
            carregar(dados)


if __name__ == "__main__":
    unittest.main()
