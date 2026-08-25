# Roadmap de execução — Mente Zero

O documento-mestre descreve o produto inteiro; este roadmap ordena a construção
por **dependência técnica e risco de plataforma**, não por apelo narrativo.

## Fase 0 — Núcleo (concluída)

Motor determinístico do IVD, Scroll Stopper, Banco de Minutos, Leilão de
Distrações, Escala ZERO e matriz de planos. Também já implementadas as regras
puras das camadas 3 (termômetro lexical, Dia Zero, Diário), 5 (Jornada do
Herói, Simulador de Perda), 6 (Tribos de Silêncio, Feed Maiêutico) e 7
(missões, detox, Feed Nutritivo), além da persistência do estado do motor —
100 testes no total. O que resta nas fases abaixo é integração de plataforma,
IA e backend.

## Fase 1 — Casca móvel mínima (o produto que já muda comportamento)

1. **Agente de eventos**
   - Android: `AccessibilityService` + `UsageStatsManager` → `EventoUso`.
   - iOS: `DeviceActivityMonitor` + `ManagedSettings` (Screen Time API). O iOS
     **não** permite ler gesto de scroll de apps de terceiros: o IVD roda em
     modo degradado (permanência + reentradas, sem velocidade/passividade).
     Isso precisa estar assumido no design, não descoberto na submissão.
2. **Camada de sobreposição:** congelamento, tela cinza de 15 s, micro-pausa com
   respiração guiada e som de natureza.
3. **Escala ZERO na tela:** os seis tipos já gerados pelo núcleo.
4. **Relatório semanal de saúde digital** (FREE).
5. **Persistência local** do estado do motor (todos os objetos são serializáveis).

Risco principal: políticas de loja sobre acessibilidade e bloqueio de apps.
Mitigar cedo, com build de revisão antes de investir nas camadas 5-7.

## Fase 2 — Economia da atenção e retenção

- Banco de Minutos e Leilão na interface, com histórico visível.
- Modo Foco Profundo (45 min) e Dia Zero mensal.
- Jornada do Herói Cognitivo: capítulos desbloqueados por semanas de foco.
- Avatar do Eu Futuro (mensagens genéricas no FREE).

## Fase 3 — PRO e inteligência

- IA Coach de atenção: **primeira versão implementada** (`core/coach.py`) —
  perfil temporal de risco por dia × hora com previsão e aviso preventivo;
  a evolução da fase troca a estatística simples por modelo aprendido,
  mantendo o contrato.
- Escala ZERO gerada por IA generativa, com validação automática de gabarito
  antes de mostrar ao usuário — item sem resposta verificável não é publicado.
- Neurofeedback óptico (consentimento explícito, processamento local).
- Diário da Mente Restaurada, criptografado no dispositivo.
- Avatar do Eu Futuro personalizado.

## Fase 4 — Social não tóxico

- Tribos de Silêncio (12 pessoas, uma reflexão semanal, sem presença online).
- Feed de Perguntas Maiêuticas com "responda antes de ler".
- Mentoria Reversa Intergeracional, com verificação de identidade e política de
  proteção — é o item de maior risco de segurança do produto e não deve entrar
  antes de moderação e denúncia funcionando.

## Fase 5 — Protocolo Realidade

- Missões offline geolocalizadas e detox sensorial programado.
- Feed Nutritivo com curadoria e exigência de reflexão.

## Métricas que provam a missão

Métricas de vaidade (DAU, tempo no app) são explicitamente **anti-metas**: o
sucesso do Mente Zero é o usuário abrir o app menos.

| Métrica | Direção desejada |
| --- | --- |
| IVD médio semanal | ↓ |
| Minutos de tela passiva por dia | ↓ |
| Sessões de Foco Profundo concluídas | ↑ |
| Nível médio na Escala ZERO | ↑ |
| Congelamentos que viram desafio aceito | ↑ |
| Tempo total dentro do Mente Zero | ↓ (anti-meta declarada) |

## Cautelas de comunicação

O produto promete restauração cognitiva; a evidência científica sobre
transferência de treino cognitivo para "QI" é limitada e contestada. A
comunicação deve falar em **atenção sustentada, tempo de foco e comportamento
digital** — que são medíveis pelo próprio app — e reservar qualquer alegação de
ganho de QI para depois de estudo controlado. Isso não é timidez de marketing: é
o que separa o Mente Zero dos apps de "treino cerebral" já multados por
publicidade enganosa.
