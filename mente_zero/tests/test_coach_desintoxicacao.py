import unittest

from mente_zero.core.coach import (
    LIMIAR_CALMO_ATUAL,
    LIMIAR_RISCO,
    MINIMO_AMOSTRAS,
    CoachAtencao,
)
from mente_zero.core.desintoxicacao import (
    MARCOS_SOBERANIA,
    MENSAGEM_LAPSO,
    MENSAGEM_SEVERO,
    PERGUNTAS_TRIAGEM,
    PISO_META_MIN,
    ProgramaDesintoxicacao,
    Severidade,
    iniciar_programa,
    triagem,
)
from mente_zero.core.models import Plano, TipoIntervencao
from mente_zero.core.recalibragem import RecursoExclusivoPro


def alimentar(coach, dia, hora, ivd, vezes=MINIMO_AMOSTRAS):
    for _ in range(vezes):
        coach.registrar_leitura(dia, hora, ivd)


class TestCoachAtencao(unittest.TestCase):
    def test_previsao_e_exclusiva_do_pro(self):
        coach = CoachAtencao(plano=Plano.FREE)
        coach.registrar_leitura(0, 22, 80.0)  # registrar é livre
        with self.assertRaises(RecursoExclusivoPro):
            coach.risco_previsto(0, 22)
        with self.assertRaises(RecursoExclusivoPro):
            coach.janelas_de_risco(0)

    def test_sem_historico_suficiente_nao_ha_previsao(self):
        coach = CoachAtencao(plano=Plano.PRO)
        alimentar(coach, 0, 22, 80.0, vezes=MINIMO_AMOSTRAS - 1)
        self.assertIsNone(coach.risco_previsto(0, 22))
        alimentar(coach, 0, 22, 80.0, vezes=1)
        self.assertIsNotNone(coach.risco_previsto(0, 22))

    def test_media_converge_para_o_padrao(self):
        coach = CoachAtencao(plano=Plano.PRO)
        alimentar(coach, 2, 21, 80.0, vezes=20)
        previsto = coach.risco_previsto(2, 21)
        self.assertGreater(previsto, 70.0)
        alimentar(coach, 2, 10, 10.0, vezes=20)
        self.assertLess(coach.risco_previsto(2, 10), 20.0)

    def test_janelas_de_risco_ordenadas(self):
        coach = CoachAtencao(plano=Plano.PRO)
        alimentar(coach, 5, 22, 85.0, vezes=10)
        alimentar(coach, 5, 13, 60.0, vezes=10)
        alimentar(coach, 5, 9, 20.0, vezes=10)  # calma: fora da lista
        janelas = coach.janelas_de_risco(5)
        self.assertEqual([j.hora for j in janelas], [22, 13])
        self.assertGreaterEqual(janelas[0].ivd_previsto, LIMIAR_RISCO)

    def test_antecipacao_chega_antes_da_recaida(self):
        coach = CoachAtencao(plano=Plano.PRO)
        alimentar(coach, 3, 22, 80.0, vezes=10)  # 22h de quinta é o buraco
        aviso = coach.antecipar(3, 21, ivd_atual=10.0)
        self.assertIsNotNone(aviso)
        self.assertIs(aviso.tipo, TipoIntervencao.ALERTA_SUAVE)
        self.assertTrue(aviso.payload["preventiva"])
        self.assertEqual(aviso.payload["hora_de_risco"], 22)

    def test_nao_antecipa_se_o_presente_ja_esta_agitado(self):
        coach = CoachAtencao(plano=Plano.PRO)
        alimentar(coach, 3, 22, 80.0, vezes=10)
        self.assertIsNone(coach.antecipar(3, 21, ivd_atual=LIMIAR_CALMO_ATUAL + 1))

    def test_nao_antecipa_sem_risco_na_proxima_hora(self):
        coach = CoachAtencao(plano=Plano.PRO)
        alimentar(coach, 3, 22, 20.0, vezes=10)
        self.assertIsNone(coach.antecipar(3, 21, ivd_atual=10.0))

    def test_virada_de_meia_noite_cruza_para_o_dia_seguinte(self):
        coach = CoachAtencao(plano=Plano.PRO)
        alimentar(coach, 4, 0, 80.0, vezes=10)  # sexta 00h
        aviso = coach.antecipar(3, 23, ivd_atual=5.0)  # quinta 23h
        self.assertIsNotNone(aviso)
        self.assertEqual(aviso.payload["hora_de_risco"], 0)

    def test_validacao_de_janela(self):
        coach = CoachAtencao(plano=Plano.PRO)
        with self.assertRaises(ValueError):
            coach.registrar_leitura(7, 10, 50.0)
        with self.assertRaises(ValueError):
            coach.registrar_leitura(0, 24, 50.0)

    def test_estado_e_serializavel(self):
        import json

        coach = CoachAtencao(plano=Plano.PRO)
        alimentar(coach, 1, 20, 70.0)
        dados = json.dumps({"medias": coach.medias, "contagens": coach.contagens})
        recuperado = json.loads(dados)
        clone = CoachAtencao(
            plano=Plano.PRO, medias=recuperado["medias"], contagens=recuperado["contagens"]
        )
        self.assertEqual(clone.risco_previsto(1, 20), coach.risco_previsto(1, 20))


class TestTriagem(unittest.TestCase):
    def test_faixas_de_severidade(self):
        n = len(PERGUNTAS_TRIAGEM)
        self.assertIs(triagem([1] * n).severidade, Severidade.LEVE)      # 8
        self.assertIs(triagem([2] * n).severidade, Severidade.MODERADO)  # 16
        self.assertIs(triagem([4] * n).severidade, Severidade.SEVERO)    # 32

    def test_severo_orienta_apoio_humano(self):
        resultado = triagem([4] * len(PERGUNTAS_TRIAGEM))
        self.assertEqual(resultado.mensagem, MENSAGEM_SEVERO)
        self.assertIn("apoio humano", resultado.mensagem)

    def test_validacao(self):
        with self.assertRaises(ValueError):
            triagem([1, 2])
        with self.assertRaises(ValueError):
            triagem([5] * len(PERGUNTAS_TRIAGEM))
        with self.assertRaises(ValueError):
            triagem([-1] * len(PERGUNTAS_TRIAGEM))


class TestProgramaDesintoxicacao(unittest.TestCase):
    def test_duracao_e_meta_por_severidade(self):
        leve = ProgramaDesintoxicacao(Severidade.LEVE, linha_de_base_min=200.0)
        severo = ProgramaDesintoxicacao(Severidade.SEVERO, linha_de_base_min=200.0)
        self.assertEqual(leve.semanas, 4)
        self.assertEqual(severo.semanas, 8)
        self.assertLess(severo.meta_final_min, leve.meta_final_min)

    def test_piso_da_meta_final(self):
        programa = ProgramaDesintoxicacao(Severidade.SEVERO, linha_de_base_min=40.0)
        self.assertEqual(programa.meta_final_min, PISO_META_MIN)

    def test_taper_e_linear_e_decrescente(self):
        programa = ProgramaDesintoxicacao(Severidade.MODERADO, linha_de_base_min=180.0)
        metas = [programa.meta_da_semana(s) for s in range(1, programa.semanas + 1)]
        self.assertEqual(metas, sorted(metas, reverse=True))
        self.assertAlmostEqual(metas[-1], programa.meta_final_min)
        self.assertLess(metas[0], 180.0)  # já reduz na primeira semana
        # após o protocolo, a meta congela na final (manutenção)
        self.assertAlmostEqual(
            programa.meta_da_semana(programa.semanas + 5), programa.meta_final_min
        )

    def test_mecanismos_acumulam_sem_recuar(self):
        programa = ProgramaDesintoxicacao(Severidade.MODERADO, linha_de_base_min=180.0)
        anteriores: tuple[str, ...] = ()
        for semana in range(1, programa.semanas + 1):
            atuais = programa.mecanismos_da_semana(semana)
            self.assertTrue(set(anteriores) <= set(atuais))
            anteriores = atuais
        self.assertIn("monitoramento do IVD", programa.mecanismos_da_semana(1))

    def test_dia_cumprido_e_lapso_sem_culpa(self):
        programa = ProgramaDesintoxicacao(Severidade.LEVE, linha_de_base_min=100.0)
        meta1 = programa.meta_da_semana(1)
        bom = programa.registrar_dia(1, meta1 - 5.0)
        self.assertTrue(bom.cumpriu)
        self.assertEqual(bom.sequencia_atual, 1)

        lapso = programa.registrar_dia(1, meta1 + 30.0)
        self.assertFalse(lapso.cumpriu)
        self.assertEqual(lapso.mensagem, MENSAGEM_LAPSO)
        self.assertEqual(lapso.sequencia_atual, 0)
        # o lapso zera a sequência mas preserva o acumulado
        self.assertEqual(lapso.dias_cumpridos_total, 1)
        self.assertEqual(programa.melhor_sequencia, 1)
        self.assertEqual(programa.lapsos, 1)

    def test_marcos_de_soberania(self):
        programa = ProgramaDesintoxicacao(Severidade.LEVE, linha_de_base_min=100.0)
        marcos = []
        for _ in range(30):
            registro = programa.registrar_dia(1, 0.0)
            if registro.marco_alcancado:
                marcos.append(registro.marco_alcancado)
        self.assertEqual(marcos, [7, 30])
        self.assertEqual(programa.marcos_alcancados, [7, 30])
        self.assertIn(90, MARCOS_SOBERANIA)

    def test_atalho_iniciar_programa(self):
        programa = iniciar_programa([3] * len(PERGUNTAS_TRIAGEM), linha_de_base_min=240.0)
        self.assertIs(programa.severidade, Severidade.SEVERO)
        self.assertEqual(programa.progresso()["semanas"], 8)

    def test_linha_de_base_invalida(self):
        with self.assertRaises(ValueError):
            ProgramaDesintoxicacao(Severidade.LEVE, linha_de_base_min=0.0)


if __name__ == "__main__":
    unittest.main()
