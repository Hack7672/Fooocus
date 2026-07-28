import unittest

from mente_zero.core.economia_atencao import PRECO_BASE_MIN
from mente_zero.core.models import (
    CategoriaApp,
    EventoUso,
    NivelRisco,
    Plano,
    TipoExercicio,
    TipoIntervencao,
)
from mente_zero.core.motor import COOLDOWN_AVISOS_S, SEGUNDOS_POR_DIA, MotorMenteZero


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


def rodar(motor, amostras, inicio=0.0, **kwargs):
    return [motor.processar(passiva(inicio + i * 5.0, **kwargs)) for i in range(amostras)]


class TestFluxoDeIntervencoes(unittest.TestCase):
    def test_uso_saudavel_nao_gera_intervencao(self):
        motor = MotorMenteZero()
        vistos = [
            motor.processar(
                passiva(
                    i * 5.0,
                    app_id="ebook",
                    categoria=CategoriaApp.LEITURA,
                    distancia_scroll_px=200.0,
                    toques=1,
                )
            )
            for i in range(200)
        ]
        self.assertTrue(all(not v.ativa for v in vistos))
        self.assertIs(motor.resumo().nivel, NivelRisco.CALMO)

    def test_scroll_stopper_tem_prioridade(self):
        motor = MotorMenteZero()
        vistos = rodar(motor, 24)
        self.assertIs(vistos[-1].tipo, TipoIntervencao.SCROLL_STOPPER)

    def test_escalada_ate_o_critico(self):
        motor = MotorMenteZero()
        tipos = set()
        for i in range(400):
            intervencao = motor.processar(passiva(i * 5.0))
            if intervencao.ativa:
                tipos.add(intervencao.tipo)
            if intervencao.tipo is TipoIntervencao.SCROLL_STOPPER:
                motor.stopper.responder(aceitou_desafio=False)
        self.assertIn(TipoIntervencao.SCROLL_STOPPER, tipos)
        self.assertIn(TipoIntervencao.MICRO_PAUSA_SENSORIAL, tipos)
        self.assertIs(motor.ivd.nivel, NivelRisco.CRITICO)

    def test_pro_recebe_mensagem_do_eu_futuro_no_critico(self):
        motor = MotorMenteZero(plano=Plano.PRO)
        tipos = set()
        for i in range(400):
            intervencao = motor.processar(passiva(i * 5.0))
            if intervencao.ativa:
                tipos.add(intervencao.tipo)
            if intervencao.tipo is TipoIntervencao.SCROLL_STOPPER:
                motor.stopper.responder(aceitou_desafio=False)
        self.assertIn(TipoIntervencao.MENSAGEM_EU_FUTURO, tipos)
        self.assertNotIn(TipoIntervencao.MICRO_PAUSA_SENSORIAL, tipos)

    def test_micro_pausa_traz_estimulo_real(self):
        motor = MotorMenteZero(plano=Plano.FREE)
        intervencao = motor._intervencao_critica(passiva(0.0))
        self.assertIs(intervencao.tipo, TipoIntervencao.MICRO_PAUSA_SENSORIAL)
        self.assertEqual(intervencao.payload["tela"], "preta")
        self.assertTrue(intervencao.payload["respiracao_guiada"])
        self.assertTrue(intervencao.payload["som"])
        self.assertTrue(intervencao.mensagem)

    def test_cooldown_evita_spam_de_avisos(self):
        motor = MotorMenteZero(plano=Plano.PRO)
        avisos = []
        for i in range(400):
            intervencao = motor.processar(passiva(i * 5.0))
            if intervencao.tipo in (
                TipoIntervencao.ALERTA_SUAVE,
                TipoIntervencao.TAREFA_RELAMPAGO,
                TipoIntervencao.MICRO_PAUSA_SENSORIAL,
                TipoIntervencao.MENSAGEM_EU_FUTURO,
            ):
                avisos.append(i * 5.0)
            if intervencao.tipo is TipoIntervencao.SCROLL_STOPPER:
                motor.stopper.responder(aceitou_desafio=False)
        for anterior, seguinte in zip(avisos, avisos[1:]):
            self.assertGreaterEqual(seguinte - anterior, COOLDOWN_AVISOS_S)

    def test_tarefa_relampago_carrega_exercicio(self):
        motor = MotorMenteZero(plano=Plano.PRO)
        exercicios = []
        for i in range(400):
            intervencao = motor.processar(passiva(i * 5.0))
            if intervencao.tipo is TipoIntervencao.TAREFA_RELAMPAGO:
                exercicios.append(intervencao.payload["exercicio"])
            if intervencao.tipo is TipoIntervencao.SCROLL_STOPPER:
                motor.stopper.responder(aceitou_desafio=False)
        self.assertTrue(exercicios)
        self.assertTrue(all(e.enunciado for e in exercicios))


class TestEconomiaNoMotor(unittest.TestCase):
    def test_acesso_gasta_moeda_ate_esgotar(self):
        motor = MotorMenteZero(plano=Plano.FREE)
        for _ in range(4):
            self.assertTrue(motor.solicitar_acesso("instagram")["liberado"])
        negado = motor.solicitar_acesso("instagram")
        self.assertFalse(negado["liberado"])
        self.assertEqual(negado["preco_min"], PRECO_BASE_MIN)

    def test_leilao_libera_quando_o_preco_e_pago(self):
        motor = MotorMenteZero(plano=Plano.FREE)
        for _ in range(4):
            motor.solicitar_acesso("instagram")
        liberado = motor.solicitar_acesso("instagram", minutos_exercicio=PRECO_BASE_MIN)
        self.assertTrue(liberado["liberado"])
        self.assertEqual(liberado["via"], "leilao")
        self.assertGreater(liberado["preco_min"], PRECO_BASE_MIN)

    def test_exercicio_correto_devolve_moeda(self):
        motor = MotorMenteZero(plano=Plano.PRO)
        for _ in range(6):
            motor.solicitar_acesso("instagram")
        self.assertEqual(motor.banco.saldo, 0)
        exercicio = motor.proximo_exercicio(TipoExercicio.LOGICA)
        motor.responder_exercicio(exercicio, exercicio.resposta, tempo_s=5.0)
        self.assertEqual(motor.banco.saldo, 1)

    def test_missao_offline_so_credita_no_pro(self):
        free = MotorMenteZero(plano=Plano.FREE)
        free.banco.gastar(4)
        free.concluir_missao_offline("praca-central")
        self.assertEqual(free.banco.saldo, 0)

        pro = MotorMenteZero(plano=Plano.PRO)
        pro.banco.gastar(6)
        pro.concluir_missao_offline("praca-central")
        self.assertEqual(pro.banco.saldo, 1)

    def test_virada_de_dia_recarrega_tudo(self):
        motor = MotorMenteZero(plano=Plano.FREE)
        motor.processar(passiva(0.0))
        for _ in range(4):
            motor.solicitar_acesso("instagram")
        motor.solicitar_acesso("instagram", minutos_exercicio=PRECO_BASE_MIN)
        motor.proximo_exercicio()

        motor.processar(passiva(SEGUNDOS_POR_DIA + 10.0))
        self.assertEqual(motor.banco.saldo, 4)
        self.assertEqual(motor.leilao.preco_min("instagram"), PRECO_BASE_MIN)
        self.assertEqual(motor.escala.restantes_hoje(), 1)
        self.assertEqual(motor.intervencoes_hoje, 0)

    def test_resumo_reflete_o_estado(self):
        motor = MotorMenteZero(plano=Plano.PRO)
        rodar(motor, 30)
        resumo = motor.resumo()
        self.assertGreater(resumo.ivd, 0.0)
        self.assertEqual(resumo.moedas, 6)
        self.assertGreater(resumo.tela_passiva_s, 0.0)
        self.assertGreaterEqual(resumo.intervencoes_hoje, 1)


if __name__ == "__main__":
    unittest.main()
