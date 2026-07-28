"""Simulação de um dia de uso — demonstração executável do núcleo.

    python3 -m mente_zero.simulacao          # plano FREE
    python3 -m mente_zero.simulacao --pro    # plano PRO

Gera uma trilha sintética de eventos (manhã compulsiva, trabalho concentrado,
recaída noturna) e imprime as intervenções que o motor decidiria emitir.
"""

from __future__ import annotations

import argparse
import random

from .core import CategoriaApp, EventoUso, MotorMenteZero, Plano, TipoIntervencao

HORA = 3600.0


def _bloco(rng, inicio, minutos, categoria, app_id, *, compulsivo, hora_local):
    """Gera amostras de 5 s cobrindo ``minutos`` de uso contínuo."""
    eventos = []
    for i in range(int(minutos * 12)):
        if compulsivo:
            scroll = rng.uniform(4000, 9000)
            toques = 1 if rng.random() < 0.05 else 0
            inversoes = 1 if rng.random() < 0.05 else 0
        else:
            scroll = rng.uniform(0, 400)
            toques = rng.randint(1, 3)
            inversoes = rng.randint(0, 2)
        eventos.append(
            EventoUso(
                timestamp=inicio + i * 5.0,
                app_id=app_id,
                categoria=categoria,
                duracao_s=5.0,
                distancia_scroll_px=scroll,
                toques=toques,
                inversoes_direcao=inversoes,
                abertura_app=(i == 0),
                hora_local=hora_local,
            )
        )
    return eventos


def trilha_de_um_dia(semente: int = 2024) -> list[EventoUso]:
    rng = random.Random(semente)
    eventos: list[EventoUso] = []
    # 07h — primeira rolagem do dia, ainda na cama.
    eventos += _bloco(rng, 7 * HORA, 25, CategoriaApp.FEED_SOCIAL, "reels", compulsivo=True, hora_local=7)
    # 09h — trabalho concentrado.
    eventos += _bloco(rng, 9 * HORA, 50, CategoriaApp.PRODUTIVIDADE, "editor", compulsivo=False, hora_local=9)
    # 13h — almoço com feed.
    eventos += _bloco(rng, 13 * HORA, 20, CategoriaApp.FEED_SOCIAL, "reels", compulsivo=True, hora_local=13)
    # 16h — leitura longa.
    eventos += _bloco(rng, 16 * HORA, 30, CategoriaApp.LEITURA, "ebook", compulsivo=False, hora_local=16)
    # 01h — recaída de madrugada.
    eventos += _bloco(rng, 25 * HORA, 40, CategoriaApp.FEED_SOCIAL, "shorts", compulsivo=True, hora_local=1)
    return eventos


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulação de um dia no Mente Zero")
    parser.add_argument("--pro", action="store_true", help="usa o plano PRO")
    parser.add_argument("--semente", type=int, default=2024)
    args = parser.parse_args()

    plano = Plano.PRO if args.pro else Plano.FREE
    motor = MotorMenteZero(plano=plano, semente=args.semente)

    print(f"MENTE ZERO — simulação de um dia (plano {plano.value.upper()})\n")
    contagem: dict[TipoIntervencao, int] = {}

    for evento in trilha_de_um_dia(args.semente):
        intervencao = motor.processar(evento)
        if not intervencao.ativa:
            continue
        contagem[intervencao.tipo] = contagem.get(intervencao.tipo, 0) + 1
        hora = int(evento.timestamp // 3600) % 24
        minuto = int(evento.timestamp % 3600) // 60
        print(
            f"{hora:02d}:{minuto:02d} | IVD {motor.ivd.valor:5.1f} "
            f"({motor.ivd.nivel.value:8s}) | {intervencao.tipo.value:22s} "
            f"| {intervencao.mensagem[:56]}"
        )
        if intervencao.tipo is TipoIntervencao.SCROLL_STOPPER:
            # O usuário simulado aceita o desafio em 1 de cada 3 congelamentos.
            motor.stopper.responder(aceitou_desafio=(contagem[intervencao.tipo] % 3 == 0))

    resumo = motor.resumo()
    # A trilha atravessa a meia-noite (recaída de madrugada), então os campos
    # diários do resumo já refletem o segundo dia; a contagem abaixo é total.
    print("\n--- resumo ---")
    print(f"IVD final ................... {resumo.ivd:.1f} ({resumo.nivel.value})")
    print(f"Moedas restantes ............ {resumo.moedas}")
    print(f"Nível na Escala ZERO ........ {resumo.nivel_escala}")
    print(f"Exercícios no dia corrente .. {resumo.exercicios_hoje}")
    print(f"Intervenções no dia corrente  {resumo.intervencoes_hoje}")
    print("Intervenções na trilha inteira:")
    for tipo, quantidade in sorted(contagem.items(), key=lambda item: -item[1]):
        print(f"  - {tipo.value:22s} {quantidade}")


if __name__ == "__main__":
    main()
