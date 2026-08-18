"""Protótipo web navegável do Mente Zero — stdlib pura, sem dependências.

    python3 -m mente_zero.webapp            # FREE em http://127.0.0.1:8788
    python3 -m mente_zero.webapp --pro --porta 9000

O protótipo simula o agente do sistema operacional: os botões "rolar feed" e
"ler com atenção" injetam amostras no motor com um relógio virtual, e o painel
mostra o IVD, as moedas e as intervenções exatamente como o motor as decide.
É uma vitrine do núcleo, não a casca final — nada aqui persiste.
"""

from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .core import CategoriaApp, EventoUso, MotorMenteZero, Plano
from .core.escala_zero import Exercicio, LimiteDiarioAtingido
from .core.jornada import simular_perda
from .core.models import TipoIntervencao

PASSO_S = 5.0


class EstadoApp:
    """Estado compartilhado do protótipo (um usuário, um motor)."""

    def __init__(self, plano: Plano) -> None:
        self.lock = threading.Lock()
        self.motor = MotorMenteZero(plano=plano, semente=2026)
        self.relogio = 8 * 3600.0  # o dia simulado começa às 08:00
        self.exercicio_pendente: Exercicio | None = None

    # Todos os métodos abaixo assumem o lock já adquirido pelo handler.

    def estado(self) -> dict:
        resumo = self.motor.resumo()
        perda = simular_perda(resumo.ivd)
        return {
            "plano": self.motor.plano.value,
            "hora": f"{int(self.relogio // 3600) % 24:02d}:{int(self.relogio % 3600) // 60:02d}",
            "ivd": round(resumo.ivd, 1),
            "nivel": resumo.nivel.value,
            "moedas": resumo.moedas,
            "nivel_escala": resumo.nivel_escala,
            "tela_passiva_min": round(resumo.tela_passiva_s / 60.0, 1),
            "intervencoes_hoje": resumo.intervencoes_hoje,
            "simulador_perda": {"fator": round(perda.fator, 3), "rotulo": perda.rotulo,
                                "aviso": perda.aviso},
        }

    def simular_uso(self, modo: str, segundos: float) -> list[dict]:
        intervencoes = []
        passos = max(1, int(segundos / PASSO_S))
        for i in range(passos):
            if modo == "compulsivo":
                evento = EventoUso(
                    timestamp=self.relogio,
                    app_id="reels",
                    categoria=CategoriaApp.FEED_SOCIAL,
                    duracao_s=PASSO_S,
                    distancia_scroll_px=6500.0,
                    toques=0,
                    abertura_app=(i == 0),
                    hora_local=int(self.relogio // 3600) % 24,
                )
            else:
                evento = EventoUso(
                    timestamp=self.relogio,
                    app_id="ebook",
                    categoria=CategoriaApp.LEITURA,
                    duracao_s=PASSO_S,
                    distancia_scroll_px=250.0,
                    toques=1,
                    inversoes_direcao=1,
                )
            intervencao = self.motor.processar(evento)
            self.relogio += PASSO_S
            if intervencao.ativa:
                registro = {"tipo": intervencao.tipo.value, "mensagem": intervencao.mensagem}
                exercicio = intervencao.payload.get("exercicio")
                if isinstance(exercicio, Exercicio):
                    registro["exercicio"] = exercicio.enunciado
                intervencoes.append(registro)
                if intervencao.tipo is TipoIntervencao.TELA_CINZA:
                    self.relogio += intervencao.duracao_s
        return intervencoes

    def responder_stopper(self, aceitou: bool) -> None:
        self.motor.stopper.responder(aceitou_desafio=aceitou)

    def pedir_exercicio(self) -> dict:
        try:
            exercicio = self.motor.proximo_exercicio()
        except LimiteDiarioAtingido as erro:
            return {"erro": str(erro)}
        self.exercicio_pendente = exercicio
        return {
            "id": exercicio.id,
            "tipo": exercicio.tipo.value,
            "nivel": exercicio.nivel,
            "enunciado": exercicio.enunciado,
            "alternativas": list(exercicio.alternativas),
            "tempo_alvo_s": exercicio.tempo_alvo_s,
        }

    def responder_exercicio(self, resposta: str, tempo_s: float) -> dict:
        if self.exercicio_pendente is None:
            return {"erro": "peça um exercício antes de responder"}
        resultado = self.motor.responder_exercicio(
            self.exercicio_pendente, resposta, tempo_s
        )
        gabarito = self.exercicio_pendente.resposta
        self.exercicio_pendente = None
        return {
            "correto": resultado.correto,
            "dentro_do_tempo": resultado.dentro_do_tempo,
            "nivel_novo": resultado.nivel_novo,
            "moedas_ganhas": resultado.moedas_ganhas,
            "gabarito": gabarito,
        }

    def pedir_acesso(self, app: str, minutos_exercicio: float) -> dict:
        return self.motor.solicitar_acesso(app, minutos_exercicio=minutos_exercicio)


PAGINA = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mente Zero — protótipo</title>
<style>
  :root { --fundo:#0d1117; --painel:#161b22; --borda:#30363d; --texto:#e6edf3;
          --fraco:#8b949e; --acento:#3fb950; --alerta:#d29922; --critico:#f85149; }
  * { box-sizing:border-box; margin:0; }
  body { background:var(--fundo); color:var(--texto);
         font:15px/1.5 system-ui,-apple-system,sans-serif; padding:1.2rem; }
  h1 { font-size:1.2rem; margin-bottom:.2rem; }
  .sub { color:var(--fraco); font-size:.85rem; margin-bottom:1rem; }
  .grade { display:grid; gap:1rem; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); }
  .painel { background:var(--painel); border:1px solid var(--borda);
            border-radius:10px; padding:1rem; }
  .painel h2 { font-size:.95rem; margin-bottom:.6rem; color:var(--fraco);
               text-transform:uppercase; letter-spacing:.05em; }
  .medidor { height:14px; background:#21262d; border-radius:7px; overflow:hidden; margin:.4rem 0; }
  .medidor > div { height:100%; width:0%; background:var(--acento); transition:all .4s; }
  .numeros { display:flex; gap:1.2rem; flex-wrap:wrap; margin-top:.5rem; }
  .numeros b { display:block; font-size:1.3rem; }
  .numeros span { color:var(--fraco); font-size:.78rem; }
  button { background:#21262d; color:var(--texto); border:1px solid var(--borda);
           border-radius:8px; padding:.55rem .9rem; cursor:pointer; font-size:.9rem; }
  button:hover { border-color:var(--fraco); }
  button.primario { background:#1f6feb; border-color:#1f6feb; }
  .fila { display:flex; gap:.5rem; flex-wrap:wrap; margin:.3rem 0; }
  #log { max-height:300px; overflow-y:auto; display:flex; flex-direction:column; gap:.45rem; }
  .item { border-left:3px solid var(--alerta); background:#1c2128;
          padding:.5rem .7rem; border-radius:0 8px 8px 0; font-size:.86rem; }
  .item.critico { border-color:var(--critico); }
  .item .tag { color:var(--fraco); font-size:.72rem; text-transform:uppercase; }
  #exercicio p { margin:.5rem 0; }
  input[type=text] { background:#0d1117; border:1px solid var(--borda); color:var(--texto);
                     border-radius:8px; padding:.5rem; width:100%; margin:.4rem 0; }
  .aviso { color:var(--fraco); font-size:.75rem; margin-top:.5rem; font-style:italic; }
</style></head><body>
<h1>MENTE ZERO <span style="color:var(--fraco)">· protótipo do motor</span></h1>
<p class="sub">Plano <b id="plano"></b> · relógio simulado <b id="hora"></b> —
os botões injetam eventos de uso; as intervenções vêm do núcleo real.</p>
<div class="grade">
  <div class="painel">
    <h2>Índice de Vício Digital</h2>
    <div class="medidor"><div id="barra"></div></div>
    <div class="numeros">
      <div><b id="ivd">–</b><span>IVD (<span id="nivel">–</span>)</span></div>
      <div><b id="moedas">–</b><span>moedas</span></div>
      <div><b id="escala">–</b><span>nível Escala ZERO</span></div>
      <div><b id="passiva">–</b><span>min de tela passiva</span></div>
      <div><b id="interv">–</b><span>intervenções hoje</span></div>
    </div>
    <p id="perda" class="aviso"></p>
  </div>
  <div class="painel">
    <h2>Simular uso</h2>
    <div class="fila">
      <button onclick="usar('compulsivo',60)">Rolar feed 1 min</button>
      <button onclick="usar('compulsivo',300)">Rolar feed 5 min</button>
      <button onclick="usar('saudavel',300)">Ler com atenção 5 min</button>
    </div>
    <div class="fila">
      <button onclick="stopper(true)">Aceitar desafio do Stopper</button>
      <button onclick="stopper(false)">Ignorar Stopper</button>
      <button onclick="acesso()">Pedir acesso ao Instagram</button>
    </div>
  </div>
  <div class="painel">
    <h2>Academia do Córtex</h2>
    <button class="primario" onclick="exercicio()">Pedir exercício</button>
    <div id="exercicio"></div>
  </div>
  <div class="painel">
    <h2>Intervenções do motor</h2>
    <div id="log"></div>
  </div>
</div>
<script>
const $ = id => document.getElementById(id);
let inicioExercicio = null;
async function api(caminho, corpo) {
  const opcoes = corpo ? {method:'POST', headers:{'Content-Type':'application/json'},
                          body:JSON.stringify(corpo)} : {};
  const resposta = await fetch(caminho, opcoes);
  return resposta.json();
}
function pintarEstado(e) {
  $('plano').textContent = e.plano.toUpperCase();
  $('hora').textContent = e.hora;
  $('ivd').textContent = e.ivd; $('nivel').textContent = e.nivel;
  $('moedas').textContent = e.moedas; $('escala').textContent = e.nivel_escala;
  $('passiva').textContent = e.tela_passiva_min; $('interv').textContent = e.intervencoes_hoje;
  const barra = $('barra'); barra.style.width = e.ivd + '%';
  barra.style.background = e.ivd >= 75 ? 'var(--critico)' : e.ivd >= 50 ? 'var(--alerta)'
                          : e.ivd >= 25 ? '#d2b022' : 'var(--acento)';
  $('perda').textContent = e.simulador_perda.rotulo + ' — ' + e.simulador_perda.aviso;
}
function registrar(itens) {
  for (const item of itens) {
    const div = document.createElement('div');
    div.className = 'item' + (['micro_pausa_sensorial','mensagem_eu_futuro','tela_cinza']
                              .includes(item.tipo) ? ' critico' : '');
    div.innerHTML = `<span class="tag">${item.tipo}</span><br>${item.mensagem || ''}` +
                    (item.exercicio ? `<br><i>${item.exercicio}</i>` : '');
    $('log').prepend(div);
  }
}
async function atualizar() { pintarEstado(await api('/api/estado')); }
async function usar(modo, segundos) {
  const r = await api('/api/evento', {modo, segundos});
  registrar(r.intervencoes); pintarEstado(r.estado);
}
async function stopper(aceitou) {
  const r = await api('/api/stopper', {aceitou}); pintarEstado(r.estado);
}
async function acesso() {
  const r = await api('/api/acesso', {app:'instagram', minutos_exercicio:0});
  registrar([{tipo: r.liberado ? 'acesso_liberado' : 'acesso_negado',
    mensagem: r.liberado ? `Liberado via ${r.via}. Saldo: ${r.saldo} moeda(s).`
      : `Sem moedas. O leilão pede ${r.preco_min} min de exercício difícil.`}]);
  await atualizar();
}
async function exercicio() {
  const e = await api('/api/exercicio', {});
  const alvo = $('exercicio');
  if (e.erro) { alvo.innerHTML = `<p class="aviso">${e.erro}</p>`; return; }
  inicioExercicio = Date.now();
  alvo.innerHTML = `<p><b>${e.tipo}</b> · nível ${e.nivel} · alvo ${e.tempo_alvo_s}s</p>
    <p>${e.enunciado}</p>
    ${e.alternativas.length ? '<p class="aviso">Opções: ' + e.alternativas.join(' · ') + '</p>' : ''}
    <input type="text" id="resposta" placeholder="sua resposta">
    <button class="primario" onclick="responder()">Responder</button>`;
}
async function responder() {
  const tempo = (Date.now() - inicioExercicio) / 1000;
  const r = await api('/api/responder', {resposta: $('resposta').value, tempo_s: tempo});
  $('exercicio').innerHTML = r.erro ? `<p class="aviso">${r.erro}</p>` :
    `<p>${r.correto ? '✔ Correto' : '✘ Incorreto (gabarito: ' + r.gabarito + ')'}
     ${r.dentro_do_tempo ? '· no tempo' : '· fora do tempo'}
     · nível agora: ${r.nivel_novo} · +${r.moedas_ganhas} moeda(s)</p>
     <button class="primario" onclick="exercicio()">Próximo</button>`;
  await atualizar();
}
atualizar();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    app: EstadoApp  # injetado por criar_servidor

    def log_message(self, *args) -> None:  # silencia o log por requisição
        pass

    def _json(self, dados: dict | list, codigo: int = 200) -> None:
        corpo = json.dumps(dados).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _corpo(self) -> dict:
        tamanho = int(self.headers.get("Content-Length", 0))
        if not tamanho:
            return {}
        try:
            return json.loads(self.rfile.read(tamanho))
        except json.JSONDecodeError:
            return {}

    def do_GET(self) -> None:
        if self.path == "/":
            corpo = PAGINA.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
        elif self.path == "/api/estado":
            with self.app.lock:
                self._json(self.app.estado())
        else:
            self._json({"erro": "rota desconhecida"}, 404)

    def do_POST(self) -> None:
        corpo = self._corpo()
        with self.app.lock:
            if self.path == "/api/evento":
                modo = corpo.get("modo", "compulsivo")
                segundos = float(corpo.get("segundos", 60))
                intervencoes = self.app.simular_uso(modo, min(segundos, 3600.0))
                self._json({"intervencoes": intervencoes, "estado": self.app.estado()})
            elif self.path == "/api/stopper":
                self.app.responder_stopper(bool(corpo.get("aceitou")))
                self._json({"estado": self.app.estado()})
            elif self.path == "/api/exercicio":
                self._json(self.app.pedir_exercicio())
            elif self.path == "/api/responder":
                self._json(
                    self.app.responder_exercicio(
                        str(corpo.get("resposta", "")), float(corpo.get("tempo_s", 0.0))
                    )
                )
            elif self.path == "/api/acesso":
                self._json(
                    self.app.pedir_acesso(
                        str(corpo.get("app", "instagram")),
                        float(corpo.get("minutos_exercicio", 0.0)),
                    )
                )
            else:
                self._json({"erro": "rota desconhecida"}, 404)


def criar_servidor(plano: Plano, porta: int) -> ThreadingHTTPServer:
    handler = type("HandlerLigado", (Handler,), {"app": EstadoApp(plano)})
    return ThreadingHTTPServer(("127.0.0.1", porta), handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Protótipo web do Mente Zero")
    parser.add_argument("--pro", action="store_true")
    parser.add_argument("--porta", type=int, default=8788)
    args = parser.parse_args()
    plano = Plano.PRO if args.pro else Plano.FREE
    servidor = criar_servidor(plano, args.porta)
    print(f"Mente Zero ({plano.value}) em http://127.0.0.1:{args.porta}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        servidor.shutdown()


if __name__ == "__main__":
    main()
