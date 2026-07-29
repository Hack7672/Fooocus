import unittest

from mente_zero.core.models import Plano
from mente_zero.core.recalibragem import (
    MENSAGEM_AJUDA,
    PERGUNTA_DIARIO,
    PLANO_OFFLINE_GUIADO,
    CotaMensalEsgotada,
    DiarioMenteRestaurada,
    DiaZero,
    DiaZeroNaoIniciado,
    EstadoEmocional,
    RecursoExclusivoPro,
    TermometroEmocional,
)


class TestTermometro(unittest.TestCase):
    def setUp(self):
        self.termometro = TermometroEmocional()

    def test_texto_sereno(self):
        avaliacao = self.termometro.avaliar(
            "Hoje caminhei no parque, li um capítulo e cozinhei com calma."
        )
        self.assertIs(avaliacao.estado, EstadoEmocional.SERENO)
        self.assertEqual(avaliacao.sugestao, "")

    def test_ansiedade_com_contexto_digital(self):
        avaliacao = self.termometro.avaliar(
            "Estou ansioso e culpado, passei horas no celular rolando o feed "
            "e me sinto vazio e agitado com tanta notificação."
        )
        self.assertIs(avaliacao.estado, EstadoEmocional.ANSIEDADE_DIGITAL)
        self.assertTrue(avaliacao.contexto_digital)
        self.assertIn("Escrita terapêutica", avaliacao.sugestao)

    def test_tensao_sem_contexto_digital(self):
        avaliacao = self.termometro.avaliar(
            "Ando preocupado e nervoso com o trabalho, meio exausto ultimamente."
        )
        self.assertIs(avaliacao.estado, EstadoEmocional.TENSAO)
        self.assertIn("Micro-meditação", avaliacao.sugestao)

    def test_acentos_nao_atrapalham(self):
        avaliacao = self.termometro.avaliar("Muita ansiedade e compulsão, tudo vazio.")
        self.assertGreater(avaliacao.escore, 0.0)

    def test_crise_encaminha_para_ajuda_humana(self):
        avaliacao = self.termometro.avaliar("Tenho pensado em suicídio.")
        self.assertIs(avaliacao.estado, EstadoEmocional.ENCAMINHAR_AJUDA)
        self.assertEqual(avaliacao.sugestao, MENSAGEM_AJUDA)
        self.assertIn("188", avaliacao.sugestao)

    def test_texto_vazio(self):
        self.assertIs(self.termometro.avaliar("   ").estado, EstadoEmocional.SERENO)


class TestDiaZero(unittest.TestCase):
    def test_free_tem_um_por_mes(self):
        dz = DiaZero(plano=Plano.FREE)
        self.assertEqual(dz.iniciar(mes=1), PLANO_OFFLINE_GUIADO)
        dz.concluir(())
        with self.assertRaises(CotaMensalEsgotada):
            dz.iniciar(mes=1)
        self.assertTrue(dz.disponivel(mes=2))
        dz.iniciar(mes=2)

    def test_pro_e_livre(self):
        dz = DiaZero(plano=Plano.PRO)
        for _ in range(4):
            dz.iniciar(mes=1)
            dz.concluir(())

    def test_relatorio_de_reconexao(self):
        dz = DiaZero(plano=Plano.PRO)
        atividades = dz.iniciar(mes=3)
        relatorio = dz.concluir(atividades[:4])
        self.assertEqual(relatorio.mes, 3)
        self.assertEqual(len(relatorio.atividades_concluidas), 4)
        self.assertAlmostEqual(relatorio.taxa_conclusao, 0.8)
        self.assertIn("atenção", relatorio.mensagem)

    def test_relatorio_ignora_atividade_inventada(self):
        dz = DiaZero(plano=Plano.PRO)
        dz.iniciar(mes=1)
        relatorio = dz.concluir(("maratona de séries",))
        self.assertEqual(relatorio.atividades_concluidas, ())
        self.assertEqual(relatorio.taxa_conclusao, 0.0)

    def test_concluir_sem_iniciar_falha(self):
        with self.assertRaises(DiaZeroNaoIniciado):
            DiaZero().concluir(())


class TestDiario(unittest.TestCase):
    def test_free_nao_tem_diario(self):
        diario = DiarioMenteRestaurada(plano=Plano.FREE)
        with self.assertRaises(RecursoExclusivoPro):
            diario.pergunta()
        with self.assertRaises(RecursoExclusivoPro):
            diario.registrar(0.0, "texto")

    def test_pro_registra_com_a_pergunta_do_mestre(self):
        diario = DiarioMenteRestaurada(plano=Plano.PRO)
        self.assertEqual(diario.pergunta(), PERGUNTA_DIARIO)
        self.assertEqual(diario.registrar(0.0, "Estava evitando o silêncio."), 1)
        self.assertEqual(diario.total, 1)

    def test_entrada_vazia_e_rejeitada(self):
        diario = DiarioMenteRestaurada(plano=Plano.PRO)
        with self.assertRaises(ValueError):
            diario.registrar(0.0, "   ")


if __name__ == "__main__":
    unittest.main()
