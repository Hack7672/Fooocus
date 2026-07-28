import unittest

from mente_zero.core.escala_zero import (
    JANELA_REPETICAO,
    NIVEL_MAX,
    NIVEL_MIN,
    EscalaZero,
    LimiteDiarioAtingido,
    TipoIndisponivel,
)
from mente_zero.core.models import TIPOS_BASICOS, Plano, TipoExercicio


class TestGeracao(unittest.TestCase):
    def test_todos_os_tipos_geram_item_valido(self):
        escala = EscalaZero(plano=Plano.PRO, semente=7)
        for tipo in TipoExercicio:
            exercicio = escala.proximo(tipo)
            self.assertIs(exercicio.tipo, tipo)
            self.assertTrue(exercicio.enunciado)
            self.assertGreater(exercicio.tempo_alvo_s, 0)
            if tipo is TipoExercicio.ASSOCIACAO_FORCADA:
                self.assertTrue(exercicio.aberto)
                self.assertIsNone(exercicio.resposta)
            else:
                self.assertFalse(exercicio.aberto)
                self.assertTrue(exercicio.resposta)

    def test_gabaritos_conferem(self):
        escala = EscalaZero(plano=Plano.PRO, semente=3)
        for tipo in TipoExercicio:
            if tipo is TipoExercicio.ASSOCIACAO_FORCADA:
                continue
            exercicio = escala.proximo(tipo)
            self.assertTrue(exercicio.confere(exercicio.resposta))
            self.assertFalse(exercicio.confere("resposta obviamente errada"))

    def test_item_aberto_exige_esforco(self):
        escala = EscalaZero(plano=Plano.PRO, semente=3)
        exercicio = escala.proximo(TipoExercicio.ASSOCIACAO_FORCADA)
        self.assertFalse(exercicio.confere("sei lá"))
        self.assertTrue(exercicio.confere("o espelho devolve o vento que a caverna guarda"))

    def test_analogia_traz_o_gabarito_entre_as_alternativas(self):
        escala = EscalaZero(plano=Plano.PRO, semente=11)
        for _ in range(10):
            exercicio = escala.proximo(TipoExercicio.ANALOGIA_VERBAL)
            self.assertIn(exercicio.resposta, exercicio.alternativas)

    def test_determinismo_por_semente(self):
        a = EscalaZero(plano=Plano.PRO, semente=42)
        b = EscalaZero(plano=Plano.PRO, semente=42)
        for _ in range(5):
            self.assertEqual(a.proximo().id, b.proximo().id)

    def test_sementes_diferentes_produzem_provas_diferentes(self):
        a = EscalaZero(plano=Plano.PRO, semente=1)
        b = EscalaZero(plano=Plano.PRO, semente=2)
        ids_a = {a.proximo().id for _ in range(10)}
        ids_b = {b.proximo().id for _ in range(10)}
        self.assertTrue(ids_a - ids_b)

    def test_repeticao_minima(self):
        escala = EscalaZero(plano=Plano.PRO, semente=5)
        vistos = [escala.proximo(TipoExercicio.SEQUENCIA_ABSTRATA).id for _ in range(JANELA_REPETICAO)]
        self.assertEqual(len(vistos), len(set(vistos)))

    def test_dificuldade_cresce_com_o_nivel(self):
        facil = EscalaZero(plano=Plano.PRO, semente=9, nivel=NIVEL_MIN)
        dificil = EscalaZero(plano=Plano.PRO, semente=9, nivel=NIVEL_MAX)
        self.assertGreater(
            dificil.proximo(TipoExercicio.LOGICA).tempo_alvo_s,
            facil.proximo(TipoExercicio.LOGICA).tempo_alvo_s,
        )
        self.assertGreater(
            len(dificil.proximo(TipoExercicio.ESPACIAL).enunciado),
            len(facil.proximo(TipoExercicio.ESPACIAL).enunciado),
        )


class TestProgressao(unittest.TestCase):
    def _responder(self, escala, correto, rapido=True, tipo=TipoExercicio.LOGICA):
        exercicio = escala.proximo(tipo)
        resposta = exercicio.resposta if correto else "errado"
        tempo = 1.0 if rapido else exercicio.tempo_alvo_s + 10.0
        return escala.responder(exercicio, resposta, tempo)

    def test_microganho_exige_dois_acertos_rapidos(self):
        escala = EscalaZero(plano=Plano.PRO, semente=13)
        primeiro = self._responder(escala, correto=True)
        self.assertEqual(primeiro.nivel_novo, NIVEL_MIN)
        segundo = self._responder(escala, correto=True)
        self.assertEqual(segundo.nivel_novo, NIVEL_MIN + 1)

    def test_acerto_lento_nao_sobe_nivel(self):
        escala = EscalaZero(plano=Plano.PRO, semente=13)
        for _ in range(4):
            resultado = self._responder(escala, correto=True, rapido=False)
            self.assertTrue(resultado.correto)
            self.assertFalse(resultado.dentro_do_tempo)
            self.assertEqual(resultado.nivel_novo, NIVEL_MIN)

    def test_erro_derruba_um_degrau_e_zera_a_sequencia(self):
        escala = EscalaZero(plano=Plano.PRO, semente=13, nivel=5)
        self._responder(escala, correto=True)
        resultado = self._responder(escala, correto=False)
        self.assertEqual(resultado.nivel_novo, 4)
        self.assertEqual(escala.acertos_rapidos_seguidos, 0)

    def test_nivel_respeita_os_limites(self):
        escala = EscalaZero(plano=Plano.PRO, semente=13, nivel=NIVEL_MIN)
        self._responder(escala, correto=False)
        self.assertEqual(escala.nivel, NIVEL_MIN)

        escala.nivel = NIVEL_MAX
        for _ in range(6):
            self._responder(escala, correto=True)
        self.assertEqual(escala.nivel, NIVEL_MAX)

    def test_acerto_gera_moeda(self):
        escala = EscalaZero(plano=Plano.PRO, semente=13)
        self.assertEqual(self._responder(escala, correto=True).moedas_ganhas, 1)
        self.assertEqual(self._responder(escala, correto=False).moedas_ganhas, 0)


class TestPlanos(unittest.TestCase):
    def test_free_tem_um_exercicio_por_dia(self):
        escala = EscalaZero(plano=Plano.FREE, semente=1)
        self.assertEqual(escala.restantes_hoje(), 1)
        escala.proximo()
        self.assertEqual(escala.restantes_hoje(), 0)
        with self.assertRaises(LimiteDiarioAtingido):
            escala.proximo()
        escala.virar_dia(escala.dia + 1)
        self.assertEqual(escala.restantes_hoje(), 1)

    def test_pro_e_ilimitado(self):
        escala = EscalaZero(plano=Plano.PRO, semente=1)
        self.assertIsNone(escala.restantes_hoje())
        for _ in range(50):
            escala.proximo()

    def test_free_so_recebe_tipos_basicos(self):
        escala = EscalaZero(plano=Plano.FREE, semente=1)
        self.assertEqual(escala.tipos_disponiveis, TIPOS_BASICOS)
        with self.assertRaises(TipoIndisponivel):
            escala.proximo(TipoExercicio.ALTERNANCIA_TAREFAS)


if __name__ == "__main__":
    unittest.main()
