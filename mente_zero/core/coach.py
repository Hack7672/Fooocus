"""IA Coach de atenção (Fase 3, PRO) — antecipação de recaídas.

O coach aprende o perfil temporal de risco do próprio usuário: mantém uma média
móvel do IVD por janela (dia da semana × hora) e, quando a próxima hora tem
histórico de risco alto e o momento atual ainda está calmo, emite uma
intervenção *preventiva* — antes da recaída, não depois dela.

Tudo roda no dispositivo, sobre a série do próprio usuário; nada é enviado a
servidor. É deliberadamente um modelo de estatística simples e auditável: a
versão com aprendizado mais rico (Fase 3) substitui o interior mantendo o mesmo
contrato.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Intervencao, Plano, TipoIntervencao
from .planos import direitos
from .recalibragem import RecursoExclusivoPro

#: Amostras mínimas numa janela antes de o coach confiar na previsão.
MINIMO_AMOSTRAS = 5

#: Fator da média móvel exponencial por janela.
ALFA = 0.3

#: IVD previsto a partir do qual a janela conta como "de risco".
LIMIAR_RISCO = 50.0

#: O aviso preventivo só sai se o momento atual ainda estiver abaixo disto.
LIMIAR_CALMO_ATUAL = 35.0

HORAS_POR_DIA = 24
DIAS_POR_SEMANA = 7


def _chave(dia_semana: int, hora: int) -> str:
    # str para que o estado seja serializável em JSON sem conversão.
    return f"{dia_semana}-{hora}"


def _validar(dia_semana: int, hora: int) -> None:
    if not 0 <= dia_semana < DIAS_POR_SEMANA:
        raise ValueError("dia_semana deve estar entre 0 (segunda) e 6 (domingo)")
    if not 0 <= hora < HORAS_POR_DIA:
        raise ValueError("hora deve estar entre 0 e 23")


@dataclass(frozen=True)
class JanelaDeRisco:
    dia_semana: int
    hora: int
    ivd_previsto: float
    amostras: int


@dataclass
class CoachAtencao:
    """Perfil temporal de risco de um usuário (recurso PRO)."""

    plano: Plano = Plano.FREE
    medias: dict[str, float] = field(default_factory=dict)
    contagens: dict[str, int] = field(default_factory=dict)

    # ------------------------------------------------------------------ API

    def _exigir_pro(self) -> None:
        if not direitos(self.plano).coach_ia:
            raise RecursoExclusivoPro("o IA Coach de atenção faz parte do ResetMind Pro")

    def registrar_leitura(self, dia_semana: int, hora: int, ivd: float) -> None:
        """Alimenta o perfil com uma leitura de IVD (chamado a cada ~5 min).

        O registro funciona em qualquer plano — assim o histórico já existe
        quando o usuário migra para o PRO; só a *previsão* é exclusiva.
        """
        _validar(dia_semana, hora)
        chave = _chave(dia_semana, hora)
        atual = self.medias.get(chave)
        self.medias[chave] = ivd if atual is None else atual + ALFA * (ivd - atual)
        self.contagens[chave] = self.contagens.get(chave, 0) + 1

    def risco_previsto(self, dia_semana: int, hora: int) -> float | None:
        """IVD esperado na janela, ou ``None`` sem histórico suficiente."""
        self._exigir_pro()
        _validar(dia_semana, hora)
        chave = _chave(dia_semana, hora)
        if self.contagens.get(chave, 0) < MINIMO_AMOSTRAS:
            return None
        return self.medias[chave]

    def janelas_de_risco(self, dia_semana: int) -> tuple[JanelaDeRisco, ...]:
        """Horas do dia com histórico de risco, ordenadas da pior para a melhor."""
        self._exigir_pro()
        janelas = []
        for hora in range(HORAS_POR_DIA):
            chave = _chave(dia_semana, hora)
            if self.contagens.get(chave, 0) >= MINIMO_AMOSTRAS and self.medias[chave] >= LIMIAR_RISCO:
                janelas.append(
                    JanelaDeRisco(dia_semana, hora, self.medias[chave], self.contagens[chave])
                )
        return tuple(sorted(janelas, key=lambda j: -j.ivd_previsto))

    def antecipar(self, dia_semana: int, hora: int, ivd_atual: float) -> Intervencao | None:
        """Aviso preventivo quando a *próxima* hora costuma ser de recaída.

        Só fala quando o presente ainda está calmo: alertar no meio da recaída
        é papel do motor; o coach existe para chegar antes.
        """
        self._exigir_pro()
        _validar(dia_semana, hora)
        if ivd_atual >= LIMIAR_CALMO_ATUAL:
            return None
        proxima_hora = (hora + 1) % HORAS_POR_DIA
        proximo_dia = dia_semana if proxima_hora > hora else (dia_semana + 1) % DIAS_POR_SEMANA
        previsto = None
        chave = _chave(proximo_dia, proxima_hora)
        if self.contagens.get(chave, 0) >= MINIMO_AMOSTRAS:
            previsto = self.medias[chave]
        if previsto is None or previsto < LIMIAR_RISCO:
            return None
        return Intervencao(
            TipoIntervencao.ALERTA_SUAVE,
            mensagem=(
                f"Nas últimas semanas, este horário ({proxima_hora:02d}h) costuma "
                "ser onde a rolagem toma o seu dia. Que tal já abrir o livro, ou "
                "agendar uma sessão de Foco Profundo agora, antes que a maré suba?"
            ),
            payload={
                "preventiva": True,
                "hora_de_risco": proxima_hora,
                "ivd_previsto": previsto,
            },
        )


__all__ = [
    "ALFA",
    "CoachAtencao",
    "JanelaDeRisco",
    "LIMIAR_CALMO_ATUAL",
    "LIMIAR_RISCO",
    "MINIMO_AMOSTRAS",
]
