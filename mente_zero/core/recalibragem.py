"""Camada 3 — Recalibragem emocional e saúde mental.

Três componentes determinísticos:

* :class:`TermometroEmocional` — triagem lexical do check-in diário. É um
  **placeholder honesto** para o modelo de NLP da Fase 3: classifica por
  vocabulário, nunca diagnostica, e qualquer menção a crise grave devolve
  orientação de buscar ajuda humana em vez de sugestão do app.
* :class:`DiaZero` — reset semanal de dopamina: plano offline guiado e
  relatório de reconexão, com cota mensal por plano (1 no FREE, livre no PRO).
* :class:`DiarioMenteRestaurada` — o diário do PRO. O núcleo guarda apenas as
  entradas em memória; **criptografia e armazenamento são obrigação da casca**.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from enum import Enum

from .models import Plano
from .planos import direitos

# --------------------------------------------------------------------------
# Termômetro emocional
# --------------------------------------------------------------------------


class EstadoEmocional(str, Enum):
    SERENO = "sereno"
    TENSAO = "tensao"
    ANSIEDADE_DIGITAL = "ansiedade_digital"
    ENCAMINHAR_AJUDA = "encaminhar_ajuda"


#: Vocabulário de triagem. Deliberadamente simples e auditável; o modelo de
#: NLP da Fase 3 o substitui mantendo o mesmo contrato de saída.
_LEXICO_ANSIEDADE = frozenset(
    """ansioso ansiosa ansiedade angustia agitado agitada inquieto inquieta
    culpa culpado culpada vicio viciado viciada compulsao compulsivo travado
    travada perdido perdida vazio vazia exausto exausta esgotado esgotada
    sobrecarregado sobrecarregada insonia nervoso nervosa preocupado preocupada
    medo panico""".split()
)

_LEXICO_DIGITAL = frozenset(
    """celular telefone tela rolagem scroll feed reels shorts rede redes
    notificacao notificacoes instagram tiktok video videos likes curtidas""".split()
)

#: Sinais de crise que curto-circuitam qualquer sugestão do app.
_LEXICO_CRISE = frozenset(
    """suicidio suicida morrer machucar automutilacao desistir-de-viver""".split()
)

MENSAGEM_AJUDA = (
    "O que você escreveu merece mais do que um app. Procure alguém de confiança "
    "ou um serviço de apoio emocional — no Brasil, o CVV atende no 188, todos os "
    "dias, de graça."
)


def _normalizar(texto: str) -> list[str]:
    sem_acentos = "".join(
        c for c in unicodedata.normalize("NFD", texto.casefold())
        if unicodedata.category(c) != "Mn"
    )
    return [p.strip(".,!?;:()\"'") for p in sem_acentos.split()]


@dataclass(frozen=True)
class Avaliacao:
    estado: EstadoEmocional
    escore: float                  # 0-1: densidade de vocabulário de ansiedade
    contexto_digital: bool         # a ansiedade menciona telas/redes?
    sugestao: str


class TermometroEmocional:
    """Triagem lexical do check-in (voz transcrita ou texto)."""

    def avaliar(self, texto: str) -> Avaliacao:
        palavras = _normalizar(texto)
        if not palavras:
            return Avaliacao(EstadoEmocional.SERENO, 0.0, False, "")

        if any(p in _LEXICO_CRISE for p in palavras):
            return Avaliacao(
                EstadoEmocional.ENCAMINHAR_AJUDA, 1.0, False, MENSAGEM_AJUDA
            )

        ansiosas = sum(1 for p in palavras if p in _LEXICO_ANSIEDADE)
        escore = min(1.0, ansiosas / max(6, len(palavras)) * 4)
        digital = any(p in _LEXICO_DIGITAL for p in palavras)

        if escore >= 0.5:
            estado = EstadoEmocional.ANSIEDADE_DIGITAL if digital else EstadoEmocional.TENSAO
            sugestao = (
                "Escrita terapêutica: descreva em cinco linhas o que estava "
                "acontecendo antes de pegar o celular."
                if digital
                else "Micro-meditação de 3 minutos com respiração 4-7-8."
            )
        elif escore >= 0.2:
            estado = EstadoEmocional.TENSAO
            sugestao = "Micro-meditação de 3 minutos com respiração 4-7-8."
        else:
            estado = EstadoEmocional.SERENO
            sugestao = ""
        return Avaliacao(estado, escore, digital, sugestao)


# --------------------------------------------------------------------------
# Dia Zero
# --------------------------------------------------------------------------

PLANO_OFFLINE_GUIADO = (
    "Caminhada de 40 minutos sem fones",
    "Leitura de 30 páginas em papel",
    "Uma conversa longa, presencial, sem celular na mesa",
    "Refeição sem tela alguma",
    "Escrever à mão três coisas que você notou no dia",
)


class CotaMensalEsgotada(RuntimeError):
    """Plano FREE já usou o Dia Zero deste mês."""


class DiaZeroNaoIniciado(RuntimeError):
    """Relatório pedido sem um Dia Zero em curso."""


@dataclass(frozen=True)
class RelatorioReconexao:
    mes: int
    atividades_concluidas: tuple[str, ...]
    taxa_conclusao: float
    mensagem: str


@dataclass
class DiaZero:
    """Reset semanal de dopamina com cota mensal por plano."""

    plano: Plano = Plano.FREE
    mes: int = 0
    usados_no_mes: int = 0
    em_curso: bool = False

    def disponivel(self, mes: int) -> bool:
        cota = direitos(self.plano).dias_zero_por_mes
        if mes != self.mes:
            return True
        return cota is None or self.usados_no_mes < cota

    def iniciar(self, mes: int) -> tuple[str, ...]:
        """Abre o Dia Zero e devolve o plano offline guiado."""
        if mes != self.mes:
            self.mes = mes
            self.usados_no_mes = 0
        if not self.disponivel(mes):
            raise CotaMensalEsgotada(
                "o plano FREE inclui um Dia Zero por mês; o próximo abre no mês seguinte"
            )
        self.usados_no_mes += 1
        self.em_curso = True
        return PLANO_OFFLINE_GUIADO

    def concluir(self, atividades_concluidas: tuple[str, ...]) -> RelatorioReconexao:
        if not self.em_curso:
            raise DiaZeroNaoIniciado("inicie o Dia Zero antes de concluí-lo")
        self.em_curso = False
        feitas = tuple(a for a in atividades_concluidas if a in PLANO_OFFLINE_GUIADO)
        taxa = len(feitas) / len(PLANO_OFFLINE_GUIADO)
        if taxa >= 0.8:
            mensagem = "Um dia inteiro seu. É assim que a atenção volta para casa."
        elif taxa >= 0.4:
            mensagem = "Metade do caminho offline já muda o tônus da semana."
        else:
            mensagem = "Começar conta. No próximo Dia Zero, escolha uma atividade e proteja-a."
        return RelatorioReconexao(self.mes, feitas, taxa, mensagem)


# --------------------------------------------------------------------------
# Diário da Mente Restaurada (PRO)
# --------------------------------------------------------------------------

PERGUNTA_DIARIO = "O que você estava evitando sentir quando pegou o celular?"


class RecursoExclusivoPro(RuntimeError):
    """Recurso presente apenas no plano PRO."""


@dataclass
class DiarioMenteRestaurada:
    """Diário guiado do PRO.

    O núcleo mantém as entradas apenas em memória de processo; persistir exige
    criptografia no dispositivo (obrigação da casca, ver ARQUITETURA.md §6).
    """

    plano: Plano = Plano.FREE
    _entradas: list[tuple[float, str]] = field(default_factory=list)

    def _exigir_pro(self) -> None:
        if not direitos(self.plano).diario_mente_restaurada:
            raise RecursoExclusivoPro(
                "o Diário da Mente Restaurada faz parte do ResetMind Pro"
            )

    def pergunta(self) -> str:
        self._exigir_pro()
        return PERGUNTA_DIARIO

    def registrar(self, timestamp: float, texto: str) -> int:
        """Guarda uma entrada e devolve o total de entradas."""
        self._exigir_pro()
        if not texto.strip():
            raise ValueError("a entrada não pode ser vazia")
        self._entradas.append((timestamp, texto))
        return len(self._entradas)

    @property
    def total(self) -> int:
        return len(self._entradas)


__all__ = [
    "Avaliacao",
    "CotaMensalEsgotada",
    "DiaZero",
    "DiaZeroNaoIniciado",
    "DiarioMenteRestaurada",
    "EstadoEmocional",
    "MENSAGEM_AJUDA",
    "PERGUNTA_DIARIO",
    "PLANO_OFFLINE_GUIADO",
    "RecursoExclusivoPro",
    "RelatorioReconexao",
    "TermometroEmocional",
]
