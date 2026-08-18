"""Camada 2 — Modo Foco Profundo e Desafio do Texto Inútil.

* :class:`FocoProfundo` — sessão de 45 minutos: bloqueia apps de distração
  enquanto ativa, entrega um texto longo e só conta como concluída após o tempo
  integral **e** uma interpretação com substância. Retomar a sessão em outro
  dispositivo é recurso PRO (multi-dispositivo).
* :class:`DesafioTextoInutil` (PRO) — parâmetros da sobreposição que degrada a
  legibilidade de propósito (baixo contraste, fonte complexa), forçando o
  Sistema 2. O núcleo entrega os parâmetros; aplicá-los sobre o navegador é
  papel da casca.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import CategoriaApp, Plano
from .planos import direitos
from .recalibragem import RecursoExclusivoPro

#: Duração integral da sessão de Foco Profundo.
DURACAO_FOCO_S = 45 * 60.0

#: Palavras mínimas para a interpretação valer.
MINIMO_INTERPRETACAO = 20


@dataclass(frozen=True)
class TextoLongo:
    id: str
    titulo: str
    trecho: str
    pergunta: str


#: Curadoria inicial; a Fase 3 pluga a biblioteca de leitura interativa aqui.
TEXTOS_LONGOS: tuple[TextoLongo, ...] = (
    TextoLongo(
        "seneca-brevidade",
        "Sêneca — Sobre a brevidade da vida",
        "Não recebemos uma vida curta, nós a tornamos curta; não somos pobres "
        "de tempo, somos pródigos dele. A vida é longa o bastante para quem a "
        "emprega inteira.",
        "Sêneca escreve sobre desperdício de tempo sem conhecer telas. O que "
        "muda e o que permanece no argumento dele aplicado ao seu feed?",
    ),
    TextoLongo(
        "james-atencao",
        "William James — A atenção como escolha",
        "Minha experiência é aquilo a que decido prestar atenção. Apenas os "
        "itens que noto moldam minha mente — sem interesse seletivo, a "
        "experiência é puro caos.",
        "Se a experiência é feita do que se nota, quem esteve fazendo a sua "
        "experiência nas últimas semanas: você ou o algoritmo? Justifique.",
    ),
    TextoLongo(
        "zweig-xadrez",
        "Stefan Zweig — A novela do xadrez (motivo)",
        "Preso sem livros e sem janelas, o doutor B. reconstruiu partidas "
        "inteiras de memória, até que a própria mente virou tabuleiro — prova "
        "de que o intelecto definha sem objeto e adoece sem descanso.",
        "O personagem sofre por excesso de um único estímulo mental. Que "
        "paralelo isso tem com uma tarde inteira de rolagem?",
    ),
)


class SessaoJaAtiva(RuntimeError):
    pass


class SessaoNaoAtiva(RuntimeError):
    pass


class FocoIncompleto(RuntimeError):
    """Tentativa de concluir antes dos 45 minutos."""


class MultiDispositivoIndisponivel(RuntimeError):
    """Retomada em outro dispositivo pedida no plano FREE."""


@dataclass(frozen=True)
class ResultadoFoco:
    concluida: bool
    minutos: float
    interpretacao_aceita: bool
    mensagem: str


@dataclass
class FocoProfundo:
    """Máquina de estados da sessão de Foco Profundo."""

    plano: Plano = Plano.FREE
    inicio_ts: float | None = None
    dispositivo: str | None = None
    texto: TextoLongo | None = None
    sessoes_concluidas: int = 0
    _cursor: int = 0

    # ------------------------------------------------------------------ API

    def em_sessao(self, ts: float) -> bool:
        return self.inicio_ts is not None

    def iniciar(self, ts: float, dispositivo: str = "principal") -> TextoLongo:
        if self.inicio_ts is not None:
            raise SessaoJaAtiva("conclua ou interrompa a sessão atual antes de outra")
        self.inicio_ts = ts
        self.dispositivo = dispositivo
        self.texto = TEXTOS_LONGOS[self._cursor % len(TEXTOS_LONGOS)]
        self._cursor += 1
        return self.texto

    def retomar_em(self, dispositivo: str) -> TextoLongo:
        """Continua a sessão ativa em outro dispositivo (PRO)."""
        if self.inicio_ts is None or self.texto is None:
            raise SessaoNaoAtiva("não há sessão ativa para retomar")
        if dispositivo != self.dispositivo and not direitos(self.plano).foco_profundo_multidispositivo:
            raise MultiDispositivoIndisponivel(
                "sessão multi-dispositivo faz parte do ResetMind Pro"
            )
        self.dispositivo = dispositivo
        return self.texto

    def deve_bloquear(self, categoria: CategoriaApp, ts: float) -> bool:
        """Durante a sessão, apps de distração ficam bloqueados."""
        return self.em_sessao(ts) and categoria.e_distracao

    def progresso(self, ts: float) -> float:
        """Fração 0-1 da sessão decorrida."""
        if self.inicio_ts is None:
            return 0.0
        return max(0.0, min(1.0, (ts - self.inicio_ts) / DURACAO_FOCO_S))

    def interromper(self, ts: float) -> ResultadoFoco:
        if self.inicio_ts is None:
            raise SessaoNaoAtiva("não há sessão ativa")
        minutos = (ts - self.inicio_ts) / 60.0
        self._limpar()
        return ResultadoFoco(
            concluida=False,
            minutos=minutos,
            interpretacao_aceita=False,
            mensagem=f"Sessão interrompida aos {minutos:.0f} min. Contam-se inteiras, "
            "mas cada minuto sustentado já treinou a rede atencional.",
        )

    def concluir(self, ts: float, interpretacao: str) -> ResultadoFoco:
        if self.inicio_ts is None:
            raise SessaoNaoAtiva("não há sessão ativa")
        decorrido = ts - self.inicio_ts
        if decorrido < DURACAO_FOCO_S:
            restante = (DURACAO_FOCO_S - decorrido) / 60.0
            raise FocoIncompleto(f"faltam {restante:.0f} min para os 45 da sessão")
        aceita = len(interpretacao.strip().split()) >= MINIMO_INTERPRETACAO
        minutos = decorrido / 60.0
        self._limpar()
        if aceita:
            self.sessoes_concluidas += 1
            mensagem = "Sessão integral com interpretação: é assim que o foco se alonga."
        else:
            mensagem = (
                "O tempo foi cumprido, mas a interpretação pede mais elaboração — "
                f"desenvolva ao menos {MINIMO_INTERPRETACAO} palavras."
            )
        return ResultadoFoco(
            concluida=aceita, minutos=minutos, interpretacao_aceita=aceita, mensagem=mensagem
        )

    # -------------------------------------------------------------- interno

    def _limpar(self) -> None:
        self.inicio_ts = None
        self.dispositivo = None
        self.texto = None


# --------------------------------------------------------------------------
# Desafio do Texto Inútil (PRO)
# --------------------------------------------------------------------------

#: intensidade -> parâmetros de degradação de legibilidade.
_PARAMETROS_TEXTO_INUTIL = {
    1: {"contraste": 0.45, "fonte": "serifada_ornamental", "espacamento_letras_em": 0.02},
    2: {"contraste": 0.30, "fonte": "serifada_ornamental", "espacamento_letras_em": 0.05},
    3: {"contraste": 0.18, "fonte": "gotica_condensada", "espacamento_letras_em": 0.08},
}


@dataclass
class DesafioTextoInutil:
    """Sobreposição que torna a leitura deliberadamente difícil (Sistema 2)."""

    plano: Plano = Plano.FREE
    ativo: bool = False

    def ativar(self) -> None:
        if not direitos(self.plano).desafio_texto_inutil:
            raise RecursoExclusivoPro(
                "o Desafio do Texto Inútil faz parte do Modo Filósofo (Pro)"
            )
        self.ativo = True

    def desativar(self) -> None:
        self.ativo = False

    def parametros(self, intensidade: int = 2) -> dict:
        if not self.ativo:
            raise RuntimeError("ative o desafio antes de pedir parâmetros")
        if intensidade not in _PARAMETROS_TEXTO_INUTIL:
            raise ValueError("intensidade deve ser 1, 2 ou 3")
        return dict(_PARAMETROS_TEXTO_INUTIL[intensidade])


__all__ = [
    "DURACAO_FOCO_S",
    "DesafioTextoInutil",
    "FocoIncompleto",
    "FocoProfundo",
    "MINIMO_INTERPRETACAO",
    "MultiDispositivoIndisponivel",
    "ResultadoFoco",
    "SessaoJaAtiva",
    "SessaoNaoAtiva",
    "TEXTOS_LONGOS",
    "TextoLongo",
]
