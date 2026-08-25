"""Programa de Desintoxicação Digital — o arco de devolução da soberania.

Para quem chega ao Mente Zero já viciado, um protocolo estruturado de saída:

1. **Triagem** — questionário de 8 itens que classifica a severidade do vício
   (leve, moderado, severo). É triagem comportamental, não diagnóstico clínico;
   o caso severo vem com a orientação explícita de considerar apoio humano.
2. **Protocolo de redução gradual** — nada de abstinência súbita: metas
   semanais de tela passiva decrescendo linearmente da linha de base até a meta
   de soberania, com mecanismos do app ativados progressivamente semana a
   semana. Duração conforme a severidade (4, 6 ou 8 semanas).
3. **Registro diário sem culpa** — o dia é cumprido ou é lapso, e o lapso é
   tratado pelo que a literatura chama de efeito de violação da abstinência:
   *um lapso não é um colapso*; a sequência recomeça sem apagar as conquistas.
4. **Marcos de soberania** — 7, 30 e 90 dias cumpridos acumulados.

Disponível integralmente no plano FREE: o caminho de saída do vício é a missão,
não um recurso premium.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

#: Questionário de triagem; cada item é respondido de 0 (nunca) a 4 (sempre).
PERGUNTAS_TRIAGEM: tuple[str, ...] = (
    "Você pega o celular sem lembrar de ter decidido pegá-lo?",
    "Você fica online mais tempo do que pretendia?",
    "Você sente inquietação ou irritação quando não pode checar as redes?",
    "Você já tentou reduzir o uso e não conseguiu?",
    "A rolagem atrapalha seu sono, trabalho ou estudo?",
    "Você usa o celular para fugir de sentimentos desconfortáveis?",
    "Você checa notificações no meio de conversas presenciais?",
    "Você sente que perde horas sem se dar conta de como passaram?",
)

RESPOSTA_MAXIMA = 4


class Severidade(str, Enum):
    LEVE = "leve"
    MODERADO = "moderado"
    SEVERO = "severo"


#: severidade -> (semanas de protocolo, fração final da linha de base)
_PARAMETROS = {
    Severidade.LEVE: (4, 0.4),
    Severidade.MODERADO: (6, 0.3),
    Severidade.SEVERO: (8, 0.25),
}

#: Piso da meta final: abaixo disto não se exige de ninguém.
PISO_META_MIN = 15.0

#: Dias cumpridos (acumulados) que marcam a soberania.
MARCOS_SOBERANIA = (7, 30, 90)

#: Mecanismos ativados progressivamente; o protocolo distribui pela duração.
_ESCADA_MECANISMOS: tuple[tuple[str, ...], ...] = (
    ("monitoramento do IVD", "relatório semanal"),
    ("Scroll Stopper nos apps de feed",),
    ("Banco de Minutos de Vida",),
    ("um Dia Zero no fim de semana",),
    ("Leilão de Distrações",),
    ("sessões de Foco Profundo",),
    ("missões offline",),
    ("Feed Nutritivo como substituto do feed",),
)

MENSAGEM_SEVERO = (
    "Sua triagem indica um padrão severo. O programa vai caminhar com você — e "
    "vale considerar também apoio humano (terapeuta ou grupo): tecnologia ajuda, "
    "mas não precisa ser sua única aliada."
)

MENSAGEM_LAPSO = (
    "Um lapso não é um colapso. O dia de hoje passou da meta — e é só isso: um "
    "dia. As suas conquistas continuam de pé; amanhã a sequência recomeça."
)


@dataclass(frozen=True)
class ResultadoTriagem:
    severidade: Severidade
    pontuacao: int
    pontuacao_maxima: int
    mensagem: str


def triagem(respostas: list[int]) -> ResultadoTriagem:
    """Classifica a severidade a partir do questionário de 8 itens."""
    if len(respostas) != len(PERGUNTAS_TRIAGEM):
        raise ValueError(f"a triagem tem {len(PERGUNTAS_TRIAGEM)} perguntas")
    if any(not 0 <= r <= RESPOSTA_MAXIMA for r in respostas):
        raise ValueError(f"cada resposta vai de 0 a {RESPOSTA_MAXIMA}")

    pontuacao = sum(respostas)
    maxima = len(PERGUNTAS_TRIAGEM) * RESPOSTA_MAXIMA
    if pontuacao <= 10:
        severidade = Severidade.LEVE
        mensagem = "Padrão leve: o programa curto consolida o que já está quase sob controle."
    elif pontuacao <= 21:
        severidade = Severidade.MODERADO
        mensagem = "Padrão moderado: seis semanas de redução gradual, um degrau por vez."
    else:
        severidade = Severidade.SEVERO
        mensagem = MENSAGEM_SEVERO
    return ResultadoTriagem(severidade, pontuacao, maxima, mensagem)


@dataclass(frozen=True)
class RegistroDia:
    cumpriu: bool
    minutos: float
    meta_min: float
    sequencia_atual: int
    dias_cumpridos_total: int
    marco_alcancado: int | None
    mensagem: str


class ProgramaNaoIniciado(RuntimeError):
    pass


@dataclass
class ProgramaDesintoxicacao:
    """Protocolo personalizado de redução gradual."""

    severidade: Severidade
    linha_de_base_min: float          # média atual de tela passiva por dia
    dias_cumpridos: int = 0
    sequencia_atual: int = 0
    melhor_sequencia: int = 0
    lapsos: int = 0
    marcos_alcancados: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.linha_de_base_min <= 0:
            raise ValueError("linha_de_base_min deve ser positiva")

    # ------------------------------------------------------------- protocolo

    @property
    def semanas(self) -> int:
        return _PARAMETROS[self.severidade][0]

    @property
    def meta_final_min(self) -> float:
        fracao = _PARAMETROS[self.severidade][1]
        return max(PISO_META_MIN, self.linha_de_base_min * fracao)

    def meta_da_semana(self, semana: int) -> float:
        """Meta de tela passiva (min/dia) da semana ``1..semanas`` — taper linear.

        Após o fim do protocolo, a meta permanece a final: manutenção.
        """
        if semana < 1:
            raise ValueError("as semanas contam a partir de 1")
        semana = min(semana, self.semanas)
        passo = (self.linha_de_base_min - self.meta_final_min) / self.semanas
        return self.linha_de_base_min - passo * semana

    def mecanismos_da_semana(self, semana: int) -> tuple[str, ...]:
        """Mecanismos ativos na semana: a escada acumula, nunca recua."""
        if semana < 1:
            raise ValueError("as semanas contam a partir de 1")
        degraus_por_semana = max(1, len(_ESCADA_MECANISMOS) // self.semanas)
        degraus = min(len(_ESCADA_MECANISMOS), degraus_por_semana * semana)
        ativos: list[str] = []
        for degrau in _ESCADA_MECANISMOS[:degraus]:
            ativos.extend(degrau)
        return tuple(ativos)

    # --------------------------------------------------------------- diário

    def registrar_dia(self, semana: int, minutos_passivos: float) -> RegistroDia:
        meta = self.meta_da_semana(semana)
        cumpriu = minutos_passivos <= meta
        marco = None
        if cumpriu:
            self.dias_cumpridos += 1
            self.sequencia_atual += 1
            self.melhor_sequencia = max(self.melhor_sequencia, self.sequencia_atual)
            for candidato in MARCOS_SOBERANIA:
                if self.dias_cumpridos == candidato:
                    marco = candidato
                    self.marcos_alcancados.append(candidato)
            if marco:
                mensagem = (
                    f"{marco} dias de soberania. Isto não é sorte: é um padrão novo "
                    "se consolidando."
                )
            else:
                mensagem = (
                    f"Dia cumprido: {minutos_passivos:.0f} min contra a meta de "
                    f"{meta:.0f}. Sequência: {self.sequencia_atual}."
                )
        else:
            self.lapsos += 1
            self.sequencia_atual = 0
            mensagem = MENSAGEM_LAPSO
        return RegistroDia(
            cumpriu=cumpriu,
            minutos=minutos_passivos,
            meta_min=meta,
            sequencia_atual=self.sequencia_atual,
            dias_cumpridos_total=self.dias_cumpridos,
            marco_alcancado=marco,
            mensagem=mensagem,
        )

    def progresso(self) -> dict:
        return {
            "severidade": self.severidade.value,
            "semanas": self.semanas,
            "meta_final_min": self.meta_final_min,
            "dias_cumpridos": self.dias_cumpridos,
            "sequencia_atual": self.sequencia_atual,
            "melhor_sequencia": self.melhor_sequencia,
            "lapsos": self.lapsos,
            "marcos_alcancados": list(self.marcos_alcancados),
        }


def iniciar_programa(respostas: list[int], linha_de_base_min: float) -> ProgramaDesintoxicacao:
    """Atalho: triagem + criação do programa personalizado."""
    resultado = triagem(respostas)
    return ProgramaDesintoxicacao(
        severidade=resultado.severidade, linha_de_base_min=linha_de_base_min
    )


__all__ = [
    "MARCOS_SOBERANIA",
    "MENSAGEM_LAPSO",
    "MENSAGEM_SEVERO",
    "PERGUNTAS_TRIAGEM",
    "PISO_META_MIN",
    "ProgramaDesintoxicacao",
    "RegistroDia",
    "ResultadoTriagem",
    "Severidade",
    "iniciar_programa",
    "triagem",
]
