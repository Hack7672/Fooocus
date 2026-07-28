# Arquitetura técnica — Mente Zero

## 1. Princípio estrutural

O produto tem duas metades com ciclos de vida muito diferentes:

* **Núcleo determinístico** (este repositório): regras de decisão que precisam
  ser auditáveis, testáveis e idênticas em qualquer plataforma. Sem I/O, sem
  rede, sem dependências externas.
* **Cascas dependentes de plataforma**: coleta de eventos do SO, sobreposição de
  tela, IA generativa, sincronização e social. Trocáveis, versionáveis, sujeitas
  às políticas de cada loja.

Toda regra que decide *quando intervir*, *quanto custa*, *qual exercício* e
*quem tem direito a quê* pertence ao núcleo. Nada disso pode viver em `if` de
tela.

```
         ┌──────────────── agente do SO (Android/iOS) ────────────────┐
evento → │ AccessibilityService / DeviceActivity → EventoUso          │
         └───────────────────────────┬───────────────────────────────┘
                                     ▼
                     ┌──────── MotorMenteZero ────────┐
                     │  CalculadoraIVD   (camada 1)   │
                     │  ScrollStopper    (camada 4)   │
                     │  BancoDeMinutos   (camada 4)   │
                     │  LeilaoDeDistracoes (camada 4) │
                     │  EscalaZero       (camada 2)   │
                     │  Direitos (planos FREE/PRO)    │
                     └───────────────┬────────────────┘
                                     ▼
                              Intervencao → UI (overlay, tela cinza,
                              micro-pausa, tarefa-relâmpago, Eu Futuro)
```

## 2. Mapa camada → módulo

| Camada do documento-mestre | Estado | Onde vive |
| --- | --- | --- |
| 1. Detecção e alerta (IVD, gatilhos) | **implementado** | `core/ivd.py`, `core/motor.py` |
| 1. Neurofeedback óptico (Pro) | pendente | casca nativa (câmera) + `Direitos.neurofeedback_optico` |
| 2. Escala ZERO, redes específicas | **implementado** | `core/escala_zero.py` |
| 2. Modo Foco Profundo, Texto Inútil | pendente | casca (bloqueio de apps, overlay de renderização) |
| 3. Termômetro emocional, Dia Zero, Diário | pendente | serviço de NLP + `Direitos.dias_zero_por_mes` |
| 4. Scroll Stopper, Banco de Minutos, Leilão | **implementado** | `core/economia_atencao.py` |
| 5. Jornada do Herói, Avatar do Eu Futuro | parcial | gatilho em `motor._intervencao_critica`; geração visual pendente |
| 6. Tribos, Mentoria Reversa, Feed Maiêutico | pendente | backend social + `Direitos.tribos_simultaneas` |
| 7. Missões offline, detox sensorial, Feed Nutritivo | parcial | `motor.concluir_missao_offline`; geolocalização pendente |

## 3. Contrato de dados

O agente do SO emite um `EventoUso` a cada ~5 s de tela ligada:

```python
EventoUso(
    timestamp=1_720_000_000.0,
    app_id="reels",
    categoria=CategoriaApp.FEED_SOCIAL,
    duracao_s=5.0,
    distancia_scroll_px=6200.0,
    toques=0,
    inversoes_direcao=0,
    abertura_app=False,
    hora_local=1,
)
```

Nenhum campo carrega **conteúdo** de tela: só geometria de gesto, categoria e
tempo. Essa é a fronteira de privacidade do produto — o núcleo é capaz de medir
compulsão sem nunca saber *o que* o usuário estava vendo.

A resposta é sempre um `Intervencao(tipo, mensagem, duracao_s, payload)`, que a
casca traduz em overlay, vibração, som ou bloqueio.

## 4. O Índice de Vício Digital

O IVD combina cinco sinais normalizados 0-1, com pesos que somam 1:

| Sinal | Peso | Satura em |
| --- | --- | --- |
| Passividade (rolar sem tocar) | 0,28 | 0 toque/min |
| Permanência contínua no feed | 0,25 | 15 min |
| Velocidade de scroll | 0,22 | 2200 px/s |
| Monotonia (scroll de sentido único) | 0,15 | 0 inversão/min |
| Reentradas na última hora | 0,10 | 8 reaberturas |

Aplica-se multiplicador de 1,15 entre 0h e 5h. O resultado instantâneo entra em
uma média móvel exponencial de tempo contínuo (τ = 150 s), de modo que amostras
de durações diferentes pesem proporcionalmente ao tempo que cobrem. Uso fora de
apps de distração puxa o índice para a linha de base de 5.

Faixas: `< 25` calmo · `25-49` atenção · `50-74` alerta · `≥ 75` crítico.

**Calibração:** os pesos e limiares são hipóteses iniciais, deliberadamente
explícitas em constantes de módulo. Devem ser revalidados contra dados reais
(rótulo: o usuário se arrependeu da sessão?) antes de qualquer alegação clínica.

## 5. Prioridade de intervenção

O motor emite no máximo uma intervenção por evento, nesta ordem:

1. **Camada 4 em curso** — Scroll Stopper, tela cinza, janela de reflexão.
2. **Eu Futuro** (PRO) ou **micro-pausa sensorial** (FREE) — risco crítico.
3. **Tarefa-relâmpago** — risco alerta, com item da Escala ZERO no payload.
4. **Alerta suave** — risco atenção.

Um intervalo mínimo de 5 minutos (`COOLDOWN_AVISOS_S`) separa avisos dos itens
2-4. Sem esse freio, o app viraria exatamente aquilo que combate: uma fonte de
notificações compulsivas.

## 6. Privacidade e ética (não negociável)

* Processamento **no dispositivo** por padrão; o núcleo não faz rede.
* Nenhum conteúdo de tela, texto lido ou identificação de post é coletado.
* Neurofeedback óptico exige consentimento explícito, é desligável a qualquer
  momento e nunca envia imagem para servidor — só o escalar inferido.
* O Diário da Mente Restaurada é criptografado no dispositivo.
* O Simulador de Perda Cognitiva é **simbólico** e deve ser rotulado como tal na
  interface: é metáfora motivacional, não diagnóstico ou medida de massa
  cinzenta.
* O app não vende, não perfila e não monetiza dados de atenção. Monetiza a
  restauração — a assinatura PRO —, jamais o vício.

## 7. Testes como especificação

`mente_zero/tests/` contém 60 testes que fixam o comportamento esperado de cada
regra numérica do documento-mestre (2 minutos, 15 segundos, 25 minutos, 4 e 6
moedas, 5 minutos com preço exponencial). Uma reimplementação em Kotlin ou Swift
deve reproduzir esses casos para ser considerada equivalente.

```bash
python3 -m unittest discover -s mente_zero/tests -t .
python3 -m mente_zero.simulacao --pro
```
