"""Motor de reset cognitivo — orquestração das camadas 1, 2, 4 e 5.

O motor é a única porta de entrada do núcleo: o agente do sistema operacional
empurra amostras de uso e recebe de volta a intervenção a executar. Ele decide
prioridade entre camadas, respeita o intervalo mínimo entre intervenções (para
que o app nunca vire mais uma fonte de ruído) e aplica a matriz de planos.

Ordem de prioridade das intervenções:

1. Camada 4 (Scroll Stopper, tela cinza, janela de reflexão) — já em curso.
2. Camada 5 (mensagem do Eu Futuro) — risco crítico, iminência de recaída.
3. Anti-dopamina rápida (micro-pausa sensorial) — risco crítico.
4. Camada 1 (tarefa-relâmpago e alerta suave) — risco alerta/atenção.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .economia_atencao import (
    CUSTO_ACESSO_SOCIAL,
    BancoDeMinutos,
    LeilaoDeDistracoes,
    ScrollStopper,
)
from .escala_zero import EscalaZero, Exercicio, LimiteDiarioAtingido, Resultado
from .ivd import CalculadoraIVD, LeituraIVD
from .models import (
    SEM_INTERVENCAO,
    EventoUso,
    Intervencao,
    NivelRisco,
    Plano,
    TipoExercicio,
    TipoIntervencao,
)
from .planos import direitos

SEGUNDOS_POR_DIA = 86_400.0

#: Intervalo mínimo (s) entre intervenções de aviso, para não virar spam.
COOLDOWN_AVISOS_S = 300.0

FRASES_MICRO_PAUSA = (
    "Respire. O que existe agora não cabe em uma tela.",
    "A pressa de rolar é a pressa de não sentir.",
    "Quem controla sua atenção controla sua vida.",
    "Uma mente que não suporta o tédio não alcança a profundidade.",
)

SONS_MICRO_PAUSA = ("chuva_na_floresta", "riacho", "vento_em_folhas", "fogueira")

MENSAGEM_EU_FUTURO_GENERICA = (
    "Se você continuar agora, eu perco mais um pedaço do que poderíamos ter sido."
)


@dataclass
class Resumo:
    """Fotografia do estado do usuário, base do relatório semanal."""

    ivd: float
    nivel: NivelRisco
    moedas: int
    nivel_escala: int
    exercicios_hoje: int
    intervencoes_hoje: int
    tela_passiva_s: float


@dataclass
class MotorMenteZero:
    """Núcleo determinístico do Mente Zero."""

    plano: Plano = Plano.FREE
    apps_mapeados: frozenset[str] = frozenset()
    semente: int = 0

    ivd: CalculadoraIVD = field(default_factory=CalculadoraIVD)
    banco: BancoDeMinutos = field(init=False)
    leilao: LeilaoDeDistracoes = field(init=False)
    escala: EscalaZero = field(init=False)
    stopper: ScrollStopper = field(init=False)

    dia: int = 0
    intervencoes_hoje: int = 0
    _ultimo_aviso_ts: float | None = None
    _ultima_leitura: LeituraIVD | None = None

    def __post_init__(self) -> None:
        self.banco = BancoDeMinutos(plano=self.plano)
        self.leilao = LeilaoDeDistracoes(plano=self.plano)
        self.escala = EscalaZero(plano=self.plano, semente=self.semente)
        self.stopper = ScrollStopper(plano=self.plano, apps_mapeados=self.apps_mapeados)

    # ------------------------------------------------------------------ API

    def processar(self, evento: EventoUso) -> Intervencao:
        """Ingere uma amostra de uso e devolve a intervenção a executar."""
        self._virar_dia(evento.timestamp)

        leitura = self.ivd.registrar(evento)
        self._ultima_leitura = leitura

        intervencao = self.stopper.registrar(evento)
        if intervencao.ativa:
            return self._emitir(intervencao, evento, conta_cooldown=False)

        if not self._pode_avisar(evento.timestamp):
            return SEM_INTERVENCAO

        if leitura.nivel is NivelRisco.CRITICO:
            return self._emitir(self._intervencao_critica(evento), evento)

        if leitura.nivel is NivelRisco.ALERTA:
            return self._emitir(self._tarefa_relampago(leitura), evento)

        if leitura.nivel is NivelRisco.ATENCAO and evento.categoria.e_distracao:
            return self._emitir(
                Intervencao(
                    TipoIntervencao.ALERTA_SUAVE,
                    mensagem=(
                        f"Seu Índice de Vício Digital está em {leitura.valor:.0f}. "
                        "Ainda dá para escolher."
                    ),
                    payload={"ivd": leitura.valor},
                ),
                evento,
            )

        return SEM_INTERVENCAO

    def solicitar_acesso(self, app_id: str, *, minutos_exercicio: float = 0.0) -> dict:
        """Pedido de acesso a um app de distração (Banco de Minutos + Leilão).

        Devolve um dicionário com ``liberado``, ``via`` ("moeda" ou "leilao"),
        ``saldo`` e ``preco_min`` — o preço da próxima tentativa quando negado.
        """
        if self.banco.pode_gastar(CUSTO_ACESSO_SOCIAL):
            saldo = self.banco.gastar(CUSTO_ACESSO_SOCIAL)
            return {
                "liberado": True,
                "via": "moeda",
                "saldo": saldo,
                "preco_min": self.leilao.preco_min(app_id),
            }

        preco = self.leilao.preco_min(app_id)
        if self.leilao.cobrar(app_id, minutos_exercicio):
            return {
                "liberado": True,
                "via": "leilao",
                "saldo": self.banco.saldo,
                "preco_min": self.leilao.preco_min(app_id),
                "minutos_cobrados": preco,
            }

        return {
            "liberado": False,
            "via": "leilao",
            "saldo": self.banco.saldo,
            "preco_min": preco,
        }

    def proximo_exercicio(self, tipo: TipoExercicio | None = None) -> Exercicio:
        """Entrega o próximo item da Escala ZERO."""
        return self.escala.proximo(tipo)

    def responder_exercicio(
        self, exercicio: Exercicio, resposta: str, tempo_s: float
    ) -> Resultado:
        """Avalia a resposta e converte acerto em moeda de atenção profunda."""
        resultado = self.escala.responder(exercicio, resposta, tempo_s)
        if resultado.moedas_ganhas:
            self.banco.creditar(resultado.moedas_ganhas, origem="exercicio")
        return resultado

    def concluir_missao_offline(self, missao_id: str) -> int:
        """Camada 7: missão offline concluída devolve crédito de foco (PRO)."""
        return self.banco.creditar(1, origem="missao_offline")

    def resumo(self) -> Resumo:
        leitura = self._ultima_leitura
        return Resumo(
            ivd=self.ivd.valor,
            nivel=self.ivd.nivel,
            moedas=self.banco.saldo,
            nivel_escala=self.escala.nivel,
            exercicios_hoje=self.escala.entregues_hoje,
            intervencoes_hoje=self.intervencoes_hoje,
            tela_passiva_s=self.stopper.passivo_total_sessao_s,
        )

    # -------------------------------------------------------------- interno

    def _virar_dia(self, timestamp: float) -> None:
        dia = int(timestamp // SEGUNDOS_POR_DIA)
        if dia == self.dia:
            return
        self.dia = dia
        self.banco.virar_dia(dia)
        self.leilao.virar_dia(dia)
        self.escala.virar_dia(dia)
        self.intervencoes_hoje = 0

    def _pode_avisar(self, timestamp: float) -> bool:
        if self._ultimo_aviso_ts is None:
            return True
        return timestamp - self._ultimo_aviso_ts >= COOLDOWN_AVISOS_S

    def _emitir(
        self, intervencao: Intervencao, evento: EventoUso, *, conta_cooldown: bool = True
    ) -> Intervencao:
        if intervencao.ativa:
            self.intervencoes_hoje += 1
            if conta_cooldown:
                self._ultimo_aviso_ts = evento.timestamp
        return intervencao

    def _intervencao_critica(self, evento: EventoUso) -> Intervencao:
        """Recaída iminente: Eu Futuro (camada 5) ou micro-pausa sensorial."""
        if direitos(self.plano).avatar_personalizado:
            return Intervencao(
                TipoIntervencao.MENSAGEM_EU_FUTURO,
                mensagem=(
                    "Se você rolar agora, eu perderei 2 pontos de QI e 1 hora com "
                    "nossos filhos."
                ),
                payload={"ivd": self.ivd.valor, "personalizada": True},
            )
        indice = int(evento.timestamp) % len(FRASES_MICRO_PAUSA)
        return Intervencao(
            TipoIntervencao.MICRO_PAUSA_SENSORIAL,
            mensagem=FRASES_MICRO_PAUSA[indice],
            duracao_s=20.0,
            payload={
                "tela": "preta",
                "respiracao_guiada": "4-7-8",
                "som": SONS_MICRO_PAUSA[indice % len(SONS_MICRO_PAUSA)],
                "eu_futuro": MENSAGEM_EU_FUTURO_GENERICA,
            },
        )

    def _tarefa_relampago(self, leitura: LeituraIVD) -> Intervencao:
        """Camada 1: alerta não invasivo acompanhado de tarefa-relâmpago."""
        payload: dict = {"ivd": leitura.valor, "sinais": leitura.sinais}
        try:
            exercicio = self.escala.proximo()
        except LimiteDiarioAtingido:
            return Intervencao(
                TipoIntervencao.ALERTA_SUAVE,
                mensagem=(
                    "Seu padrão de rolagem disparou o alerta. Seu exercício de hoje "
                    "já foi usado — respire fundo antes de continuar."
                ),
                payload=payload,
            )
        payload["exercicio"] = exercicio
        return Intervencao(
            TipoIntervencao.TAREFA_RELAMPAGO,
            mensagem="Trinta segundos de cérebro antes de continuar:",
            payload=payload,
        )


__all__ = ["MotorMenteZero", "Resumo"]
