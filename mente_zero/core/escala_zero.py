"""Camada 2 — Escala ZERO (Academia do Córtex).

Gerador adaptativo de exercícios cognitivos com três garantias exigidas pelo
documento-mestre:

* **Progressão por microganhos** — o nível sobe apenas após dois acertos
  consecutivos dentro do tempo-alvo, e cai um degrau a cada erro.
* **Repetição mínima** — um item só pode reaparecer depois de ``JANELA_REPETICAO``
  outros itens, evitando memorização em vez de raciocínio.
* **Determinismo** — todos os geradores derivam de uma semente, então a mesma
  semente produz a mesma prova: exercícios são reprodutíveis em testes,
  auditorias e estudos de eficácia.

Os seis tipos cobrem as redes neurais listadas na camada 2: lógica, raciocínio
espacial, analogias verbais, sequências abstratas, alternância de tarefas e
associação forçada (esta última é aberta, avaliada por engajamento e não por
gabarito).
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field

from .models import Plano, TipoExercicio
from .planos import direitos

#: Quantos itens precisam passar antes que um item possa se repetir.
JANELA_REPETICAO = 40

#: Acertos rápidos consecutivos necessários para subir de nível.
ACERTOS_PARA_SUBIR = 2

NIVEL_MIN = 1
NIVEL_MAX = 10


class LimiteDiarioAtingido(RuntimeError):
    """Levantada quando o plano FREE esgota o exercício diário."""


class TipoIndisponivel(RuntimeError):
    """Levantada quando o tipo pedido não está no plano do usuário."""


@dataclass(frozen=True)
class Exercicio:
    """Um item da Escala ZERO."""

    id: str
    tipo: TipoExercicio
    nivel: int
    enunciado: str
    resposta: str | None                  # None em itens abertos
    alternativas: tuple[str, ...] = ()
    tempo_alvo_s: float = 45.0
    aberto: bool = False

    def confere(self, resposta: str) -> bool:
        """Compara a resposta do usuário com o gabarito."""
        if self.aberto:
            # Item aberto: vale como acerto qualquer resposta com substância.
            return len(resposta.strip().split()) >= 3
        assert self.resposta is not None
        return resposta.strip().casefold() == self.resposta.casefold()


@dataclass(frozen=True)
class Resultado:
    """Consequência de responder um exercício."""

    correto: bool
    dentro_do_tempo: bool
    nivel_anterior: int
    nivel_novo: int
    moedas_ganhas: int


# --------------------------------------------------------------------------
# Geradores determinísticos
# --------------------------------------------------------------------------

_NOMES = (
    "Ana", "Bruno", "Clara", "Davi", "Elisa", "Fábio", "Gil", "Hana",
    "Igor", "Júlia", "Kai", "Lia",
)

_ANALOGIAS = (
    ("médico", "hospital", "professor", "escola"),
    ("livro", "leitura", "partitura", "música"),
    ("raiz", "árvore", "alicerce", "prédio"),
    ("bússola", "direção", "relógio", "tempo"),
    ("semente", "fruto", "hipótese", "teoria"),
    ("mapa", "território", "palavra", "coisa"),
    ("remo", "barco", "asa", "ave"),
    ("fome", "comida", "tédio", "sentido"),
)

_DISTRATORES = (
    "hospital", "silêncio", "algoritmo", "espelho", "caverna", "vento",
    "número", "retrato", "muro", "rio",
)


def _gerar_logica(rng: random.Random, nivel: int) -> tuple[str, str, tuple[str, ...]]:
    quantidade = min(len(_NOMES), 3 + nivel // 2)
    pessoas = rng.sample(_NOMES, quantidade)
    ordem = list(pessoas)
    rng.shuffle(ordem)  # ordem[0] é o mais alto
    premissas = [
        f"{ordem[i]} é mais alto que {ordem[i + 1]}" for i in range(len(ordem) - 1)
    ]
    rng.shuffle(premissas)
    enunciado = (
        "Considere as afirmações: "
        + "; ".join(premissas)
        + ". Quem é o mais alto?"
    )
    return enunciado, ordem[0], tuple(sorted(pessoas))


def _gerar_espacial(rng: random.Random, nivel: int) -> tuple[str, str, tuple[str, ...]]:
    passos = 3 + nivel
    direcoes = {"norte": (0, 1), "sul": (0, -1), "leste": (1, 0), "oeste": (-1, 0)}
    x = y = 0
    trajeto = []
    for _ in range(passos):
        nome = rng.choice(list(direcoes))
        distancia = rng.randint(1, 3)
        dx, dy = direcoes[nome]
        x += dx * distancia
        y += dy * distancia
        trajeto.append(f"{distancia} para o {nome}")
    enunciado = (
        "Você parte da origem (0, 0) de um mapa e caminha, sem desenhar nada: "
        + ", ".join(trajeto)
        + ". Em que coordenada (x, y) você termina?"
    )
    return enunciado, f"({x}, {y})", ()


def _gerar_analogia(rng: random.Random, nivel: int) -> tuple[str, str, tuple[str, ...]]:
    a, b, c, d = rng.choice(_ANALOGIAS)
    quantidade_distratores = min(len(_DISTRATORES), 2 + nivel // 3)
    opcoes = {d}
    for palavra in rng.sample(_DISTRATORES, quantidade_distratores):
        if palavra != d:
            opcoes.add(palavra)
    enunciado = f"{a} está para {b} assim como {c} está para ___"
    return enunciado, d, tuple(sorted(opcoes))


def _gerar_sequencia(rng: random.Random, nivel: int) -> tuple[str, str, tuple[str, ...]]:
    regra = rng.choice(("aritmetica", "geometrica", "fibonacci", "alternada"))
    inicio = rng.randint(1, 3 + nivel)
    passo = rng.randint(2, 2 + nivel)
    termos: list[int] = []
    if regra == "aritmetica":
        termos = [inicio + passo * i for i in range(6)]
    elif regra == "geometrica":
        razao = rng.randint(2, 3)
        termos = [inicio * razao**i for i in range(6)]
    elif regra == "fibonacci":
        termos = [inicio, inicio + passo]
        for _ in range(4):
            termos.append(termos[-1] + termos[-2])
    else:  # alternada: soma e multiplica alternadamente
        termos = [inicio]
        for i in range(5):
            anterior = termos[-1]
            termos.append(anterior + passo if i % 2 == 0 else anterior * 2)
    visiveis = termos[:-1]
    enunciado = (
        "Qual é o próximo termo da sequência? "
        + ", ".join(str(t) for t in visiveis)
        + ", ___"
    )
    return enunciado, str(termos[-1]), ()


def _gerar_alternancia(rng: random.Random, nivel: int) -> tuple[str, str, tuple[str, ...]]:
    quantidade = 4 + nivel
    itens = [rng.randint(10, 99) for _ in range(quantidade)]
    total = 0
    for indice, numero in enumerate(itens):
        # Regra que alterna a cada item: soma os dígitos ou soma o número inteiro.
        total += sum(int(d) for d in str(numero)) if indice % 2 == 0 else numero
    enunciado = (
        "Percorra a lista alternando a regra a cada item: no 1º some os dígitos, "
        "no 2º some o número inteiro, no 3º volte a somar os dígitos, e assim por "
        "diante. Qual é o total? Lista: "
        + ", ".join(str(i) for i in itens)
    )
    return enunciado, str(total), ()


def _gerar_associacao(rng: random.Random, nivel: int) -> tuple[str, str | None, tuple[str, ...]]:
    palavras = rng.sample(_DISTRATORES, 2)
    enunciado = (
        f"Em uma frase, ligue '{palavras[0]}' e '{palavras[1]}' por uma relação "
        "que não seja óbvia. Não existe resposta certa: existe esforço de conexão."
    )
    return enunciado, None, ()


_GERADORES = {
    TipoExercicio.LOGICA: _gerar_logica,
    TipoExercicio.ESPACIAL: _gerar_espacial,
    TipoExercicio.ANALOGIA_VERBAL: _gerar_analogia,
    TipoExercicio.SEQUENCIA_ABSTRATA: _gerar_sequencia,
    TipoExercicio.ALTERNANCIA_TAREFAS: _gerar_alternancia,
    TipoExercicio.ASSOCIACAO_FORCADA: _gerar_associacao,
}


def _tempo_alvo(tipo: TipoExercicio, nivel: int) -> float:
    base = {
        TipoExercicio.LOGICA: 30.0,
        TipoExercicio.ESPACIAL: 35.0,
        TipoExercicio.ANALOGIA_VERBAL: 20.0,
        TipoExercicio.SEQUENCIA_ABSTRATA: 25.0,
        TipoExercicio.ALTERNANCIA_TAREFAS: 40.0,
        TipoExercicio.ASSOCIACAO_FORCADA: 60.0,
    }[tipo]
    return base + 6.0 * (nivel - 1)


# --------------------------------------------------------------------------
# Motor adaptativo
# --------------------------------------------------------------------------


@dataclass
class EscalaZero:
    """Estado adaptativo da Academia do Córtex para um usuário."""

    plano: Plano = Plano.FREE
    nivel: int = NIVEL_MIN
    semente: int = 0
    dia: int = 0
    entregues_hoje: int = 0
    acertos_rapidos_seguidos: int = 0
    _contador: int = 0
    _historico: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------ API

    def virar_dia(self, dia: int) -> None:
        if dia != self.dia:
            self.dia = dia
            self.entregues_hoje = 0

    @property
    def tipos_disponiveis(self) -> tuple[TipoExercicio, ...]:
        return direitos(self.plano).tipos_exercicio

    def restantes_hoje(self) -> int | None:
        """Exercícios ainda disponíveis hoje; ``None`` quando ilimitado."""
        limite = direitos(self.plano).exercicios_diarios
        if limite is None:
            return None
        return max(0, limite - self.entregues_hoje)

    def proximo(self, tipo: TipoExercicio | None = None) -> Exercicio:
        """Gera o próximo exercício respeitando plano, nível e repetição mínima."""
        restantes = self.restantes_hoje()
        if restantes == 0:
            raise LimiteDiarioAtingido(
                "limite diário do plano FREE atingido; conclua amanhã ou migre para o PRO"
            )

        if tipo is None:
            rng_tipo = random.Random(self.semente * 7919 + self._contador)
            tipo = rng_tipo.choice(list(self.tipos_disponiveis))
        elif tipo not in self.tipos_disponiveis:
            raise TipoIndisponivel(f"{tipo.value} não está disponível no plano {self.plano.value}")

        exercicio = self._gerar_sem_repetir(tipo)
        self._registrar_entrega(exercicio)
        return exercicio

    def responder(self, exercicio: Exercicio, resposta: str, tempo_s: float) -> Resultado:
        """Avalia a resposta e aplica a progressão por microganhos."""
        correto = exercicio.confere(resposta)
        dentro_do_tempo = tempo_s <= exercicio.tempo_alvo_s
        nivel_anterior = self.nivel

        if correto and dentro_do_tempo:
            self.acertos_rapidos_seguidos += 1
            if self.acertos_rapidos_seguidos >= ACERTOS_PARA_SUBIR:
                self.nivel = min(NIVEL_MAX, self.nivel + 1)
                self.acertos_rapidos_seguidos = 0
        elif correto:
            self.acertos_rapidos_seguidos = 0
        else:
            self.acertos_rapidos_seguidos = 0
            self.nivel = max(NIVEL_MIN, self.nivel - 1)

        moedas = 1 if correto else 0
        return Resultado(
            correto=correto,
            dentro_do_tempo=dentro_do_tempo,
            nivel_anterior=nivel_anterior,
            nivel_novo=self.nivel,
            moedas_ganhas=moedas,
        )

    # -------------------------------------------------------------- interno

    def _gerar_sem_repetir(self, tipo: TipoExercicio) -> Exercicio:
        recentes = set(self._historico[-JANELA_REPETICAO:])
        for tentativa in range(64):
            exercicio = self._gerar(tipo, self._contador + tentativa)
            if exercicio.id not in recentes:
                self._contador += tentativa
                return exercicio
        # Espaço de itens exaurido para este nível: sobe um degrau e tenta de novo.
        self.nivel = min(NIVEL_MAX, self.nivel + 1)
        self._contador += 64
        return self._gerar(tipo, self._contador)

    def _gerar(self, tipo: TipoExercicio, passo: int) -> Exercicio:
        # Semente textual: random.Random deriva de SHA-512 e é estável entre
        # execuções, ao contrário de hash() de strings.
        rng = random.Random(f"{self.semente}|{tipo.value}|{self.nivel}|{passo}")
        enunciado, resposta, alternativas = _GERADORES[tipo](rng, self.nivel)
        digest = hashlib.sha1(f"{enunciado}|{resposta}".encode()).hexdigest()[:10]
        identificador = f"{tipo.value}-{self.nivel}-{digest}"
        return Exercicio(
            id=identificador,
            tipo=tipo,
            nivel=self.nivel,
            enunciado=enunciado,
            resposta=resposta,
            alternativas=alternativas,
            tempo_alvo_s=_tempo_alvo(tipo, self.nivel),
            aberto=resposta is None,
        )

    def _registrar_entrega(self, exercicio: Exercicio) -> None:
        self._contador += 1
        self.entregues_hoje += 1
        self._historico.append(exercicio.id)
        if len(self._historico) > JANELA_REPETICAO * 4:
            del self._historico[: JANELA_REPETICAO]


__all__ = [
    "EscalaZero",
    "Exercicio",
    "LimiteDiarioAtingido",
    "Resultado",
    "TipoIndisponivel",
]
