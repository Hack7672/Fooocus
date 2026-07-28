import unittest

from mente_zero.core.economia_atencao import (
    DURACAO_TELA_CINZA_S,
    JANELA_RESPOSTA_S,
    LIMITE_JANELA_REFLEXAO_S,
    LIMITE_ROLAGEM_PASSIVA_S,
    PRECO_BASE_MIN,
    PRECO_TETO_MIN,
    TETO_MOEDAS_CONQUISTADAS,
    BancoDeMinutos,
    EstadoStopper,
    LeilaoDeDistracoes,
    SaldoInsuficiente,
    ScrollStopper,
)
from mente_zero.core.models import CategoriaApp, EventoUso, Plano, TipoIntervencao


def passiva(t, **kwargs):
    padrao = dict(
        timestamp=t,
        app_id="feedapp",
        categoria=CategoriaApp.FEED_SOCIAL,
        duracao_s=5.0,
        distancia_scroll_px=4000.0,
        toques=0,
    )
    padrao.update(kwargs)
    return EventoUso(**padrao)


class TestScrollStopper(unittest.TestCase):
    def test_congela_apos_dois_minutos_de_rolagem_passiva(self):
        stopper = ScrollStopper()
        vistas = [stopper.registrar(passiva(i * 5.0)) for i in range(24)]
        tipos = [v.tipo for v in vistas]
        self.assertEqual(tipos.count(TipoIntervencao.SCROLL_STOPPER), 1)
        self.assertIs(vistas[-1].tipo, TipoIntervencao.SCROLL_STOPPER)
        self.assertGreaterEqual(
            vistas[-1].payload["rolagem_passiva_s"], LIMITE_ROLAGEM_PASSIVA_S
        )
        self.assertIs(stopper.estado, EstadoStopper.CONGELADO)

    def test_congelamento_ignorado_vira_tela_cinza(self):
        stopper = ScrollStopper()
        t = 0.0
        while stopper.estado is not EstadoStopper.CONGELADO:
            stopper.registrar(passiva(t))
            t += 5.0
        cinza = stopper.registrar(passiva(t + JANELA_RESPOSTA_S))
        self.assertIs(cinza.tipo, TipoIntervencao.TELA_CINZA)
        self.assertEqual(cinza.duracao_s, DURACAO_TELA_CINZA_S)

    def test_aceitar_desafio_reinicia_o_ciclo(self):
        stopper = ScrollStopper()
        t = 0.0
        while stopper.estado is not EstadoStopper.CONGELADO:
            stopper.registrar(passiva(t))
            t += 5.0
        stopper.responder(aceitou_desafio=True)
        self.assertIs(stopper.estado, EstadoStopper.OBSERVANDO)
        self.assertEqual(stopper.passivo_acumulado_s, 0.0)
        self.assertIs(stopper.registrar(passiva(t + 5.0)).tipo, TipoIntervencao.NENHUMA)

    def test_interacao_intencional_alivia_o_acumulador(self):
        stopper = ScrollStopper()
        for i in range(48):  # 4 minutos, mas sempre com toque
            intervencao = stopper.registrar(passiva(i * 5.0, toques=2))
            self.assertIs(intervencao.tipo, TipoIntervencao.NENHUMA)

    def test_free_so_age_em_apps_mapeados(self):
        stopper = ScrollStopper(plano=Plano.FREE, apps_mapeados=frozenset({"instagram"}))
        for i in range(48):
            intervencao = stopper.registrar(passiva(i * 5.0, app_id="appdesconhecido"))
            self.assertIs(intervencao.tipo, TipoIntervencao.NENHUMA)

    def test_pro_age_em_qualquer_app_de_distracao(self):
        stopper = ScrollStopper(plano=Plano.PRO, apps_mapeados=frozenset({"instagram"}))
        vistos = [stopper.registrar(passiva(i * 5.0, app_id="novoapp")) for i in range(24)]
        self.assertIs(vistos[-1].tipo, TipoIntervencao.SCROLL_STOPPER)

    def test_janela_de_reflexao_apos_25_minutos_de_tela_passiva(self):
        stopper = ScrollStopper()
        t = 0.0
        tipos = []
        while stopper.passivo_total_sessao_s < LIMITE_JANELA_REFLEXAO_S + 10:
            tipos.append(stopper.registrar(passiva(t)).tipo)
            if stopper.estado is EstadoStopper.CONGELADO:
                stopper.responder(aceitou_desafio=False)
            t += 5.0
        self.assertIn(TipoIntervencao.JANELA_REFLEXAO, tipos)


class TestBancoDeMinutos(unittest.TestCase):
    def test_saldo_inicial_por_plano(self):
        self.assertEqual(BancoDeMinutos(plano=Plano.FREE).saldo, 4)
        self.assertEqual(BancoDeMinutos(plano=Plano.PRO).saldo, 6)

    def test_gasto_e_saldo_insuficiente(self):
        banco = BancoDeMinutos(plano=Plano.FREE)
        for esperado in (3, 2, 1, 0):
            self.assertEqual(banco.gastar(), esperado)
        self.assertFalse(banco.pode_gastar())
        with self.assertRaises(SaldoInsuficiente):
            banco.gastar()

    def test_exercicio_credita_ate_o_teto(self):
        banco = BancoDeMinutos(plano=Plano.FREE)
        for _ in range(4):
            banco.gastar()
        for _ in range(10):
            banco.creditar(1, origem="exercicio")
        self.assertEqual(banco.saldo, TETO_MOEDAS_CONQUISTADAS)

    def test_missao_offline_credita_apenas_no_pro(self):
        free = BancoDeMinutos(plano=Plano.FREE)
        free.creditar(1, origem="missao_offline")
        self.assertEqual(free.saldo, 4)

        pro = BancoDeMinutos(plano=Plano.PRO)
        pro.creditar(1, origem="missao_offline")
        self.assertEqual(pro.saldo, 7)

    def test_moedas_nao_acumulam_entre_dias(self):
        banco = BancoDeMinutos(plano=Plano.PRO, dia=10)
        banco.creditar(2)
        banco.virar_dia(11)
        self.assertEqual(banco.saldo, 6)
        self.assertEqual(banco.conquistadas_hoje, 0)


class TestLeilaoDeDistracoes(unittest.TestCase):
    def test_preco_inicial(self):
        self.assertEqual(LeilaoDeDistracoes().preco_min("tiktok"), PRECO_BASE_MIN)

    def test_preco_sobe_exponencialmente(self):
        leilao = LeilaoDeDistracoes(plano=Plano.FREE)
        precos = []
        for _ in range(4):
            preco = leilao.preco_min("tiktok")
            precos.append(preco)
            self.assertTrue(leilao.cobrar("tiktok", preco))
        self.assertEqual(precos, sorted(precos))
        self.assertAlmostEqual(precos[1] / precos[0], 1.6, places=6)
        self.assertAlmostEqual(precos[2] / precos[1], 1.6, places=6)

    def test_pro_tem_crescimento_mais_agressivo(self):
        free, pro = LeilaoDeDistracoes(plano=Plano.FREE), LeilaoDeDistracoes(plano=Plano.PRO)
        for leilao in (free, pro):
            leilao.cobrar("x", leilao.preco_min("x"))
        self.assertGreater(pro.preco_min("x"), free.preco_min("x"))

    def test_pagamento_insuficiente_nao_libera_nem_encarece(self):
        leilao = LeilaoDeDistracoes()
        self.assertFalse(leilao.cobrar("tiktok", PRECO_BASE_MIN - 0.5))
        self.assertEqual(leilao.preco_min("tiktok"), PRECO_BASE_MIN)

    def test_preco_respeita_o_teto(self):
        leilao = LeilaoDeDistracoes(plano=Plano.PRO)
        for _ in range(20):
            leilao.cobrar("tiktok", PRECO_TETO_MIN)
        self.assertEqual(leilao.preco_min("tiktok"), PRECO_TETO_MIN)

    def test_preco_e_por_app_e_zera_no_dia_seguinte(self):
        leilao = LeilaoDeDistracoes(dia=1)
        leilao.cobrar("tiktok", PRECO_BASE_MIN)
        self.assertGreater(leilao.preco_min("tiktok"), leilao.preco_min("x"))
        leilao.virar_dia(2)
        self.assertEqual(leilao.preco_min("tiktok"), PRECO_BASE_MIN)


if __name__ == "__main__":
    unittest.main()
