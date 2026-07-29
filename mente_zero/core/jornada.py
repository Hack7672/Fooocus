"""Camada 5 — Reconstrução da identidade e narrativa (Efeito Fênix).

* :class:`JornadaDoHeroi` — progressão por semanas de foco cumpridas. O FREE
  vive o prólogo; a jornada completa, com habilidades desbloqueáveis, é PRO.
* :func:`simular_perda` — o Simulador de Perda Cognitiva. É **simbólico por
  contrato**: a saída carrega o aviso obrigatório e a interface deve exibi-lo
  (ver ARQUITETURA.md §6 — metáfora motivacional, não medida de massa cinzenta).
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Plano
from .planos import direitos

# --------------------------------------------------------------------------
# Jornada do Herói Cognitivo
# --------------------------------------------------------------------------

#: (título, habilidade desbloqueada, semanas de foco exigidas)
CAPITULOS: tuple[tuple[str, str, int], ...] = (
    ("Prólogo — O Despertar", "Ver o próprio IVD sem desviar o olhar", 0),
    ("Capítulo 1 — O Chamado", "Primeira moeda conquistada por mérito", 1),
    ("Capítulo 2 — O Deserto do Feed", "Scroll Stopper aceito sem hesitar", 2),
    ("Capítulo 3 — A Travessia do Tédio", "Sessão de Foco Profundo de 45 min", 4),
    ("Capítulo 4 — O Espelho do Eu Futuro", "Diálogo com quem você está virando", 6),
    ("Capítulo 5 — O Confronto com o Algoritmo do Vazio", "Um Dia Zero por vontade própria", 9),
    ("Epílogo — O Guardião da Própria Mente", "A atenção como escolha, não como sorte", 12),
)

#: Dias de foco na semana para que ela conte como "semana de foco".
META_DIAS_DE_FOCO = 5

#: Capítulos acessíveis no plano FREE (apenas o prólogo).
CAPITULOS_FREE = 1


@dataclass(frozen=True)
class Capitulo:
    indice: int
    titulo: str
    habilidade: str
    semanas_exigidas: int


@dataclass
class JornadaDoHeroi:
    """Progressão narrativa por semanas de foco."""

    plano: Plano = Plano.FREE
    semanas_de_foco: int = 0

    def registrar_semana(self, dias_de_foco: int) -> bool:
        """Fecha uma semana; conta como semana de foco se a meta foi cumprida."""
        if not 0 <= dias_de_foco <= 7:
            raise ValueError("dias_de_foco deve estar entre 0 e 7")
        cumprida = dias_de_foco >= META_DIAS_DE_FOCO
        if cumprida:
            self.semanas_de_foco += 1
        return cumprida

    def capitulos_desbloqueados(self) -> tuple[Capitulo, ...]:
        completa = direitos(self.plano).avatar_personalizado  # jornada completa é PRO
        limite = len(CAPITULOS) if completa else CAPITULOS_FREE
        desbloqueados = []
        for indice, (titulo, habilidade, exigidas) in enumerate(CAPITULOS[:limite]):
            if self.semanas_de_foco >= exigidas:
                desbloqueados.append(Capitulo(indice, titulo, habilidade, exigidas))
        return tuple(desbloqueados)

    def proximo_capitulo(self) -> Capitulo | None:
        desbloqueados = len(self.capitulos_desbloqueados())
        completa = direitos(self.plano).avatar_personalizado
        limite = len(CAPITULOS) if completa else CAPITULOS_FREE
        if desbloqueados >= limite:
            return None
        titulo, habilidade, exigidas = CAPITULOS[desbloqueados]
        return Capitulo(desbloqueados, titulo, habilidade, exigidas)


# --------------------------------------------------------------------------
# Simulador de Perda Cognitiva
# --------------------------------------------------------------------------

AVISO_SIMBOLICO = (
    "Representação simbólica do custo atencional do seu padrão de uso. "
    "Não é diagnóstico nem medida do seu cérebro."
)


@dataclass(frozen=True)
class SimulacaoPerda:
    fator: float          # 1.0 = íntegro; 0.6 = encolhimento máximo da metáfora
    rotulo: str
    aviso: str            # sempre AVISO_SIMBOLICO; a UI é obrigada a exibi-lo


def simular_perda(ivd: float) -> SimulacaoPerda:
    """Mapeia o IVD (0-100) no fator visual do encolhimento simbólico."""
    ivd = max(0.0, min(100.0, ivd))
    fator = 1.0 - 0.4 * (ivd / 100.0)
    if ivd < 25:
        rotulo = "Mente íntegra: a atenção está com você."
    elif ivd < 50:
        rotulo = "Primeiras rachaduras: o feed começa a decidir por você."
    elif ivd < 75:
        rotulo = "Erosão visível: horas suas escorrendo pela rolagem."
    else:
        rotulo = "Encolhimento simbólico máximo: é disto que o Eu Futuro fala."
    return SimulacaoPerda(fator=fator, rotulo=rotulo, aviso=AVISO_SIMBOLICO)


__all__ = [
    "AVISO_SIMBOLICO",
    "CAPITULOS",
    "Capitulo",
    "JornadaDoHeroi",
    "META_DIAS_DE_FOCO",
    "SimulacaoPerda",
    "simular_perda",
]
