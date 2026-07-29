"""Persistência do estado do motor (roadmap, Fase 1).

Converte um :class:`MotorMenteZero` em um dicionário JSON-serializável e o
reconstrói sem perda de comportamento: o motor restaurado deve reagir aos
próximos eventos exatamente como o original reagiria. A casca decide onde
guardar o dicionário (arquivo local, keychain, banco); o núcleo só garante o
formato.

O campo ``versao`` permite migração de esquema em versões futuras.
"""

from __future__ import annotations

from .economia_atencao import (
    BancoDeMinutos,
    EstadoStopper,
    LeilaoDeDistracoes,
    ScrollStopper,
)
from .escala_zero import EscalaZero
from .ivd import CalculadoraIVD
from .models import Plano
from .motor import MotorMenteZero

VERSAO_ESQUEMA = 1


class EsquemaIncompativel(RuntimeError):
    """Levantada ao carregar um snapshot de versão desconhecida."""


def salvar(motor: MotorMenteZero) -> dict:
    """Fotografa o estado completo do motor em um dicionário JSON-serializável."""
    return {
        "versao": VERSAO_ESQUEMA,
        "plano": motor.plano.value,
        "apps_mapeados": sorted(motor.apps_mapeados),
        "semente": motor.semente,
        "dia": motor.dia,
        "intervencoes_hoje": motor.intervencoes_hoje,
        "ultimo_aviso_ts": motor._ultimo_aviso_ts,
        "ivd": {
            "valor": motor.ivd.valor,
            "permanencia_s": motor.ivd.permanencia_s,
            "ultimo_ts": motor.ivd._ultimo_ts,
            "aberturas": list(motor.ivd._aberturas),
        },
        "banco": {
            "dia": motor.banco.dia,
            "saldo": motor.banco.saldo,
            "conquistadas_hoje": motor.banco.conquistadas_hoje,
        },
        "leilao": {
            "dia": motor.leilao.dia,
            "tentativas": dict(motor.leilao.tentativas),
        },
        "escala": {
            "nivel": motor.escala.nivel,
            "dia": motor.escala.dia,
            "entregues_hoje": motor.escala.entregues_hoje,
            "acertos_rapidos_seguidos": motor.escala.acertos_rapidos_seguidos,
            "contador": motor.escala._contador,
            "historico": list(motor.escala._historico),
        },
        "stopper": {
            "estado": motor.stopper.estado.value,
            "passivo_acumulado_s": motor.stopper.passivo_acumulado_s,
            "passivo_total_sessao_s": motor.stopper.passivo_total_sessao_s,
            "congelado_em": motor.stopper._congelado_em,
            "cinza_ate": motor.stopper._cinza_ate,
            "reflexao_emitida": motor.stopper._reflexao_emitida,
            "ultimo_ts": motor.stopper._ultimo_ts,
        },
    }


def carregar(dados: dict) -> MotorMenteZero:
    """Reconstrói um motor a partir de um snapshot de :func:`salvar`."""
    versao = dados.get("versao")
    if versao != VERSAO_ESQUEMA:
        raise EsquemaIncompativel(f"versão de snapshot desconhecida: {versao!r}")

    plano = Plano(dados["plano"])
    apps = frozenset(dados["apps_mapeados"])
    motor = MotorMenteZero(plano=plano, apps_mapeados=apps, semente=dados["semente"])

    motor.dia = dados["dia"]
    motor.intervencoes_hoje = dados["intervencoes_hoje"]
    motor._ultimo_aviso_ts = dados["ultimo_aviso_ts"]

    ivd = dados["ivd"]
    motor.ivd = CalculadoraIVD(
        valor=ivd["valor"],
        permanencia_s=ivd["permanencia_s"],
        _ultimo_ts=ivd["ultimo_ts"],
        _aberturas=list(ivd["aberturas"]),
    )

    banco = dados["banco"]
    motor.banco = BancoDeMinutos(
        plano=plano,
        dia=banco["dia"],
        saldo=banco["saldo"],
        conquistadas_hoje=banco["conquistadas_hoje"],
    )

    leilao = dados["leilao"]
    motor.leilao = LeilaoDeDistracoes(
        plano=plano,
        dia=leilao["dia"],
        tentativas=dict(leilao["tentativas"]),
    )

    escala = dados["escala"]
    motor.escala = EscalaZero(
        plano=plano,
        nivel=escala["nivel"],
        semente=dados["semente"],
        dia=escala["dia"],
        entregues_hoje=escala["entregues_hoje"],
        acertos_rapidos_seguidos=escala["acertos_rapidos_seguidos"],
        _contador=escala["contador"],
        _historico=list(escala["historico"]),
    )

    stopper = dados["stopper"]
    motor.stopper = ScrollStopper(
        plano=plano,
        apps_mapeados=apps,
        estado=EstadoStopper(stopper["estado"]),
        passivo_acumulado_s=stopper["passivo_acumulado_s"],
        passivo_total_sessao_s=stopper["passivo_total_sessao_s"],
        _congelado_em=stopper["congelado_em"],
        _cinza_ate=stopper["cinza_ate"],
        _reflexao_emitida=stopper["reflexao_emitida"],
        _ultimo_ts=stopper["ultimo_ts"],
    )

    return motor


__all__ = ["EsquemaIncompativel", "carregar", "salvar", "VERSAO_ESQUEMA"]
