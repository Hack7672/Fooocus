# Mente Zero (ResetMind)

> Recuperar a inteligência perdida, extinguir o vício em rolagem infinita,
> reconstruir a identidade cognitiva e devolver a soberania atencional.

Este diretório contém o **documento-mestre** do produto e o **núcleo
determinístico** do motor de reset cognitivo — Python puro, sem dependências,
sem I/O e sem rede.

## Documentos

| Arquivo | Conteúdo |
| --- | --- |
| [`docs/MASTER.md`](docs/MASTER.md) | Documento-mestre: missão, fundamentos, 7 camadas, planos FREE e PRO |
| [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) | Mapa camada → módulo, contrato de dados, fórmula do IVD, privacidade |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Fases de execução, métricas e cautelas de comunicação |

## O que já roda

| Camada | Implementado |
| --- | --- |
| 1 — Detecção | Índice de Vício Digital (5 sinais, média móvel exponencial, faixas de risco) |
| 2 — Academia do Córtex | Escala ZERO: 6 tipos de exercício adaptativos, microganhos, repetição mínima; Modo Foco Profundo (45 min, multi-dispositivo no PRO) e Desafio do Texto Inútil |
| 3 — Recalibragem emocional | Termômetro (triagem lexical com encaminhamento em crise), Dia Zero, Diário da Mente Restaurada |
| 4 — Economia da atenção | Scroll Stopper, tela cinza, janela de reflexão, Banco de Minutos, Leilão de Distrações |
| 5 — Identidade | Jornada do Herói (7 capítulos), Simulador de Perda simbólico, gatilho do Eu Futuro |
| 6 — Social não tóxico | Tribos de Silêncio (12 pessoas, sem API de chat), Feed de Perguntas Maiêuticas |
| 7 — Protocolo Realidade | Missões offline rotativas, cronograma de detox sensorial, Feed Nutritivo |
| — | Matriz de direitos FREE/PRO em um único lugar; persistência completa do estado do motor; relatório semanal de saúde digital |

## Uso

```python
from mente_zero import MotorMenteZero, Plano
from mente_zero.core import CategoriaApp, EventoUso

motor = MotorMenteZero(plano=Plano.PRO, semente=42)

intervencao = motor.processar(
    EventoUso(
        timestamp=1_720_000_000.0,
        app_id="reels",
        categoria=CategoriaApp.FEED_SOCIAL,
        duracao_s=5.0,
        distancia_scroll_px=6200.0,
        toques=0,
    )
)
if intervencao.ativa:
    print(intervencao.tipo, intervencao.mensagem)

# Economia da atenção
motor.solicitar_acesso("instagram")               # gasta 1 moeda
exercicio = motor.proximo_exercicio()             # Escala ZERO
motor.responder_exercicio(exercicio, exercicio.resposta, tempo_s=12.0)
```

## Rodando

```bash
# 121 testes, ~0,6 s
python3 -m unittest discover -s mente_zero/tests -t .

# simulação de um dia de uso (manhã compulsiva, trabalho, recaída de madrugada)
python3 -m mente_zero.simulacao
python3 -m mente_zero.simulacao --pro

# protótipo navegável (stdlib pura) em http://127.0.0.1:8788
python3 -m mente_zero.webapp --pro
```

O núcleo não coleta conteúdo de tela: só geometria de gesto, categoria de app e
tempo. Ver a seção de privacidade em [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md).
