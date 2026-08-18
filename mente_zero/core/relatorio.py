"""Relatório semanal de saúde digital (recurso FREE, Fase 1 do roadmap).

Consolida os resumos diários do motor em um relatório com tendência sobre a
semana anterior. Segue a régua de métricas do ROADMAP.md: as direções desejadas
são IVD para baixo, tela passiva para baixo, foco e exercícios para cima — e o
tempo dentro do próprio app é anti-meta, então o relatório celebra ausência,
nunca engajamento.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ivd import nivel_para


@dataclass(frozen=True)
class ResumoDiario:
    """Uma linha por dia, extraída de ``MotorMenteZero.resumo()`` ao fim do dia."""

    dia: int
    ivd_medio: float
    minutos_passivos: float
    exercicios: int
    intervencoes: int
    sessoes_foco: int = 0


@dataclass(frozen=True)
class RelatorioSemanal:
    dias_cobertos: int
    ivd_medio: float
    faixa: str
    minutos_passivos_por_dia: float
    exercicios: int
    sessoes_foco: int
    intervencoes: int
    variacao_ivd: float | None            # delta vs semana anterior; negativo = melhora
    variacao_passivo_min: float | None
    destaque: str
    recomendacao: str


def _media(valores: list[float]) -> float:
    return sum(valores) / len(valores) if valores else 0.0


def gerar_relatorio(
    semana: list[ResumoDiario],
    semana_anterior: list[ResumoDiario] | None = None,
) -> RelatorioSemanal:
    """Consolida uma semana (1 a 7 dias) e compara com a anterior, se houver."""
    if not 1 <= len(semana) <= 7:
        raise ValueError("uma semana tem de 1 a 7 resumos diários")

    ivd_medio = _media([d.ivd_medio for d in semana])
    passivo_dia = _media([d.minutos_passivos for d in semana])
    exercicios = sum(d.exercicios for d in semana)
    sessoes_foco = sum(d.sessoes_foco for d in semana)
    intervencoes = sum(d.intervencoes for d in semana)

    variacao_ivd = variacao_passivo = None
    if semana_anterior:
        variacao_ivd = ivd_medio - _media([d.ivd_medio for d in semana_anterior])
        variacao_passivo = passivo_dia - _media(
            [d.minutos_passivos for d in semana_anterior]
        )

    destaque = _destaque(ivd_medio, passivo_dia, variacao_ivd, variacao_passivo)
    recomendacao = _recomendacao(ivd_medio, passivo_dia, exercicios, sessoes_foco)

    return RelatorioSemanal(
        dias_cobertos=len(semana),
        ivd_medio=ivd_medio,
        faixa=nivel_para(ivd_medio).value,
        minutos_passivos_por_dia=passivo_dia,
        exercicios=exercicios,
        sessoes_foco=sessoes_foco,
        intervencoes=intervencoes,
        variacao_ivd=variacao_ivd,
        variacao_passivo_min=variacao_passivo,
        destaque=destaque,
        recomendacao=recomendacao,
    )


def _destaque(
    ivd: float,
    passivo: float,
    variacao_ivd: float | None,
    variacao_passivo: float | None,
) -> str:
    if variacao_ivd is not None and variacao_ivd <= -5.0:
        return (
            f"Seu IVD caiu {abs(variacao_ivd):.0f} pontos em relação à semana "
            "passada. A atenção está voltando para casa."
        )
    if variacao_passivo is not None and variacao_passivo <= -15.0:
        return (
            f"Você rolou {abs(variacao_passivo):.0f} minutos a menos por dia. "
            "Esse tempo agora é seu."
        )
    if variacao_ivd is not None and variacao_ivd >= 5.0:
        return (
            f"O IVD subiu {variacao_ivd:.0f} pontos esta semana. Sem culpa — "
            "com plano: escolha um gatilho e proteja-o."
        )
    if ivd < 25.0:
        return "Semana em faixa calma. O padrão está estável e sob seu comando."
    return "Semana registrada. Os números abaixo mostram onde a rolagem mora."


def _recomendacao(ivd: float, passivo: float, exercicios: int, sessoes_foco: int) -> str:
    if ivd >= 50.0:
        return (
            "Prioridade: um Dia Zero neste fim de semana e o Scroll Stopper "
            "ativo nos apps que mais aparecem no seu histórico."
        )
    if passivo >= 90.0:
        return (
            "Troque 15 dos minutos passivos diários por uma sessão curta de "
            "leitura — o Feed Nutritivo é um bom começo."
        )
    if sessoes_foco == 0:
        return "Experimente uma sessão de Foco Profundo de 45 minutos esta semana."
    if exercicios < 3:
        return "Três exercícios da Escala ZERO nesta semana mantêm a progressão."
    return "Mantenha o ritmo: consistência vale mais do que intensidade."


__all__ = ["RelatorioSemanal", "ResumoDiario", "gerar_relatorio"]
