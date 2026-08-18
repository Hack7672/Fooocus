import unittest

from mente_zero.core.foco import (
    DURACAO_FOCO_S,
    TEXTOS_LONGOS,
    DesafioTextoInutil,
    FocoIncompleto,
    FocoProfundo,
    MultiDispositivoIndisponivel,
    SessaoJaAtiva,
    SessaoNaoAtiva,
)
from mente_zero.core.models import CategoriaApp, Plano
from mente_zero.core.recalibragem import RecursoExclusivoPro
from mente_zero.core.relatorio import ResumoDiario, gerar_relatorio

INTERPRETACAO_BOA = (
    "Sêneca fala de tempo desperdiçado por escolha e o feed automatiza essa "
    "escolha, transformando desperdício ativo em desperdício por omissão, o que "
    "torna o argumento dele ainda mais atual do que era em Roma."
)


class TestFocoProfundo(unittest.TestCase):
    def test_sessao_entrega_texto_e_bloqueia_distracao(self):
        foco = FocoProfundo()
        texto = foco.iniciar(0.0)
        self.assertIn(texto, TEXTOS_LONGOS)
        self.assertTrue(foco.deve_bloquear(CategoriaApp.FEED_SOCIAL, 100.0))
        self.assertFalse(foco.deve_bloquear(CategoriaApp.LEITURA, 100.0))
        with self.assertRaises(SessaoJaAtiva):
            foco.iniciar(10.0)

    def test_concluir_antes_da_hora_falha(self):
        foco = FocoProfundo()
        foco.iniciar(0.0)
        with self.assertRaises(FocoIncompleto):
            foco.concluir(DURACAO_FOCO_S - 60.0, INTERPRETACAO_BOA)

    def test_conclusao_integral_com_interpretacao(self):
        foco = FocoProfundo()
        foco.iniciar(0.0)
        self.assertAlmostEqual(foco.progresso(DURACAO_FOCO_S / 2), 0.5)
        resultado = foco.concluir(DURACAO_FOCO_S, INTERPRETACAO_BOA)
        self.assertTrue(resultado.concluida)
        self.assertEqual(foco.sessoes_concluidas, 1)
        self.assertFalse(foco.em_sessao(DURACAO_FOCO_S + 1))

    def test_interpretacao_rasa_nao_conclui(self):
        foco = FocoProfundo()
        foco.iniciar(0.0)
        resultado = foco.concluir(DURACAO_FOCO_S, "gostei do texto")
        self.assertFalse(resultado.concluida)
        self.assertEqual(foco.sessoes_concluidas, 0)

    def test_interromper_e_recomecar(self):
        foco = FocoProfundo()
        foco.iniciar(0.0)
        resultado = foco.interromper(600.0)
        self.assertFalse(resultado.concluida)
        self.assertAlmostEqual(resultado.minutos, 10.0)
        foco.iniciar(700.0)  # pode recomeçar
        with self.assertRaises(SessaoNaoAtiva):
            FocoProfundo().interromper(0.0)

    def test_textos_rotacionam(self):
        foco = FocoProfundo()
        ids = set()
        for i in range(len(TEXTOS_LONGOS)):
            ids.add(foco.iniciar(i * 100.0).id)
            foco.interromper(i * 100.0 + 50.0)
        self.assertEqual(len(ids), len(TEXTOS_LONGOS))

    def test_multidispositivo_e_pro(self):
        free = FocoProfundo(plano=Plano.FREE)
        free.iniciar(0.0, dispositivo="celular")
        free.retomar_em("celular")  # mesmo dispositivo é livre
        with self.assertRaises(MultiDispositivoIndisponivel):
            free.retomar_em("tablet")

        pro = FocoProfundo(plano=Plano.PRO)
        texto = pro.iniciar(0.0, dispositivo="celular")
        self.assertEqual(pro.retomar_em("tablet"), texto)
        self.assertEqual(pro.dispositivo, "tablet")


class TestTextoInutil(unittest.TestCase):
    def test_exclusivo_do_pro(self):
        with self.assertRaises(RecursoExclusivoPro):
            DesafioTextoInutil(plano=Plano.FREE).ativar()

    def test_parametros_degradam_com_a_intensidade(self):
        desafio = DesafioTextoInutil(plano=Plano.PRO)
        with self.assertRaises(RuntimeError):
            desafio.parametros()
        desafio.ativar()
        leve, pesado = desafio.parametros(1), desafio.parametros(3)
        self.assertGreater(leve["contraste"], pesado["contraste"])
        self.assertLess(leve["espacamento_letras_em"], pesado["espacamento_letras_em"])
        with self.assertRaises(ValueError):
            desafio.parametros(4)
        desafio.desativar()
        self.assertFalse(desafio.ativo)


class TestRelatorioSemanal(unittest.TestCase):
    @staticmethod
    def semana(ivd, passivo, exercicios=1, foco=0):
        return [
            ResumoDiario(
                dia=i, ivd_medio=ivd, minutos_passivos=passivo,
                exercicios=exercicios, intervencoes=2, sessoes_foco=foco,
            )
            for i in range(7)
        ]

    def test_consolidacao_basica(self):
        relatorio = gerar_relatorio(self.semana(30.0, 60.0, exercicios=1, foco=1))
        self.assertEqual(relatorio.dias_cobertos, 7)
        self.assertAlmostEqual(relatorio.ivd_medio, 30.0)
        self.assertEqual(relatorio.faixa, "atencao")
        self.assertEqual(relatorio.exercicios, 7)
        self.assertEqual(relatorio.sessoes_foco, 7)
        self.assertIsNone(relatorio.variacao_ivd)

    def test_melhora_e_celebrada(self):
        relatorio = gerar_relatorio(
            self.semana(30.0, 50.0), semana_anterior=self.semana(45.0, 80.0)
        )
        self.assertAlmostEqual(relatorio.variacao_ivd, -15.0)
        self.assertIn("caiu", relatorio.destaque)

    def test_piora_vem_com_plano_e_nao_com_culpa(self):
        relatorio = gerar_relatorio(
            self.semana(55.0, 90.0), semana_anterior=self.semana(40.0, 80.0)
        )
        self.assertIn("Sem culpa", relatorio.destaque)
        self.assertIn("Dia Zero", relatorio.recomendacao)

    def test_recomendacao_escalona_por_situacao(self):
        muito_passivo = gerar_relatorio(self.semana(30.0, 120.0))
        self.assertIn("minutos passivos", muito_passivo.recomendacao)
        sem_foco = gerar_relatorio(self.semana(20.0, 30.0, exercicios=1, foco=0))
        self.assertIn("Foco Profundo", sem_foco.recomendacao)
        em_ritmo = gerar_relatorio(self.semana(15.0, 20.0, exercicios=2, foco=1))
        self.assertIn("consistência", em_ritmo.recomendacao)

    def test_semana_invalida(self):
        with self.assertRaises(ValueError):
            gerar_relatorio([])
        with self.assertRaises(ValueError):
            gerar_relatorio(self.semana(10.0, 10.0) + self.semana(10.0, 10.0))


if __name__ == "__main__":
    unittest.main()
