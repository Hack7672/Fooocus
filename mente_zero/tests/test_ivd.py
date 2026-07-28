import unittest

from mente_zero.core.ivd import CalculadoraIVD, nivel_para
from mente_zero.core.models import CategoriaApp, EventoUso, NivelRisco


def amostra(t, **kwargs):
    padrao = dict(
        timestamp=t,
        app_id="feedapp",
        categoria=CategoriaApp.FEED_SOCIAL,
        duracao_s=5.0,
        distancia_scroll_px=6000.0,
        toques=0,
        inversoes_direcao=0,
    )
    padrao.update(kwargs)
    return EventoUso(**padrao)


class TestFaixas(unittest.TestCase):
    def test_limiares(self):
        self.assertIs(nivel_para(0.0), NivelRisco.CALMO)
        self.assertIs(nivel_para(24.9), NivelRisco.CALMO)
        self.assertIs(nivel_para(25.0), NivelRisco.ATENCAO)
        self.assertIs(nivel_para(50.0), NivelRisco.ALERTA)
        self.assertIs(nivel_para(99.0), NivelRisco.CRITICO)


class TestCalculadoraIVD(unittest.TestCase):
    def test_comeca_calmo(self):
        self.assertIs(CalculadoraIVD().nivel, NivelRisco.CALMO)

    def test_scroll_compulsivo_eleva_indice(self):
        calc = CalculadoraIVD()
        leitura = None
        for i in range(120):  # 10 minutos de rolagem passiva e veloz
            leitura = calc.registrar(amostra(i * 5.0, abertura_app=(i == 0)))
        self.assertIsNotNone(leitura)
        self.assertGreaterEqual(leitura.valor, 50.0)
        self.assertIn(leitura.nivel, (NivelRisco.ALERTA, NivelRisco.CRITICO))

    def test_leitura_atenta_nao_eleva_indice(self):
        calc = CalculadoraIVD()
        leitura = None
        for i in range(120):
            leitura = calc.registrar(
                amostra(
                    i * 5.0,
                    distancia_scroll_px=300.0,   # rolagem lenta
                    toques=1,                    # interação intencional
                    inversoes_direcao=1,         # volta para reler
                )
            )
        self.assertLess(leitura.valor, 25.0)
        self.assertIs(leitura.nivel, NivelRisco.CALMO)

    def test_uso_saudavel_faz_o_indice_decair(self):
        calc = CalculadoraIVD()
        for i in range(120):
            calc.registrar(amostra(i * 5.0))
        pico = calc.valor
        for i in range(120, 360):  # 20 minutos em app de produtividade
            calc.registrar(
                amostra(
                    i * 5.0,
                    app_id="editor",
                    categoria=CategoriaApp.PRODUTIVIDADE,
                    distancia_scroll_px=0.0,
                )
            )
        self.assertLess(calc.valor, pico)
        self.assertIs(calc.nivel, NivelRisco.CALMO)

    def test_madrugada_agrava(self):
        def rodar(hora):
            calc = CalculadoraIVD()
            leitura = None
            for i in range(60):
                leitura = calc.registrar(amostra(i * 5.0, hora_local=hora))
            return leitura.valor

        self.assertGreater(rodar(3), rodar(15))

    def test_permanencia_reseta_em_app_neutro(self):
        calc = CalculadoraIVD()
        for i in range(60):
            calc.registrar(amostra(i * 5.0))
        self.assertGreater(calc.permanencia_s, 0.0)
        calc.registrar(
            amostra(310.0, categoria=CategoriaApp.LEITURA, distancia_scroll_px=100.0)
        )
        self.assertEqual(calc.permanencia_s, 0.0)

    def test_reentradas_contam_apenas_ultima_hora(self):
        calc = CalculadoraIVD()
        calc.registrar(amostra(0.0, abertura_app=True))
        calc.registrar(amostra(1000.0, abertura_app=True))
        self.assertEqual(calc.reentradas_ultima_hora(1000.0), 2)
        calc.registrar(amostra(5000.0, abertura_app=True))
        self.assertEqual(calc.reentradas_ultima_hora(5000.0), 1)

    def test_duracao_invalida_e_rejeitada(self):
        with self.assertRaises(ValueError):
            EventoUso(0.0, "x", CategoriaApp.FEED_SOCIAL, duracao_s=0.0)


if __name__ == "__main__":
    unittest.main()
