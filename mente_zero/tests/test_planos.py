import unittest
from dataclasses import fields

from mente_zero.core.models import TIPOS_BASICOS, Plano, TipoExercicio
from mente_zero.core.planos import direitos


class TestMatrizDePlanos(unittest.TestCase):
    def test_todo_plano_tem_direitos(self):
        for plano in Plano:
            self.assertIsNotNone(direitos(plano))

    def test_pro_nunca_e_pior_que_free(self):
        free, pro = direitos(Plano.FREE), direitos(Plano.PRO)
        for campo in fields(free):
            valor_free = getattr(free, campo.name)
            valor_pro = getattr(pro, campo.name)
            if valor_free is None or valor_pro is None:
                # None significa ilimitado: só o PRO pode tê-lo.
                self.assertIsNone(valor_pro, campo.name)
            elif isinstance(valor_free, bool):
                self.assertGreaterEqual(int(valor_pro), int(valor_free), campo.name)
            elif isinstance(valor_free, (int, float)):
                self.assertGreaterEqual(valor_pro, valor_free, campo.name)
            elif isinstance(valor_free, tuple):
                self.assertTrue(set(valor_free) <= set(valor_pro), campo.name)

    def test_numeros_do_documento_mestre(self):
        free, pro = direitos(Plano.FREE), direitos(Plano.PRO)
        self.assertEqual(free.moedas_diarias, 4)
        self.assertEqual(pro.moedas_diarias, 6)
        self.assertEqual(free.exercicios_diarios, 1)
        self.assertIsNone(pro.exercicios_diarios)
        self.assertEqual(free.tribos_simultaneas, 1)
        self.assertEqual(free.perguntas_maieuticas_semana, 3)
        self.assertEqual(free.dias_zero_por_mes, 1)
        self.assertEqual(free.tipos_exercicio, TIPOS_BASICOS)
        self.assertEqual(set(pro.tipos_exercicio), set(TipoExercicio))
        self.assertGreater(pro.crescimento_leilao, free.crescimento_leilao)

    def test_recursos_exclusivos_do_pro(self):
        free, pro = direitos(Plano.FREE), direitos(Plano.PRO)
        exclusivos = (
            "neurofeedback_optico",
            "coach_ia",
            "foco_profundo_multidispositivo",
            "avatar_personalizado",
            "diario_mente_restaurada",
            "mentoria_reversa",
            "desafio_texto_inutil",
            "creditos_bonus_missoes",
        )
        for nome in exclusivos:
            self.assertFalse(getattr(free, nome), nome)
            self.assertTrue(getattr(pro, nome), nome)


if __name__ == "__main__":
    unittest.main()
