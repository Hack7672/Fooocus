"""Camada 7 — Integração com o mundo físico (Protocolo Realidade).

* :class:`ProtocoloRealidade` — propõe missão de mapeamento cognitivo após
  longa permanência em casa e valida a conclusão (a geolocalização em si é da
  casca; o núcleo decide *quando* propor e *o que* pedir).
* :func:`cronograma_detox` — a agenda do detox sensorial: som ambiente e um
  lembrete a cada 5 minutos.
* :class:`FeedNutritivo` — um item de alta densidade por vez; o próximo só
  destrava depois de uma reflexão sobre o atual.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Plano

# --------------------------------------------------------------------------
# Missões offline
# --------------------------------------------------------------------------

#: Horas contínuas em casa que disparam a proposta de missão.
HORAS_EM_CASA_PARA_MISSAO = 6.0

#: (id, título, instrução de atenção espacial)
MISSOES: tuple[tuple[str, str, str], ...] = (
    (
        "ponto-historico",
        "Mapeamento cognitivo: o prédio que você nunca olhou",
        "Caminhe até uma construção antiga do bairro e descreva três detalhes "
        "arquitetônicos que você nunca tinha notado.",
    ),
    (
        "rota-nova",
        "A rua paralela",
        "Faça um trajeto conhecido por uma rua paralela e registre o que muda: "
        "sons, cheiros, ritmo das pessoas.",
    ),
    (
        "arvore-mais-antiga",
        "A árvore mais antiga",
        "Encontre a árvore que parece mais antiga num raio de dez quarteirões e "
        "estime a idade dela pelos sinais que encontrar.",
    ),
    (
        "cartografia-de-sons",
        "Cartografia de sons",
        "Sente-se numa praça por dez minutos e liste todos os sons na ordem em "
        "que os perceber, do mais próximo ao mais distante.",
    ),
)


@dataclass(frozen=True)
class Missao:
    id: str
    titulo: str
    instrucao: str


@dataclass
class ProtocoloRealidade:
    """Propositor de missões offline."""

    plano: Plano = Plano.FREE
    concluidas: list[str] = field(default_factory=list)
    _cursor: int = 0

    def propor_missao(self, horas_em_casa: float) -> Missao | None:
        """Propõe uma missão quando a permanência em casa passa do limiar."""
        if horas_em_casa < HORAS_EM_CASA_PARA_MISSAO:
            return None
        id_, titulo, instrucao = MISSOES[self._cursor % len(MISSOES)]
        self._cursor += 1
        return Missao(id_, titulo, instrucao)

    def concluir(self, missao: Missao, relato: str) -> bool:
        """Valida a conclusão pelo relato de observação (mínimo de substância)."""
        if len(relato.strip().split()) < 10:
            return False
        self.concluidas.append(missao.id)
        return True


# --------------------------------------------------------------------------
# Detox sensorial programado
# --------------------------------------------------------------------------

SONS_AMBIENTE = ("floresta_3d", "cafeteria_tranquila")
INTERVALO_LEMBRETE_S = 300.0
LEMBRETE = "Você está no mundo real. Olhe ao redor."


@dataclass(frozen=True)
class PassoDetox:
    em_s: float
    acao: str            # "iniciar_som" | "vibrar"
    detalhe: str


def cronograma_detox(duracao_min: float, som: str = SONS_AMBIENTE[0]) -> tuple[PassoDetox, ...]:
    """Gera a agenda executável do detox: som contínuo + vibração a cada 5 min."""
    if duracao_min <= 0:
        raise ValueError("duracao_min deve ser positiva")
    if som not in SONS_AMBIENTE:
        raise ValueError(f"som desconhecido: {som!r}")
    passos = [PassoDetox(0.0, "iniciar_som", som)]
    momento = INTERVALO_LEMBRETE_S
    fim = duracao_min * 60.0
    while momento <= fim:
        passos.append(PassoDetox(momento, "vibrar", LEMBRETE))
        momento += INTERVALO_LEMBRETE_S
    return tuple(passos)


# --------------------------------------------------------------------------
# Feed Nutritivo
# --------------------------------------------------------------------------

#: (título, corpo). Curadoria inicial; a Fase 5 pluga curadoria dinâmica aqui.
ITENS_NUTRITIVOS: tuple[tuple[str, str], ...] = (
    (
        "O paradoxo da escolha do navio de Teseu",
        "Se cada prancha de um navio for trocada, ele continua o mesmo navio? "
        "E se as pranchas antigas forem remontadas ao lado?",
    ),
    (
        "Por que 0,999... é exatamente 1",
        "Chame x = 0,999...; então 10x = 9,999...; subtraindo, 9x = 9, logo x = 1. "
        "O desconforto que sobra diz mais sobre intuição do que sobre matemática.",
    ),
    (
        "Microensaio: a atenção como moeda",
        "Toda economia da atenção pressupõe que ela é finita. O que muda em um dia "
        "vivido como quem gasta uma moeda que não volta?",
    ),
    (
        "O problema da ponte de Königsberg",
        "Euler provou que não há passeio que cruze cada uma das sete pontes uma "
        "única vez — e fundou a teoria dos grafos ao explicar por quê.",
    ),
)


class ReflexaoPendente(RuntimeError):
    pass


@dataclass
class FeedNutritivo:
    """Um item por vez; a reflexão destrava o próximo."""

    _cursor: int = 0
    _aguardando_reflexao: bool = False
    reflexoes: list[str] = field(default_factory=list)

    def proximo_item(self) -> tuple[str, str]:
        if self._aguardando_reflexao:
            raise ReflexaoPendente(
                "reflita sobre o item atual antes de pedir o próximo — "
                "aqui não existe rolagem"
            )
        item = ITENS_NUTRITIVOS[self._cursor % len(ITENS_NUTRITIVOS)]
        self._cursor += 1
        self._aguardando_reflexao = True
        return item

    def refletir(self, texto: str) -> None:
        if len(texto.strip().split()) < 5:
            raise ValueError("uma reflexão pede ao menos uma frase inteira")
        self.reflexoes.append(texto)
        self._aguardando_reflexao = False


__all__ = [
    "FeedNutritivo",
    "HORAS_EM_CASA_PARA_MISSAO",
    "INTERVALO_LEMBRETE_S",
    "ITENS_NUTRITIVOS",
    "LEMBRETE",
    "MISSOES",
    "Missao",
    "PassoDetox",
    "ProtocoloRealidade",
    "ReflexaoPendente",
    "SONS_AMBIENTE",
    "cronograma_detox",
]
