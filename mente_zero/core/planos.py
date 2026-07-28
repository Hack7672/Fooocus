"""Matriz de direitos por plano (seção 3 do documento-mestre).

Um único lugar decide o que FREE e PRO liberam. Toda checagem de recurso no
motor passa por :func:`direitos`, para que nenhuma regra comercial fique
espalhada pelas camadas.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import TIPOS_BASICOS, Plano, TipoExercicio


@dataclass(frozen=True)
class Direitos:
    """Direitos efetivos de um plano."""

    moedas_diarias: int
    exercicios_diarios: int | None          # None = ilimitado
    tipos_exercicio: tuple[TipoExercicio, ...]
    crescimento_leilao: float               # base do preço exponencial
    neurofeedback_optico: bool
    coach_ia: bool
    foco_profundo_multidispositivo: bool
    tribos_simultaneas: int | None
    perguntas_maieuticas_semana: int | None
    dias_zero_por_mes: int | None
    avatar_personalizado: bool
    diario_mente_restaurada: bool
    mentoria_reversa: bool
    desafio_texto_inutil: bool
    creditos_bonus_missoes: bool


_MATRIZ: dict[Plano, Direitos] = {
    Plano.FREE: Direitos(
        moedas_diarias=4,
        exercicios_diarios=1,
        tipos_exercicio=TIPOS_BASICOS,
        crescimento_leilao=1.6,
        neurofeedback_optico=False,
        coach_ia=False,
        foco_profundo_multidispositivo=False,
        tribos_simultaneas=1,
        perguntas_maieuticas_semana=3,
        dias_zero_por_mes=1,
        avatar_personalizado=False,
        diario_mente_restaurada=False,
        mentoria_reversa=False,
        desafio_texto_inutil=False,
        creditos_bonus_missoes=False,
    ),
    Plano.PRO: Direitos(
        moedas_diarias=6,
        exercicios_diarios=None,
        tipos_exercicio=tuple(TipoExercicio),
        crescimento_leilao=2.2,
        neurofeedback_optico=True,
        coach_ia=True,
        foco_profundo_multidispositivo=True,
        tribos_simultaneas=None,
        perguntas_maieuticas_semana=None,
        dias_zero_por_mes=None,
        avatar_personalizado=True,
        diario_mente_restaurada=True,
        mentoria_reversa=True,
        desafio_texto_inutil=True,
        creditos_bonus_missoes=True,
    ),
}


def direitos(plano: Plano) -> Direitos:
    """Devolve os direitos do plano informado."""
    return _MATRIZ[plano]


__all__ = ["Direitos", "direitos"]
