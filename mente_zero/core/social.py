"""Camada 6 — Redes de restauração social não tóxicas.

* :class:`TriboDeSilencio` — grupo de até 12 pessoas, uma reflexão longa por
  membro por semana. Não existe método para mensagem instantânea, indicador de
  presença ou reação: a ausência dessas APIs é a própria regra do produto.
* :class:`GerenciadorTribos` — aplica o limite de tribos do plano (1 no FREE).
* :class:`FeedMaieutico` — perguntas socráticas; o usuário só vê respostas
  alheias depois de escrever a sua. FREE limitado a 3 perguntas por semana.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Plano
from .planos import direitos

# --------------------------------------------------------------------------
# Tribos de Silêncio
# --------------------------------------------------------------------------

LIMITE_MEMBROS = 12

#: Comprimento mínimo (caracteres) de uma reflexão em texto; força texto longo.
MINIMO_REFLEXAO = 280


class TriboCheia(RuntimeError):
    pass


class ForaDaTribo(RuntimeError):
    pass


class ReflexaoJaEnviada(RuntimeError):
    pass


class ReflexaoCurta(ValueError):
    pass


class LimiteDeTribos(RuntimeError):
    pass


@dataclass(frozen=True)
class Reflexao:
    membro: str
    semana: int
    conteudo: str
    em_audio: bool = False


@dataclass
class TriboDeSilencio:
    """Grupo lento: uma reflexão semanal por membro, nada de chat."""

    nome: str
    membros: set[str] = field(default_factory=set)
    reflexoes: list[Reflexao] = field(default_factory=list)

    def entrar(self, membro: str) -> None:
        if membro in self.membros:
            return
        if len(self.membros) >= LIMITE_MEMBROS:
            raise TriboCheia(f"a tribo '{self.nome}' já tem {LIMITE_MEMBROS} pessoas")
        self.membros.add(membro)

    def sair(self, membro: str) -> None:
        self.membros.discard(membro)

    def refletir(
        self, membro: str, semana: int, conteudo: str, *, em_audio: bool = False
    ) -> Reflexao:
        if membro not in self.membros:
            raise ForaDaTribo(f"{membro} não pertence à tribo '{self.nome}'")
        if any(r.membro == membro and r.semana == semana for r in self.reflexoes):
            raise ReflexaoJaEnviada("uma reflexão por semana; a próxima abre na semana seguinte")
        if not em_audio and len(conteudo.strip()) < MINIMO_REFLEXAO:
            raise ReflexaoCurta(
                f"reflexão em texto pede pelo menos {MINIMO_REFLEXAO} caracteres — "
                "aqui a lentidão é o recurso"
            )
        reflexao = Reflexao(membro, semana, conteudo, em_audio)
        self.reflexoes.append(reflexao)
        return reflexao

    def mural_da_semana(self, semana: int) -> tuple[Reflexao, ...]:
        return tuple(r for r in self.reflexoes if r.semana == semana)


@dataclass
class GerenciadorTribos:
    """Vínculo usuário ↔ tribos, com o limite do plano."""

    plano: Plano = Plano.FREE
    tribos: dict[str, TriboDeSilencio] = field(default_factory=dict)

    def entrar(self, usuario: str, tribo: TriboDeSilencio) -> None:
        limite = direitos(self.plano).tribos_simultaneas
        atuais = sum(1 for t in self.tribos.values() if usuario in t.membros)
        if tribo.nome in self.tribos and usuario in self.tribos[tribo.nome].membros:
            return
        if limite is not None and atuais >= limite:
            raise LimiteDeTribos(
                f"o plano {self.plano.value} participa de {limite} tribo(s) por vez"
            )
        tribo.entrar(usuario)
        self.tribos[tribo.nome] = tribo


# --------------------------------------------------------------------------
# Feed de Perguntas Maiêuticas
# --------------------------------------------------------------------------

PERGUNTAS_MAIEUTICAS: tuple[str, ...] = (
    "Qual crença sua mudou no último ano e por quê?",
    "O que você faria se ninguém pudesse ver?",
    "Que pergunta você anda evitando se fazer?",
    "O que o tédio tenta lhe dizer quando você o interrompe?",
    "De quem é a voz que fala quando você se critica?",
    "O que você chamaria de 'tempo bem perdido'?",
    "Qual hábito seu pertence mais ao algoritmo do que a você?",
    "O que você saberia fazer aos dez anos que desaprendeu?",
)


class CotaSemanalEsgotada(RuntimeError):
    pass


class RespostaPendente(RuntimeError):
    pass


@dataclass
class FeedMaieutico:
    """Feed socrático: responder antes de ler é a mecânica central."""

    plano: Plano = Plano.FREE
    semana: int = 0
    abertas_na_semana: int = 0
    respondidas: dict[str, str] = field(default_factory=dict)   # pergunta -> resposta
    _mural: dict[str, list[str]] = field(default_factory=dict)  # respostas anônimas

    def virar_semana(self, semana: int) -> None:
        if semana != self.semana:
            self.semana = semana
            self.abertas_na_semana = 0

    def proxima_pergunta(self) -> str:
        cota = direitos(self.plano).perguntas_maieuticas_semana
        if cota is not None and self.abertas_na_semana >= cota:
            raise CotaSemanalEsgotada(
                f"o plano {self.plano.value} abre {cota} perguntas por semana"
            )
        pergunta = PERGUNTAS_MAIEUTICAS[
            (len(self.respondidas) + self.abertas_na_semana) % len(PERGUNTAS_MAIEUTICAS)
        ]
        self.abertas_na_semana += 1
        return pergunta

    def responder(self, pergunta: str, resposta: str) -> None:
        if len(resposta.strip().split()) < 5:
            raise ValueError("responda com uma frase inteira — o feed é lento de propósito")
        self.respondidas[pergunta] = resposta
        self._mural.setdefault(pergunta, []).append(resposta)

    def respostas_anonimas(self, pergunta: str) -> tuple[str, ...]:
        """Só abre o mural de quem já respondeu — o coração do modo maiêutico."""
        if pergunta not in self.respondidas:
            raise RespostaPendente("escreva a sua resposta antes de ler as dos outros")
        alheias = [r for r in self._mural.get(pergunta, []) if r != self.respondidas[pergunta]]
        return tuple(alheias)

    def semear_mural(self, pergunta: str, respostas: list[str]) -> None:
        """Ponto de entrada para respostas vindas do backend social."""
        self._mural.setdefault(pergunta, []).extend(respostas)


__all__ = [
    "CotaSemanalEsgotada",
    "FeedMaieutico",
    "ForaDaTribo",
    "GerenciadorTribos",
    "LIMITE_MEMBROS",
    "LimiteDeTribos",
    "MINIMO_REFLEXAO",
    "PERGUNTAS_MAIEUTICAS",
    "Reflexao",
    "ReflexaoCurta",
    "ReflexaoJaEnviada",
    "RespostaPendente",
    "TriboCheia",
    "TriboDeSilencio",
]
