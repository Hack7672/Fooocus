"""Camada 1 — Índice de Vício Digital (IVD).

O IVD é um escalar 0-100 que resume, em tempo real, o quanto o comportamento
atual se parece com rolagem compulsiva. Ele combina cinco sinais observáveis
pelo agente do sistema operacional, sem exigir conteúdo da tela:

1. **Velocidade de scroll** — quanto mais rápido, menos leitura, mais varredura.
2. **Passividade** — rolar sem tocar em nada é a assinatura do consumo zumbi.
3. **Monotonia** — scroll de sentido único, sem voltar para reler.
4. **Permanência contínua** — tempo ininterrupto dentro do app de feed.
5. **Reentradas** — quantas vezes o app foi reaberto na última hora.

O índice é suavizado por média móvel exponencial em tempo contínuo, de modo que
amostras de durações diferentes tenham peso proporcional ao tempo que cobrem.
Uso fora de apps de distração puxa o índice de volta para a linha de base.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .models import EventoUso, NivelRisco

#: Velocidade (px/s) a partir da qual o sinal satura em 1.0.
VELOCIDADE_SATURACAO_PX_S = 2200.0

#: Permanência contínua (s) a partir da qual o sinal de permanência satura.
PERMANENCIA_SATURACAO_S = 900.0  # 15 min

#: Reentradas por hora a partir das quais o sinal satura.
REENTRADAS_SATURACAO = 8.0

#: Intervalo (s) sem amostras que encerra a sessão contínua.
INTERVALO_FIM_SESSAO_S = 120.0

#: Constante de tempo (s) da média móvel exponencial.
TAU_SUAVIZACAO_S = 150.0

#: Pesos dos sinais; somam 1.0.
PESOS = {
    "velocidade": 0.22,
    "passividade": 0.28,
    "monotonia": 0.15,
    "permanencia": 0.25,
    "reentradas": 0.10,
}

#: Horas consideradas madrugada, com multiplicador de agravamento.
HORAS_MADRUGADA = frozenset({0, 1, 2, 3, 4, 5})
MULTIPLICADOR_MADRUGADA = 1.15

#: Limiares das faixas de risco.
LIMIAR_ATENCAO = 25.0
LIMIAR_ALERTA = 50.0
LIMIAR_CRITICO = 75.0

#: Valor para o qual o IVD converge durante uso saudável.
LINHA_DE_BASE = 5.0


def _saturar(valor: float, teto: float) -> float:
    """Normaliza ``valor`` para 0-1 saturando em ``teto``."""
    if teto <= 0:
        return 0.0
    return max(0.0, min(1.0, valor / teto))


def nivel_para(ivd: float) -> NivelRisco:
    """Traduz o escalar do IVD em faixa de risco."""
    if ivd >= LIMIAR_CRITICO:
        return NivelRisco.CRITICO
    if ivd >= LIMIAR_ALERTA:
        return NivelRisco.ALERTA
    if ivd >= LIMIAR_ATENCAO:
        return NivelRisco.ATENCAO
    return NivelRisco.CALMO


@dataclass
class LeituraIVD:
    """Resultado de uma ingestão de evento."""

    valor: float
    nivel: NivelRisco
    instantaneo: float
    permanencia_s: float
    sinais: dict[str, float]


@dataclass
class CalculadoraIVD:
    """Mantém o estado do IVD de um usuário.

    A instância é serializável (todos os campos são primitivos ou listas de
    primitivos), o que permite persistir e retomar entre execuções do app.
    """

    valor: float = LINHA_DE_BASE
    permanencia_s: float = 0.0
    _ultimo_ts: float | None = None
    _aberturas: list[float] = field(default_factory=list)

    # ------------------------------------------------------------------ API

    @property
    def nivel(self) -> NivelRisco:
        return nivel_para(self.valor)

    def reentradas_ultima_hora(self, agora: float) -> int:
        return sum(1 for ts in self._aberturas if agora - ts <= 3600.0)

    def registrar(self, evento: EventoUso) -> LeituraIVD:
        """Ingere uma amostra de uso e devolve a leitura atualizada."""
        self._atualizar_sessao(evento)

        if evento.categoria.e_distracao:
            sinais = self._sinais(evento)
            instantaneo = self._instantaneo(sinais, evento)
        else:
            # Uso saudável não zera o índice de imediato: ele decai.
            sinais = {}
            instantaneo = LINHA_DE_BASE

        alfa = 1.0 - math.exp(-evento.duracao_s / TAU_SUAVIZACAO_S)
        self.valor = self.valor + alfa * (instantaneo - self.valor)
        self.valor = max(0.0, min(100.0, self.valor))

        return LeituraIVD(
            valor=self.valor,
            nivel=self.nivel,
            instantaneo=instantaneo,
            permanencia_s=self.permanencia_s,
            sinais=sinais,
        )

    # -------------------------------------------------------------- interno

    def _atualizar_sessao(self, evento: EventoUso) -> None:
        houve_intervalo = (
            self._ultimo_ts is not None
            and evento.timestamp - self._ultimo_ts > INTERVALO_FIM_SESSAO_S
        )
        if not evento.categoria.e_distracao or houve_intervalo or evento.abertura_app:
            self.permanencia_s = 0.0

        if evento.categoria.e_distracao:
            self.permanencia_s += evento.duracao_s
            if evento.abertura_app:
                self._aberturas.append(evento.timestamp)
                # Descarta aberturas fora da janela de uma hora.
                corte = evento.timestamp - 3600.0
                self._aberturas = [ts for ts in self._aberturas if ts >= corte]

        self._ultimo_ts = evento.timestamp

    def _sinais(self, evento: EventoUso) -> dict[str, float]:
        toques_por_min = evento.toques / (evento.duracao_s / 60.0)
        inversoes_por_min = evento.inversoes_direcao / (evento.duracao_s / 60.0)
        return {
            "velocidade": _saturar(evento.velocidade_scroll, VELOCIDADE_SATURACAO_PX_S),
            # 0 toques/min => 1.0; 6+ toques/min => 0.0
            "passividade": 1.0 - _saturar(toques_por_min, 6.0),
            # 0 inversões/min => 1.0; 4+ inversões/min => 0.0
            "monotonia": 1.0 - _saturar(inversoes_por_min, 4.0),
            "permanencia": _saturar(self.permanencia_s, PERMANENCIA_SATURACAO_S),
            "reentradas": _saturar(
                self.reentradas_ultima_hora(evento.timestamp), REENTRADAS_SATURACAO
            ),
        }

    def _instantaneo(self, sinais: dict[str, float], evento: EventoUso) -> float:
        bruto = sum(PESOS[nome] * valor for nome, valor in sinais.items()) * 100.0
        if evento.hora_local in HORAS_MADRUGADA:
            bruto *= MULTIPLICADOR_MADRUGADA
        return max(LINHA_DE_BASE, min(100.0, bruto))


def ivd_de_serie(eventos: list[EventoUso]) -> LeituraIVD:
    """Utilitário: calcula o IVD final de uma série de eventos.

    Útil para relatórios semanais e para reprocessar histórico offline.
    """
    calculadora = CalculadoraIVD()
    leitura = LeituraIVD(
        valor=calculadora.valor,
        nivel=calculadora.nivel,
        instantaneo=calculadora.valor,
        permanencia_s=0.0,
        sinais={},
    )
    for evento in eventos:
        leitura = calculadora.registrar(evento)
    return leitura


__all__ = ["CalculadoraIVD", "LeituraIVD", "ivd_de_serie", "nivel_para"]
