import unittest

from mente_zero.core.jornada import (
    AVISO_SIMBOLICO,
    CAPITULOS,
    JornadaDoHeroi,
    simular_perda,
)
from mente_zero.core.models import Plano
from mente_zero.core.protocolo_realidade import (
    HORAS_EM_CASA_PARA_MISSAO,
    INTERVALO_LEMBRETE_S,
    FeedNutritivo,
    ProtocoloRealidade,
    ReflexaoPendente,
    cronograma_detox,
)
from mente_zero.core.social import (
    LIMITE_MEMBROS,
    MINIMO_REFLEXAO,
    CotaSemanalEsgotada,
    FeedMaieutico,
    ForaDaTribo,
    GerenciadorTribos,
    LimiteDeTribos,
    ReflexaoCurta,
    ReflexaoJaEnviada,
    RespostaPendente,
    TriboCheia,
    TriboDeSilencio,
)

TEXTO_LONGO = "x" * MINIMO_REFLEXAO


class TestJornada(unittest.TestCase):
    def test_semana_conta_apenas_com_meta_cumprida(self):
        jornada = JornadaDoHeroi(plano=Plano.PRO)
        self.assertFalse(jornada.registrar_semana(4))
        self.assertTrue(jornada.registrar_semana(5))
        self.assertEqual(jornada.semanas_de_foco, 1)

    def test_free_vive_apenas_o_prologo(self):
        jornada = JornadaDoHeroi(plano=Plano.FREE)
        for _ in range(20):
            jornada.registrar_semana(7)
        self.assertEqual(len(jornada.capitulos_desbloqueados()), 1)
        self.assertIsNone(jornada.proximo_capitulo())

    def test_pro_desbloqueia_a_jornada_completa(self):
        jornada = JornadaDoHeroi(plano=Plano.PRO)
        self.assertEqual(len(jornada.capitulos_desbloqueados()), 1)  # prólogo
        for _ in range(12):
            jornada.registrar_semana(7)
        self.assertEqual(len(jornada.capitulos_desbloqueados()), len(CAPITULOS))
        self.assertIsNone(jornada.proximo_capitulo())

    def test_proximo_capitulo_informa_a_meta(self):
        jornada = JornadaDoHeroi(plano=Plano.PRO)
        proximo = jornada.proximo_capitulo()
        self.assertEqual(proximo.indice, 1)
        self.assertEqual(proximo.semanas_exigidas, 1)

    def test_dias_invalidos(self):
        with self.assertRaises(ValueError):
            JornadaDoHeroi().registrar_semana(8)

    def test_simulador_e_sempre_rotulado_como_simbolico(self):
        for ivd in (0.0, 30.0, 60.0, 100.0):
            simulacao = simular_perda(ivd)
            self.assertEqual(simulacao.aviso, AVISO_SIMBOLICO)
        self.assertAlmostEqual(simular_perda(0.0).fator, 1.0)
        self.assertAlmostEqual(simular_perda(100.0).fator, 0.6)
        self.assertGreater(simular_perda(20.0).fator, simular_perda(80.0).fator)


class TestTribos(unittest.TestCase):
    def test_limite_de_doze_membros(self):
        tribo = TriboDeSilencio("aurora")
        for i in range(LIMITE_MEMBROS):
            tribo.entrar(f"pessoa{i}")
        with self.assertRaises(TriboCheia):
            tribo.entrar("intruso")

    def test_nao_existe_api_de_chat(self):
        proibidos = {"mensagem", "chat", "curtir", "reagir", "online", "digitando"}
        membros_da_classe = {nome.lower() for nome in dir(TriboDeSilencio)}
        self.assertFalse(proibidos & membros_da_classe)

    def test_uma_reflexao_por_semana_e_texto_longo(self):
        tribo = TriboDeSilencio("aurora")
        tribo.entrar("ana")
        with self.assertRaises(ReflexaoCurta):
            tribo.refletir("ana", semana=1, conteudo="curto demais")
        tribo.refletir("ana", semana=1, conteudo=TEXTO_LONGO)
        with self.assertRaises(ReflexaoJaEnviada):
            tribo.refletir("ana", semana=1, conteudo=TEXTO_LONGO)
        tribo.refletir("ana", semana=2, conteudo=TEXTO_LONGO)
        self.assertEqual(len(tribo.mural_da_semana(1)), 1)

    def test_audio_dispensa_minimo_de_texto(self):
        tribo = TriboDeSilencio("aurora")
        tribo.entrar("ana")
        reflexao = tribo.refletir("ana", semana=1, conteudo="ref-audio-01", em_audio=True)
        self.assertTrue(reflexao.em_audio)

    def test_nao_membro_nao_reflete(self):
        tribo = TriboDeSilencio("aurora")
        with self.assertRaises(ForaDaTribo):
            tribo.refletir("intruso", semana=1, conteudo=TEXTO_LONGO)

    def test_free_participa_de_uma_tribo(self):
        gerenciador = GerenciadorTribos(plano=Plano.FREE)
        gerenciador.entrar("ana", TriboDeSilencio("aurora"))
        with self.assertRaises(LimiteDeTribos):
            gerenciador.entrar("ana", TriboDeSilencio("crepusculo"))

    def test_pro_e_ilimitado(self):
        gerenciador = GerenciadorTribos(plano=Plano.PRO)
        for nome in ("a", "b", "c", "d"):
            gerenciador.entrar("ana", TriboDeSilencio(nome))


class TestFeedMaieutico(unittest.TestCase):
    RESPOSTA = "Mudei de ideia sobre o valor do tédio este ano."

    def test_free_abre_tres_perguntas_por_semana(self):
        feed = FeedMaieutico(plano=Plano.FREE)
        for _ in range(3):
            feed.proxima_pergunta()
        with self.assertRaises(CotaSemanalEsgotada):
            feed.proxima_pergunta()
        feed.virar_semana(2)
        feed.proxima_pergunta()

    def test_mural_so_abre_depois_de_responder(self):
        feed = FeedMaieutico(plano=Plano.PRO)
        pergunta = feed.proxima_pergunta()
        feed.semear_mural(pergunta, ["Uma resposta alheia qualquer."])
        with self.assertRaises(RespostaPendente):
            feed.respostas_anonimas(pergunta)
        feed.responder(pergunta, self.RESPOSTA)
        self.assertEqual(len(feed.respostas_anonimas(pergunta)), 1)

    def test_resposta_curta_e_rejeitada(self):
        feed = FeedMaieutico(plano=Plano.PRO)
        pergunta = feed.proxima_pergunta()
        with self.assertRaises(ValueError):
            feed.responder(pergunta, "sim")


class TestProtocoloRealidade(unittest.TestCase):
    RELATO = "A fachada tem azulejos portugueses, cornija dupla e uma data de 1911 gravada."

    def test_missao_so_apos_longa_permanencia(self):
        protocolo = ProtocoloRealidade()
        self.assertIsNone(protocolo.propor_missao(HORAS_EM_CASA_PARA_MISSAO - 1))
        missao = protocolo.propor_missao(HORAS_EM_CASA_PARA_MISSAO)
        self.assertIsNotNone(missao)
        self.assertTrue(missao.instrucao)

    def test_missoes_rotacionam(self):
        protocolo = ProtocoloRealidade()
        ids = {protocolo.propor_missao(10.0).id for _ in range(4)}
        self.assertEqual(len(ids), 4)

    def test_conclusao_exige_relato_com_substancia(self):
        protocolo = ProtocoloRealidade()
        missao = protocolo.propor_missao(10.0)
        self.assertFalse(protocolo.concluir(missao, "fui lá"))
        self.assertTrue(protocolo.concluir(missao, self.RELATO))
        self.assertIn(missao.id, protocolo.concluidas)

    def test_cronograma_detox(self):
        passos = cronograma_detox(20)
        self.assertEqual(passos[0].acao, "iniciar_som")
        vibracoes = [p for p in passos if p.acao == "vibrar"]
        self.assertEqual(len(vibracoes), 4)  # 20 min / 5 min
        self.assertEqual(vibracoes[0].em_s, INTERVALO_LEMBRETE_S)
        with self.assertRaises(ValueError):
            cronograma_detox(0)
        with self.assertRaises(ValueError):
            cronograma_detox(10, som="heavy_metal")

    def test_feed_nutritivo_exige_reflexao_entre_itens(self):
        feed = FeedNutritivo()
        titulo, corpo = feed.proximo_item()
        self.assertTrue(titulo and corpo)
        with self.assertRaises(ReflexaoPendente):
            feed.proximo_item()
        with self.assertRaises(ValueError):
            feed.refletir("ok")
        feed.refletir("O navio de Teseu somos nós trocando hábitos aos poucos.")
        feed.proximo_item()


if __name__ == "__main__":
    unittest.main()
