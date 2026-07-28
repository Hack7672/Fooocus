"""Camada 4 — Intervenção direta na rolagem e economia da atenção.

Três mecanismos, todos determinísticos e testáveis:

* :class:`ScrollStopper` — máquina de estados que congela a tela após 2 minutos
  de rolagem passiva e aplica tela cinza quando o congelamento é ignorado.
* :class:`BancoDeMinutos` — moedas diárias de atenção profunda: acessar rede
  social custa 1 moeda; exercícios e missões offline devolvem moedas.
* :class:`LeilaoDeDistracoes` — preço em minutos de exercício difícil para
  destravar um app bloqueado, subindo exponencialmente a cada tentativa do dia.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .models import EventoUso, Intervencao, Plano, TipoIntervencao
from .planos import direitos

# --------------------------------------------------------------------------
# Scroll Stopper
# --------------------------------------------------------------------------

#: Rolagem passiva acumulada (s) que dispara o congelamento.
LIMITE_ROLAGEM_PASSIVA_S = 120.0

#: Tempo (s) que o usuário tem para responder ao congelamento.
JANELA_RESPOSTA_S = 20.0

#: Duração (s) da tela cinza quando o congelamento é ignorado.
DURACAO_TELA_CINZA_S = 15.0

#: Tela passiva acumulada (s) que dispara a janela de reflexão obrigatória.
LIMITE_JANELA_REFLEXAO_S = 1500.0  # 25 min

#: Intervalo (s) sem rolagem passiva que zera o acumulador.
INTERVALO_RESET_S = 90.0

PERGUNTA_REFLEXAO = "O que você estava evitando sentir quando pegou o celular?"


class EstadoStopper(str, Enum):
    OBSERVANDO = "observando"
    CONGELADO = "congelado"
    CINZA = "cinza"


@dataclass
class ScrollStopper:
    """Máquina de estados do Scroll Stopper.

    Regras (documento-mestre, camada 4):

    * 2 min de rolagem passiva → tela congela com a escolha "continuar" ou
      "desafio de 1 minuto";
    * congelamento ignorado por ``JANELA_RESPOSTA_S`` → tela cinza por 15 s;
    * 25 min de tela passiva acumulada → janela de reflexão obrigatória.

    No plano FREE o stopper só age em apps de feed mapeados; no PRO ele também
    considera qualquer app cuja categoria seja de distração.
    """

    plano: Plano = Plano.FREE
    apps_mapeados: frozenset[str] = frozenset()
    estado: EstadoStopper = EstadoStopper.OBSERVANDO
    passivo_acumulado_s: float = 0.0
    passivo_total_sessao_s: float = 0.0
    _congelado_em: float | None = None
    _cinza_ate: float | None = None
    _reflexao_emitida: bool = False
    _ultimo_ts: float | None = None

    def monitora(self, evento: EventoUso) -> bool:
        """Diz se este evento está no escopo de atuação do stopper."""
        if not evento.categoria.e_distracao:
            return False
        if self.plano is Plano.PRO:
            return True
        return not self.apps_mapeados or evento.app_id in self.apps_mapeados

    def registrar(self, evento: EventoUso) -> Intervencao:
        """Ingere uma amostra e devolve a intervenção correspondente."""
        agora = evento.timestamp

        if self._cinza_ate is not None:
            if agora < self._cinza_ate:
                return Intervencao(
                    TipoIntervencao.TELA_CINZA,
                    duracao_s=self._cinza_ate - agora,
                )
            self._encerrar_ciclo()

        if not self.monitora(evento):
            self._decair(agora)
            self._ultimo_ts = agora
            return Intervencao(TipoIntervencao.NENHUMA)

        if self._ultimo_ts is not None and agora - self._ultimo_ts > INTERVALO_RESET_S:
            self.passivo_acumulado_s = 0.0
        self._ultimo_ts = agora

        if evento.e_passivo:
            self.passivo_acumulado_s += evento.duracao_s
            self.passivo_total_sessao_s += evento.duracao_s
        else:
            # Interação intencional não é scroll zumbi: alivia o acumulador.
            self.passivo_acumulado_s = max(0.0, self.passivo_acumulado_s - evento.duracao_s)

        if (
            not self._reflexao_emitida
            and self.passivo_total_sessao_s >= LIMITE_JANELA_REFLEXAO_S
        ):
            self._reflexao_emitida = True
            return Intervencao(
                TipoIntervencao.JANELA_REFLEXAO,
                mensagem=PERGUNTA_REFLEXAO,
                payload={"tela_passiva_s": self.passivo_total_sessao_s},
            )

        if self.estado is EstadoStopper.CONGELADO:
            assert self._congelado_em is not None
            if agora - self._congelado_em >= JANELA_RESPOSTA_S:
                self.estado = EstadoStopper.CINZA
                self._cinza_ate = agora + DURACAO_TELA_CINZA_S
                return Intervencao(
                    TipoIntervencao.TELA_CINZA, duracao_s=DURACAO_TELA_CINZA_S
                )
            return Intervencao(
                TipoIntervencao.SCROLL_STOPPER,
                mensagem="Continuar ou desafio de 1 minuto para fortalecer seu cérebro?",
                payload={"repetido": True},
            )

        if self.passivo_acumulado_s >= LIMITE_ROLAGEM_PASSIVA_S:
            self.estado = EstadoStopper.CONGELADO
            self._congelado_em = agora
            return Intervencao(
                TipoIntervencao.SCROLL_STOPPER,
                mensagem="Continuar ou desafio de 1 minuto para fortalecer seu cérebro?",
                payload={"rolagem_passiva_s": self.passivo_acumulado_s},
            )

        return Intervencao(TipoIntervencao.NENHUMA)

    def responder(self, aceitou_desafio: bool) -> None:
        """Registra a resposta do usuário ao congelamento."""
        self._encerrar_ciclo()
        if aceitou_desafio:
            self.passivo_total_sessao_s = 0.0
            self._reflexao_emitida = False

    def _encerrar_ciclo(self) -> None:
        self.estado = EstadoStopper.OBSERVANDO
        self.passivo_acumulado_s = 0.0
        self._congelado_em = None
        self._cinza_ate = None

    def _decair(self, agora: float) -> None:
        if self._ultimo_ts is not None and agora - self._ultimo_ts > INTERVALO_RESET_S:
            self.passivo_acumulado_s = 0.0


# --------------------------------------------------------------------------
# Banco de Minutos de Vida
# --------------------------------------------------------------------------

#: Teto de moedas conquistadas por dia, para que o banco não vire moeda infinita.
TETO_MOEDAS_CONQUISTADAS = 3

#: Custo em moedas de uma abertura de rede social.
CUSTO_ACESSO_SOCIAL = 1


class SaldoInsuficiente(RuntimeError):
    """Levantada quando não há moedas para pagar o acesso."""


@dataclass
class BancoDeMinutos:
    """Moedas de atenção profunda (4 no FREE, 6 no PRO)."""

    plano: Plano = Plano.FREE
    dia: int = 0                      # dia ordinal corrente
    saldo: int = -1                   # -1 = ainda não inicializado
    conquistadas_hoje: int = 0

    def __post_init__(self) -> None:
        if self.saldo < 0:
            self.saldo = direitos(self.plano).moedas_diarias

    def virar_dia(self, dia: int) -> None:
        """Recarrega o saldo diário. Moedas não acumulam entre dias."""
        if dia == self.dia:
            return
        self.dia = dia
        self.saldo = direitos(self.plano).moedas_diarias
        self.conquistadas_hoje = 0

    def pode_gastar(self, custo: int = CUSTO_ACESSO_SOCIAL) -> bool:
        return self.saldo >= custo

    def gastar(self, custo: int = CUSTO_ACESSO_SOCIAL) -> int:
        """Debita ``custo`` moedas e devolve o saldo restante."""
        if custo <= 0:
            raise ValueError("custo deve ser positivo")
        if not self.pode_gastar(custo):
            raise SaldoInsuficiente(
                f"saldo {self.saldo} insuficiente para custo {custo}"
            )
        self.saldo -= custo
        return self.saldo

    def creditar(self, quantidade: int = 1, *, origem: str = "exercicio") -> int:
        """Credita moedas conquistadas com exercícios ou missões offline.

        Missões offline só geram crédito no PRO (créditos de foco bônus).
        O total conquistado por dia é limitado por ``TETO_MOEDAS_CONQUISTADAS``.
        """
        if quantidade <= 0:
            raise ValueError("quantidade deve ser positiva")
        if origem == "missao_offline" and not direitos(self.plano).creditos_bonus_missoes:
            return self.saldo

        espaco = TETO_MOEDAS_CONQUISTADAS - self.conquistadas_hoje
        creditado = max(0, min(quantidade, espaco))
        self.saldo += creditado
        self.conquistadas_hoje += creditado
        return self.saldo


# --------------------------------------------------------------------------
# Leilão de distrações
# --------------------------------------------------------------------------

#: Preço inicial em minutos de exercício lógico difícil.
PRECO_BASE_MIN = 5.0

#: Teto de preço, para que o leilão continue sendo um pedágio e não uma parede.
PRECO_TETO_MIN = 60.0


@dataclass
class LeilaoDeDistracoes:
    """Preço exponencial para destravar um app bloqueado.

    ``preco(app) = PRECO_BASE_MIN * crescimento ** tentativas_do_dia(app)``,
    limitado por ``PRECO_TETO_MIN``. O crescimento é mais agressivo no PRO.
    """

    plano: Plano = Plano.FREE
    dia: int = 0
    tentativas: dict[str, int] = field(default_factory=dict)

    def virar_dia(self, dia: int) -> None:
        if dia != self.dia:
            self.dia = dia
            self.tentativas.clear()

    def preco_min(self, app_id: str) -> float:
        crescimento = direitos(self.plano).crescimento_leilao
        preco = PRECO_BASE_MIN * (crescimento ** self.tentativas.get(app_id, 0))
        return min(PRECO_TETO_MIN, preco)

    def cobrar(self, app_id: str, minutos_pagos: float) -> bool:
        """Tenta destravar o app pagando ``minutos_pagos`` de exercício.

        Devolve ``True`` quando o acesso é liberado; nesse caso a próxima
        tentativa do dia para o mesmo app fica mais cara.
        """
        preco = self.preco_min(app_id)
        if minutos_pagos + 1e-9 < preco:
            return False
        self.tentativas[app_id] = self.tentativas.get(app_id, 0) + 1
        return True


__all__ = [
    "BancoDeMinutos",
    "EstadoStopper",
    "LeilaoDeDistracoes",
    "SaldoInsuficiente",
    "ScrollStopper",
]
