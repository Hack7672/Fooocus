"""Tipos de domínio compartilhados pelo motor de reset cognitivo.

Tudo aqui é puro (sem I/O, sem dependências externas) para que o núcleo possa
ser embarcado em backend, mobile ou reimplementado a partir dos testes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Plano(str, Enum):
    """Planos comerciais descritos no documento-mestre (seção 3)."""

    FREE = "free"
    PRO = "pro"


class CategoriaApp(str, Enum):
    """Categoria do app em uso, usada para pesar sinais do IVD."""

    FEED_SOCIAL = "feed_social"       # Instagram, TikTok, Reels, Shorts...
    MENSAGEM = "mensagem"
    LEITURA = "leitura"
    PRODUTIVIDADE = "produtividade"
    OUTRO = "outro"

    @property
    def e_distracao(self) -> bool:
        return self is CategoriaApp.FEED_SOCIAL


class NivelRisco(str, Enum):
    """Faixas do Índice de Vício Digital."""

    CALMO = "calmo"
    ATENCAO = "atencao"
    ALERTA = "alerta"
    CRITICO = "critico"


class TipoIntervencao(str, Enum):
    """Intervenções que o motor pode emitir (camadas 1 e 4)."""

    NENHUMA = "nenhuma"
    ALERTA_SUAVE = "alerta_suave"                 # camada 1
    TAREFA_RELAMPAGO = "tarefa_relampago"         # camada 1
    MICRO_PAUSA_SENSORIAL = "micro_pausa_sensorial"  # anti-dopamina rápida
    SCROLL_STOPPER = "scroll_stopper"             # camada 4
    TELA_CINZA = "tela_cinza"                     # camada 4
    JANELA_REFLEXAO = "janela_reflexao"           # 25 min de tela passiva
    MENSAGEM_EU_FUTURO = "mensagem_eu_futuro"     # camada 5


class TipoExercicio(str, Enum):
    """Famílias da Escala ZERO (camada 2)."""

    LOGICA = "logica"
    ESPACIAL = "espacial"
    ANALOGIA_VERBAL = "analogia_verbal"
    SEQUENCIA_ABSTRATA = "sequencia_abstrata"
    ALTERNANCIA_TAREFAS = "alternancia_tarefas"
    ASSOCIACAO_FORCADA = "associacao_forcada"


#: Tipos liberados no plano FREE (um exercício lógico diário, Escala ZERO básica).
TIPOS_BASICOS = (TipoExercicio.LOGICA, TipoExercicio.SEQUENCIA_ABSTRATA)


@dataclass(frozen=True)
class EventoUso:
    """Amostra bruta de uso do aparelho, emitida pelo agente do SO.

    Uma amostra cobre uma janela contínua de ``duracao_s`` segundos dentro de um
    único app. O agente móvel deve emitir uma amostra a cada ~5 s de tela ligada.
    """

    timestamp: float                    # epoch em segundos
    app_id: str
    categoria: CategoriaApp
    duracao_s: float                    # duração da amostra
    distancia_scroll_px: float = 0.0    # pixels rolados na amostra
    toques: int = 0                     # toques intencionais (curtir, comentar, abrir)
    inversoes_direcao: int = 0          # trocas de sentido do scroll
    abertura_app: bool = False          # a amostra inicia uma nova abertura do app
    hora_local: int | None = None       # 0-23; usado para penalizar madrugada

    def __post_init__(self) -> None:
        if self.duracao_s <= 0:
            raise ValueError("duracao_s deve ser positiva")
        if self.hora_local is not None and not 0 <= self.hora_local <= 23:
            raise ValueError("hora_local deve estar entre 0 e 23")

    @property
    def velocidade_scroll(self) -> float:
        """Pixels por segundo."""
        return self.distancia_scroll_px / self.duracao_s

    @property
    def e_passivo(self) -> bool:
        """Rolagem sem interação intencional — a assinatura do scroll zumbi."""
        return self.distancia_scroll_px > 0 and self.toques == 0


@dataclass
class Intervencao:
    """Decisão do motor a ser executada pela camada de apresentação."""

    tipo: TipoIntervencao
    mensagem: str = ""
    duracao_s: float = 0.0
    payload: dict = field(default_factory=dict)

    @property
    def ativa(self) -> bool:
        return self.tipo is not TipoIntervencao.NENHUMA


#: Intervenção nula reutilizável.
SEM_INTERVENCAO = Intervencao(TipoIntervencao.NENHUMA)
