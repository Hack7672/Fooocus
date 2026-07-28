"""Núcleo determinístico do Mente Zero (ResetMind).

Sem dependências externas e sem I/O: o pacote pode ser embarcado em um backend,
exposto por API para o app móvel ou reimplementado em Kotlin/Swift usando os
testes como especificação executável.
"""

from .economia_atencao import (
    BancoDeMinutos,
    EstadoStopper,
    LeilaoDeDistracoes,
    SaldoInsuficiente,
    ScrollStopper,
)
from .escala_zero import (
    EscalaZero,
    Exercicio,
    LimiteDiarioAtingido,
    Resultado,
    TipoIndisponivel,
)
from .ivd import CalculadoraIVD, LeituraIVD, ivd_de_serie, nivel_para
from .models import (
    CategoriaApp,
    EventoUso,
    Intervencao,
    NivelRisco,
    Plano,
    TipoExercicio,
    TipoIntervencao,
)
from .motor import MotorMenteZero, Resumo
from .planos import Direitos, direitos

__all__ = [
    "BancoDeMinutos",
    "CalculadoraIVD",
    "CategoriaApp",
    "Direitos",
    "EscalaZero",
    "EstadoStopper",
    "EventoUso",
    "Exercicio",
    "Intervencao",
    "LeilaoDeDistracoes",
    "LeituraIVD",
    "LimiteDiarioAtingido",
    "MotorMenteZero",
    "NivelRisco",
    "Plano",
    "Resultado",
    "Resumo",
    "SaldoInsuficiente",
    "ScrollStopper",
    "TipoExercicio",
    "TipoIndisponivel",
    "TipoIntervencao",
    "direitos",
    "ivd_de_serie",
    "nivel_para",
]
