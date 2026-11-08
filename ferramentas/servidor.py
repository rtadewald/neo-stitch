# /// script
# requires-python = ">=3.11"
# ///
"""Servidor local do Neo Stitch: a API do canvas + os arquivos dos projetos + o app compilado (app/dist).

    uv run ferramentas/servidor.py [porta]      → http://localhost:8730/

Só biblioteca padrão. No desenvolvimento, o Vite (app/, porta 5173) repassa /api e /projects para cá.

Rotas (JSON; erro volta como {"erro": "…"}):
- GET  /api/projetos                                  a lista (capa, custos, contagem)
- GET  /api/spec/agentes                              docs/AGENTES.md (vídeo → HTML por outros agentes) para o app mostrar
- PATCH /api/projetos/<slug>/impl/<IMG>/<vN[.M]> {estado?, desloc?}   aprova/descarta uma versão de HTML ou move o card dela (impl.json)
- POST /api/projetos/<slug>/impl/<IMG>/<vN[.M]>/pasta   abre a pasta da versão no Finder
- POST /api/projetos {nome, tipo, descricao}           cria (Brief + primeira Tela)
- GET  /api/projetos/<slug>?rev=…                      {rev, projeto, nos, custos, brief, diario, modelos, modelos_video,
                                                        avancos, …} ou {rev, igual: true} quando nada mudou
- PATCH /api/projetos/<slug> {nome?, padroes?, tetos?, layout?: pilha|grade|grade3|grade4|grade5, compacto?: bool, final?: código | null}
                                                       final: a versão final (vira a capa; o projeto vai para Concluídos)
- POST /api/projetos/<slug>/vistas {acao: abrir|pinar|despinar, id}   o histórico (10) e os pinados da barra lateral
- PUT  /api/projetos/<slug>/brief {texto}
- POST /api/projetos/<slug>/nos {tipo: tela|pedido, …}  cria um nó
- PATCH /api/projetos/<slug>/nos/<id> {…}              só os campos que o app pode mexer (CAMPOS_APP)
- DELETE /api/projetos/<slug>/nos/<id>                 o nó e todo o galho dele vão para a lixeira (num lote)
- POST /api/projetos/<slug>/nos/<id>/restaurar         traz de volta da lixeira (o ⌘Z do app)
- PUT  /api/projetos/<slug>/posicoes {id: {x, y}}      várias posições de uma vez (arrastar, reorganizar)
- POST /api/projetos/<slug>/nos/<id>/enviar            pedido/brief → enviado + linha na fila.jsonl (o Claude observa)
- POST /api/projetos/<slug>/nos/<id>/comentarios {texto, pin?}  · DELETE …/comentarios/<cid>
- POST /api/projetos/<slug>/refs  (imagem crua no corpo; cabeçalhos X-Nome, X-Pos "x,y") → nó referência
"""
from __future__ import annotations

import json
import mimetypes
import re
import queue
import subprocess
import sys
import threading
from typing import Callable
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, str(Path(__file__).parent))
import base as B  # noqa: E402

PORTA = 8730
DIST = B.RAIZ / 'app' / 'dist'
ID = r'([A-Z]{2,5}-\d{3,})'
SLUG = r'([a-z0-9][a-z0-9-]*)'
# o que o app pode mudar em cada tipo de nó. Todo nó: 'pos', 'recolhido' (o galho fecha), 'escondidos' (só esses filhos
# somem) e 'desloc' (ajuste manual sobre a posição automática). SO_RASCUNHO: campos do pedido que travam depois do envio.
SO_RASCUNHO = {'intencao', 'literal', 'quantidade', 'modelo', 'aspecto', 'resolucao', 'entradas', 'variacoes', 'midia', 'modelos', 'duracao'}
_TODO_NO = {'pos', 'recolhido', 'desloc', 'escondidos'}
CAMPOS_APP = {
    'brief': _TODO_NO | {'titulo', 'direcoes'},
    'tela': _TODO_NO | {'titulo'},
    'pedido': _TODO_NO | SO_RASCUNHO,
    'imagem': _TODO_NO | {'estado'},
    'referencia': _TODO_NO | {'titulo'},
    'video': _TODO_NO | {'estado'},
}
MIDIA = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.mp4', '.webm', '.bin', '.glb'}
mimetypes.add_type('model/gltf-binary', '.glb')
EXTENSOES = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif'}

ROTAS: list[tuple[str, re.Pattern, Callable]] = []


class Erro(Exception):
    def __init__(self, msg: str, status: int = 422):
        super().__init__(msg)
        self.status = status


def rota(metodo: str, padrao: str):
    def deco(fn):
        ROTAS.append((metodo, re.compile(f'^{padrao}$'), fn))
        return fn
    return deco


# ---------- projetos ----------

def resumo(slug: str) -> dict:
    p = B.ler_projeto(slug)
    lista = B.nos(slug)
    por_id = {n['id']: n for n in lista}
    imgs = [n for n in lista if n['tipo'] == 'imagem' and n.get('arquivo')]
    capa = next((n for n in imgs if n.get('estado') == 'aprovada'), None) or (imgs[-1] if imgs else None)
    capa = capa and f'/projects/{slug}/{capa.get("thumb") or capa["arquivo"]}'
    # a versão final, quando marcada, é a capa (um HTML usa a imagem de onde saiu)
    final = p.get('final')
    capa = (final and B.capa_de(slug, final, por_id)) or capa
    atualizado = max([n.get('atualizado') or n.get('criado') or '' for n in lista] + [p.get('criado', '')])
    return {'slug': slug, 'nome': p['nome'], 'prefixo': p['prefixo'], 'tipo': p['tipo'],
            'capa': capa, 'final': final, 'concluido': p.get('concluido'),
            'imagens': len(imgs), 'custos': B.custos(slug, lista), 'atualizado': atualizado,
            'pinados': [{'id': c, 'thumb': B.capa_de(slug, c, por_id), 'nome': (por_id.get(c.split('/')[0]) or {}).get('nome') or ''}
                        for c in B.vistas_de(slug, lista)['pinados']]}


@rota('GET', '/api/spec/agentes')
def spec_agentes(h, m, corpo):
    """A spec para delegar vídeo → HTML a outros agentes (docs/AGENTES.md), para o app mostrar."""
    arq = B.RAIZ / 'docs' / 'AGENTES.md'
    return {'texto': arq.read_text(encoding='utf-8'), 'caminho': str(arq), 'raiz': str(B.RAIZ)}


@rota('PATCH', f'/api/projetos/{SLUG}/impl/{ID}/' + r'(v\d+(?:\.\d+)?)')
def mudar_impl(h, m, corpo):
    """O que o app grava no impl.json de uma versão de HTML: a aprovação (estado: neutra · aprovada · descartada) e o
    deslocamento do card no canvas (desloc: {x, y} ou null); o resto é do agente."""
    slug, img, v = m.groups()
    if 'estado' in corpo and corpo['estado'] not in B.ESTADOS:
        raise Erro('estado inválido')
    d = corpo.get('desloc')
    if d is not None and not (isinstance(d, dict) and all(isinstance(d.get(k), (int, float)) for k in 'xy')):
        raise Erro('desloc inválido')
    with B.travado(slug):
        f = B.pasta(slug) / 'impl' / img / v / 'impl.json'
        ficha = B.ler_json(f, None)
        if ficha is None:
            raise Erro('Versão sem impl.json.')
        if 'estado' in corpo:
            ficha['estado'] = corpo['estado']
        if 'desloc' in corpo:
            ficha['desloc'] = {'x': round(d['x']), 'y': round(d['y'])} if d else None
        B.gravar_json(f, ficha)
    return ficha


@rota('POST', f'/api/projetos/{SLUG}/impl/{ID}/' + r'(v\d+(?:\.\d+)?)/pasta')
def abrir_pasta_impl(h, m, corpo):
    """Abre a pasta de uma versão de HTML no Finder (o servidor roda na máquina do usuário)."""
    slug, img, v = m.groups()
    d = B.pasta(slug) / 'impl' / img / v
    if not d.is_dir():
        raise Erro('A pasta desta versão não existe.')
    subprocess.run(['open', str(d)], check=False)
    return {'ok': True}


@rota('GET', '/api/projetos')
def listar(h, m, corpo):
    return sorted((resumo(s) for s in B.projetos()), key=lambda r: r['atualizado'], reverse=True)


@rota('POST', '/api/projetos')
def criar(h, m, corpo):
    nome = (corpo.get('nome') or '').strip()
    if not nome:
        raise Erro('Dê um nome ao projeto.')
    p = B.criar_projeto(nome, corpo.get('tipo') or 'webapp', corpo.get('descricao') or '')
    if (corpo.get('descricao') or '').strip():
        brief = next(n for n in B.nos(p['slug']) if n['tipo'] == 'brief')
        with B.travado(p['slug']):
            no = B.ler_no(p['slug'], brief['id'])
            no['status'] = 'enviado'
            B.gravar_no(p['slug'], no)
        B.enfileirar(p['slug'], brief['id'], 'direcoes')
    return resumo(p['slug'])


@rota('GET', f'/api/projetos/{SLUG}')
def estado(h, m, corpo):
    slug = m.group(1)
    if not (B.pasta(slug) / 'projeto.json').exists():
        raise Erro('Projeto não encontrado.', 404)
    r = B.rev(slug)
    if h.query.get('rev', [''])[0] == r:
        return {'rev': r, 'igual': True}
    d = B.pasta(slug)
    lista = B.nos(slug)
    av = B.avancos(slug, lista)
    pedir_fotos(slug, av)
    return {'rev': r, 'projeto': B.ler_projeto(slug), 'nos': lista, 'custos': B.custos(slug, lista),
            'brief': (d / 'brief.md').read_text(encoding='utf-8') if (d / 'brief.md').exists() else '',
            'diario': (d / 'diario.md').read_text(encoding='utf-8') if (d / 'diario.md').exists() else '',
            'modelos': B.MODELOS, 'aspectos': B.ASPECTOS, 'ouvinte': B.ouvinte_vivo(), 'modelos_video': B.modelos_video(),
            'avancos': av, 'vistas': B.vistas_de(slug, lista)}


@rota('POST', f'/api/projetos/{SLUG}/vistas')
def vistas(h, m, corpo):
    slug, cod = m.group(1), str(corpo.get('id') or '')
    if not cod or cod.split('/')[0] not in {n['id'] for n in B.nos(slug)}:
        raise Erro('Nó não encontrado.', 404)
    try:
        return B.vista(slug, corpo.get('acao') or '', cod)
    except ValueError as e:
        raise Erro(str(e)) from e


@rota('PATCH', f'/api/projetos/{SLUG}')
def mudar_projeto(h, m, corpo):
    slug = m.group(1)
    with B.travado(slug):
        p = B.ler_projeto(slug)
        if corpo.get('nome'):
            p['nome'] = corpo['nome'].strip()
        if isinstance(corpo.get('padroes'), dict):
            for k, v in corpo['padroes'].items():
                if k in B.PADROES:
                    p['padroes'][k] = v
        if corpo.get('layout') in B.LAYOUTS:
            p['layout'] = corpo['layout']
        if isinstance(corpo.get('compacto'), bool):
            p['compacto'] = corpo['compacto']
        if isinstance(corpo.get('tetos'), dict):
            p['tetos'].update({k: v for k, v in corpo['tetos'].items() if k in B.TETOS})
        if 'final' in corpo:
            # a versão final: um nó (imagem, vídeo, modelo) ou um HTML (<IMG>/<vN>); null reabre o projeto
            cod = corpo['final']
            if cod is None:
                p.pop('final', None)
                p.pop('concluido', None)
            else:
                img, _, v = str(cod).partition('/')
                try:
                    B.ler_no(slug, img)
                except (KeyError, ValueError):
                    raise Erro(f'{cod} não existe.')
                if v and not (B.pasta(slug) / 'impl' / img / v).is_dir():
                    raise Erro(f'{cod} não existe.')
                p['final'], p['concluido'] = str(cod), B.agora()
        B.gravar_projeto(slug, p)
    return p


@rota('PUT', f'/api/projetos/{SLUG}/brief')
def gravar_brief(h, m, corpo):
    slug = m.group(1)
    with B.travado(slug):
        (B.pasta(slug) / 'brief.md').write_text(str(corpo.get('texto', '')), encoding='utf-8')
    return {'ok': True}


# ---------- nós ----------

def limpar_campos(tipo: str, corpo: dict) -> dict:
    campos = {k: v for k, v in corpo.items() if k in CAMPOS_APP.get(tipo, set())}
    if 'estado' in campos and campos['estado'] not in B.ESTADOS:
        raise Erro('estado inválido')
    if 'quantidade' in campos:
        campos['quantidade'] = max(1, min(12, int(campos['quantidade'])))
    if 'aspecto' in campos and campos['aspecto'] not in B.ASPECTOS:
        raise Erro('aspecto inválido')
    if 'modelo' in campos:
        campos['modelo'] = B.modelo(campos['modelo'])
    if 'midia' in campos and campos['midia'] not in ('imagem', 'video'):
        raise Erro('mídia inválida')
    if 'modelos' in campos:
        catalogo = B.modelos_video()
        campos['modelos'] = [m for m in dict.fromkeys(campos['modelos'] or []) if m in catalogo][:30]
    if 'duracao' in campos:
        campos['duracao'] = max(2, min(15, int(campos['duracao'])))
    if campos.get('desloc') is not None:
        campos['desloc'] = {'x': round(float(campos['desloc']['x'])), 'y': round(float(campos['desloc']['y']))}
    if 'escondidos' in campos:
        campos['escondidos'] = [str(x) for x in (campos['escondidos'] or []) if isinstance(x, str)][:500]
    if 'recolhido' in campos:
        campos['recolhido'] = bool(campos['recolhido'])
    if 'pos' in campos and campos['pos'] is not None:
        campos['pos'] = {'x': round(float(campos['pos']['x'])), 'y': round(float(campos['pos']['y']))}
    return campos


@rota('POST', f'/api/projetos/{SLUG}/nos')
def criar_no(h, m, corpo):
    slug = m.group(1)
    tipo = corpo.get('tipo')
    if tipo not in ('tela', 'pedido'):
        raise Erro('Só telas e pedidos nascem pelo app.')
    with B.travado(slug):
        existentes = {n['id']: n for n in B.nos(slug)}
        extra = {}
        if tipo == 'tela':
            brief = next((n for n in existentes.values() if n['tipo'] == 'brief'), None)
            extra = {'titulo': (corpo.get('titulo') or 'Nova tela').strip(), 'pai': brief and brief['id']}
        else:
            entradas = [e for e in corpo.get('entradas') or [] if e in existentes and existentes[e]['tipo'] in ('imagem', 'referencia')]
            tela = next(filter(None, (tela_de(existentes, e) for e in entradas)), None)
            if not tela and existentes.get(corpo.get('tela'), {}).get('tipo') == 'tela':
                tela = corpo['tela']
            if not tela:
                raise Erro('Um pedido precisa de uma tela ou de imagens de entrada.')
            extra = {'tela': tela, 'entradas': entradas}
        campos = limpar_campos(tipo, {k: v for k, v in corpo.items() if k not in ('tipo', 'entradas', 'tela')})
        return B.novo_no(slug, tipo, **extra, **campos)


def tela_de(existentes: dict, id_: str | None, fundo: int = 0) -> str | None:
    """A tela (ramo) de um nó: imagem → pedido → tela; referência → a tela onde foi colada."""
    no = existentes.get(id_)
    if not no or fundo > 50:
        return None
    if no['tipo'] == 'tela':
        return no['id']
    if no['tipo'] == 'pedido':
        return no.get('tela')
    if no['tipo'] == 'imagem':
        return tela_de(existentes, no.get('pedido'), fundo + 1)
    return no.get('tela')


@rota('PATCH', f'/api/projetos/{SLUG}/nos/{ID}')
def mudar_no(h, m, corpo):
    slug, id_ = m.groups()
    with B.travado(slug):
        no = B.ler_no(slug, id_)
        campos = limpar_campos(no['tipo'], corpo)
        if no['tipo'] == 'pedido' and no.get('status') != 'rascunho' and SO_RASCUNHO & campos.keys():
            raise Erro('Este pedido já foi enviado; crie um novo a partir dele.')
        no.update(campos)
        return B.gravar_no(slug, no)


@rota('PUT', f'/api/projetos/{SLUG}/posicoes')
def posicoes(h, m, corpo):
    slug = m.group(1)
    with B.travado(slug):
        for id_, pos in corpo.items():
            try:
                no = B.ler_no(slug, id_)
            except (KeyError, ValueError):
                continue
            no['pos'] = {'x': round(float(pos['x'])), 'y': round(float(pos['y']))}
            B.gravar_no(slug, no)
    return {'ok': True}


@rota('DELETE', f'/api/projetos/{SLUG}/nos/{ID}')
def apagar_no(h, m, corpo):
    """Apaga o nó e todo o galho que saiu dele (um lote na lixeira; o ⌘Z restaura tudo). O brief não sai."""
    slug, id_ = m.groups()
    with B.travado(slug):
        no = B.ler_no(slug, id_)
        todos = B.nos(slug)
        if no['tipo'] == 'brief':
            raise Erro('O brief é a raiz do projeto e não é apagado.')
        junto = B.galho(todos, id_)
        sai = {id_, *junto}
        por_id = {n['id']: n for n in todos}
        if any(por_id[i]['tipo'] == 'pedido' and por_id[i].get('status') in ('enviado', 'trabalhando') for i in sai):
            raise Erro('Há um pedido em andamento neste galho: espere o Claude terminar.')
        for n in todos:  # rascunhos que ficam tiram as entradas que saíram
            if n['id'] not in sai and n.get('status') == 'rascunho' and sai & set(n.get('entradas') or []):
                n['entradas'] = [e for e in n['entradas'] if e not in sai]
                B.gravar_no(slug, n)
        B.para_lixeira(slug, id_, junto)
    return {'ok': True, 'apagados': [id_, *junto]}


@rota('POST', f'/api/projetos/{SLUG}/nos/{ID}/restaurar')
def restaurar(h, m, corpo):
    slug, id_ = m.groups()
    with B.travado(slug):
        return B.restaurar_da_lixeira(slug, id_)


@rota('POST', f'/api/projetos/{SLUG}/nos/{ID}/enviar')
def enviar(h, m, corpo):
    slug, id_ = m.groups()
    with B.travado(slug):
        no = B.ler_no(slug, id_)
        if no['tipo'] == 'pedido':
            if no.get('status') not in ('rascunho', 'erro'):
                raise Erro('Este pedido já foi enviado.')
            if not (no.get('intencao') or '').strip() and not no.get('entradas') and not no.get('variacoes'):
                raise Erro('Escreva o que você quer (ou ligue imagens ao pedido).')
            acao = 'video' if no.get('midia') == 'video' else 'gerar'
            if acao == 'video' and not no.get('modelos'):
                raise Erro('Marque ao menos um modelo de vídeo.')
        elif no['tipo'] == 'brief':
            acao = 'direcoes'
        else:
            raise Erro('Só pedidos e o brief são enviados.')
        no['status'] = 'enviado'
        no['enviado_em'] = B.agora()
        no.pop('erro', None)
        B.gravar_no(slug, no)
    B.enfileirar(slug, id_, acao)
    return no


@rota('POST', f'/api/projetos/{SLUG}/nos/{ID}/comentarios')
def comentar(h, m, corpo):
    slug, id_ = m.groups()
    texto = (corpo.get('texto') or '').strip()
    if not texto:
        raise Erro('Comentário vazio.')
    pin = corpo.get('pin')
    if pin is not None:
        pin = {'x': max(0.0, min(1.0, float(pin['x']))), 'y': max(0.0, min(1.0, float(pin['y']))),
               **({'t': round(max(0.0, float(pin['t'])), 2)} if pin.get('t') is not None else {})}
    with B.travado(slug):
        return B.comentar(slug, id_, 'voce', texto, pin)


@rota('DELETE', f'/api/projetos/{SLUG}/nos/{ID}/comentarios/([a-f0-9]+)')
def apagar_comentario(h, m, corpo):
    slug, id_, cid = m.groups()
    with B.travado(slug):
        no = B.ler_no(slug, id_)
        no['comentarios'] = [c for c in no.get('comentarios', []) if c['id'] != cid]
        B.gravar_no(slug, no)
    return {'ok': True}


@rota('POST', f'/api/projetos/{SLUG}/refs')
def subir_ref(h, m, corpo):
    slug = m.group(1)
    tipo = (h.headers.get('Content-Type') or '').split(';')[0].strip()
    ext = EXTENSOES.get(tipo)
    if not ext:
        raise Erro('Só imagens (png, jpg, webp, gif).')
    dados = h.corpo_cru
    if not dados:
        raise Erro('Imagem vazia.')
    nome = unquote(h.headers.get('X-Nome') or '').strip() or 'referência'
    pos = None
    if h.headers.get('X-Pos'):
        x, y = h.headers['X-Pos'].split(',')
        pos = {'x': round(float(x)), 'y': round(float(y))}
    with B.travado(slug):
        no = B.novo_no(slug, 'referencia', titulo=Path(nome).stem[:60], pos=pos, tela=h.headers.get('X-Tela') or None)
        arq = B.pasta(slug) / 'refs' / f'{no["id"]}.{ext}'
        arq.write_bytes(dados)
        no['arquivo'] = f'refs/{arq.name}'
        try:
            B.miniatura(arq, B.pasta(slug) / 'thumbs' / f'{no["id"]}.jpg')
            no['thumb'] = f'thumbs/{no["id"]}.jpg'
        except Exception:
            pass
        med = B.medidas(arq)
        if med:
            no['largura'], no['altura'] = med
        return B.gravar_no(slug, no)


# ---------- HTTP ----------

class Handler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(B.RAIZ), **kw)

    def log_message(self, format, *args):  # noqa: A002 (nome do pai)
        # só as escritas na API (POST/PATCH/PUT/DELETE); o polling de GET a cada 2 s não polui o terminal
        if args and '/api/' in str(args[0]) and not str(args[0]).startswith('GET'):
            sys.stderr.write('%s\n' % (format % args))

    def end_headers(self):
        if self.path.startswith('/api/'):
            self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def responder(self, status: int, dados) -> None:
        corpo = json.dumps(dados, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def api(self, metodo: str) -> None:
        url = urlparse(self.path)
        self.query = parse_qs(url.query)
        n = int(self.headers.get('Content-Length') or 0)
        self.corpo_cru = self.rfile.read(n) if n else b''
        for met, padrao, fn in ROTAS:
            m = padrao.match(unquote(url.path))
            if met == metodo and m:
                try:
                    corpo = {}
                    if self.corpo_cru and 'json' in (self.headers.get('Content-Type') or ''):
                        corpo = json.loads(self.corpo_cru)
                    self.responder(200, fn(self, m, corpo))
                except Erro as e:
                    self.responder(e.status, {'erro': str(e)})
                except (KeyError, ValueError) as e:
                    self.responder(404 if isinstance(e, KeyError) else 422, {'erro': str(e).strip("'")})
                except Exception as e:  # noqa: BLE001
                    import traceback
                    traceback.print_exc()
                    self.responder(500, {'erro': f'{type(e).__name__}: {e}'})
                return
        self.responder(404, {'erro': 'rota não encontrada'})

    def do_GET(self):
        caminho = urlparse(self.path).path
        if caminho.startswith('/api/'):
            return self.api('GET')
        if caminho.startswith('/projects/'):
            alvo = (B.RAIZ / unquote(caminho).lstrip('/')).resolve()
            if not str(alvo).startswith(str(B.PROJETOS.resolve())) or not alvo.is_file():
                return self.responder(404, {'erro': 'arquivo não encontrado'})
            # mídia gerada não muda (cache longo); o código das implementações (impl/…: html, js, css, json) muda o tempo todo
            return self.arquivo(alvo, cache=alvo.suffix.lower() in MIDIA)
        # o app compilado (SPA): qualquer outra rota cai no index.html
        alvo = (DIST / unquote(caminho).lstrip('/')).resolve()
        if str(alvo).startswith(str(DIST.resolve())) and alvo.is_file():
            return self.arquivo(alvo, cache='/assets/' in caminho)
        if (DIST / 'index.html').exists():
            return self.arquivo(DIST / 'index.html', cache=False)
        return self.responder(503, {'erro': 'app não compilado: rode `npm run build` em app/ (ou use o Vite em :5173)'})

    def arquivo(self, alvo: Path, cache: bool) -> None:
        """Serve o arquivo; com Range (vídeos: o player avança e volta sem baixar tudo)."""
        tamanho = alvo.stat().st_size
        ini, fim = 0, tamanho - 1
        faixa = re.match(r'bytes=(\d*)-(\d*)', self.headers.get('Range') or '')
        if faixa and (faixa.group(1) or faixa.group(2)):
            if faixa.group(1):
                ini = int(faixa.group(1))
                fim = int(faixa.group(2)) if faixa.group(2) else tamanho - 1
            else:
                ini = max(0, tamanho - int(faixa.group(2)))
            fim = min(fim, tamanho - 1)
            self.send_response(206)
            self.send_header('Content-Range', f'bytes {ini}-{fim}/{tamanho}')
        else:
            self.send_response(200)
        self.send_header('Content-Type', mimetypes.guess_type(alvo.name)[0] or 'application/octet-stream')
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(fim - ini + 1))
        self.send_header('Cache-Control', 'public, max-age=31536000, immutable' if cache else 'no-cache')
        self.end_headers()
        with open(alvo, 'rb') as f:
            f.seek(ini)
            restante = fim - ini + 1
            while restante > 0:
                bloco = f.read(min(1 << 20, restante))
                if not bloco:
                    break
                try:
                    self.wfile.write(bloco)
                except (BrokenPipeError, ConnectionResetError):
                    return
                restante -= len(bloco)

    def do_POST(self):
        self.api('POST')

    def do_PUT(self):
        self.api('PUT')

    def do_PATCH(self):
        self.api('PATCH')

    def do_DELETE(self):
        self.api('DELETE')


class Servidor(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        # o navegador fecha conexões no meio (troca de vídeo, recarregar a página): isso não é erro do servidor
        if isinstance(sys.exc_info()[1], (ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


def garantir_build() -> None:
    """O app compilado (app/dist) não é versionado: num clone novo ou depois de um `git pull`, ele falta ou está velho e o
    app aparece sem os recursos novos. Compila de novo quando algum arquivo de app/src é mais novo que o build."""
    app = B.RAIZ / 'app'
    fontes = [f for f in [*(app / 'src').rglob('*'), app / 'index.html', app / 'package.json'] if f.is_file()]
    build = DIST / 'index.html'
    # sem o código do app (só o dist) não há o que compilar
    if not fontes or build.exists() and max(f.stat().st_mtime for f in fontes) <= build.stat().st_mtime:
        return
    print('app/dist ausente ou desatualizado: compilando o app (npm run build)…', flush=True)
    try:
        if not (app / 'node_modules').is_dir():
            subprocess.run(['npm', '--prefix', str(app), 'install'], check=True)
        subprocess.run(['npm', '--prefix', str(app), 'run', 'build'], check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as e:
        print(f'AVISO: não consegui compilar o app ({e}). Rode `npm --prefix app install && npm --prefix app run build`.',
              flush=True)


# ---------- os prints das páginas ----------
# O cartão de uma página mostra o print (captura.png) e só roda a página viva com o mouse em cima: dezenas de páginas com
# WebGL rodando juntas travam o canvas. O servidor tira os prints que faltam (ou ficaram velhos), um de cada vez, ao fundo.
FOTOS: queue.Queue = queue.Queue()
NA_FILA: set[str] = set()
FALHAS: dict[str, float] = {}   # versão → mtime do index.html quando o print falhou (não tenta de novo até a página mudar)
PORTA_ATUAL = PORTA


def pedir_fotos(slug: str, av: dict) -> None:
    for img, a in av.items():
        for v in a['impl']:
            chave = f'{slug}/{img}/{v}'
            d = B.pasta(slug) / 'impl' / img / v
            if chave in NA_FILA or not B.captura_velha(d):
                continue
            if FALHAS.get(chave) == (d / 'index.html').stat().st_mtime:
                continue
            NA_FILA.add(chave)
            FOTOS.put((slug, img, v))


def fotografo() -> None:
    while True:
        slug, img, v = FOTOS.get()
        chave = f'{slug}/{img}/{v}'
        d = B.pasta(slug) / 'impl' / img / v
        try:
            if B.captura_velha(d) and not B.capturar(d, f'http://127.0.0.1:{PORTA_ATUAL}/projects/{slug}/impl/{img}/{v}/index.html'):
                FALHAS[chave] = (d / 'index.html').stat().st_mtime
        except OSError:
            pass
        finally:
            NA_FILA.discard(chave)


def main() -> None:
    global PORTA_ATUAL
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else PORTA
    PORTA_ATUAL = porta
    B.PROJETOS.mkdir(exist_ok=True)
    garantir_build()
    threading.Thread(target=fotografo, daemon=True).start()
    srv = Servidor(('127.0.0.1', porta), Handler)
    print(f'Neo Stitch em http://localhost:{porta}/', flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
