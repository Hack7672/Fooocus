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
from .foco import DesafioTextoInutil, FocoProfundo
from .ivd import CalculadoraIVD, LeituraIVD, ivd_de_serie, nivel_para
from .jornada import JornadaDoHeroi, SimulacaoPerda, simular_perda
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
from .persistencia import carregar, salvar
from .planos import Direitos, direitos
from .protocolo_realidade import FeedNutritivo, ProtocoloRealidade, cronograma_detox
from .relatorio import RelatorioSemanal, ResumoDiario, gerar_relatorio
from .recalibragem import (
    DiarioMenteRestaurada,
    DiaZero,
    TermometroEmocional,
)
from .social import FeedMaieutico, GerenciadorTribos, TriboDeSilencio

__all__ = [
    "BancoDeMinutos",
    "CalculadoraIVD",
    "CategoriaApp",
    "DesafioTextoInutil",
    "DiaZero",
    "DiarioMenteRestaurada",
    "Direitos",
    "EscalaZero",
    "FeedMaieutico",
    "FeedNutritivo",
    "FocoProfundo",
    "GerenciadorTribos",
    "JornadaDoHeroi",
    "ProtocoloRealidade",
    "RelatorioSemanal",
    "ResumoDiario",
    "SimulacaoPerda",
    "TermometroEmocional",
    "TriboDeSilencio",
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
    "carregar",
    "cronograma_detox",
    "direitos",
    "gerar_relatorio",
    "ivd_de_serie",
    "nivel_para",
    "salvar",
    "simular_perda",
]
