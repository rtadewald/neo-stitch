"""Base do Neo Stitch: caminhos, JSON atômico, trava por projeto, nós e códigos.

Cada projeto vive em projects/<slug>/:
    projeto.json   config (nome, prefixo, tipo, padrões de geração, tetos de custo, contador de códigos)
    brief.md       o brief (mantido pelo Claude; editável no app)
    diario.md      o diário de decisões (o Claude escreve)
    nodes/<COD>.json  um arquivo por nó (brief, tela, pedido, imagem, referencia)
    images/<COD>.png  · thumbs/<COD>.jpg · refs/<COD>.<ext> · lixeira/

Contrato dos nós: .claude/skills/neo-stitch/modelo.md. Toda escrita passa por `travado(slug)` (fcntl, ou msvcrt no
Windows) e `gravar_json` (temp + rename), então o servidor e os scripts do Claude nunca perdem a escrita um do outro.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path

if os.name == 'nt':
    import msvcrt
else:
    import fcntl

# no Windows o console e os pipes saem em cp1252: acento passa, mas 🔥 e → derrubam o print
for _saida in (sys.stdout, sys.stderr):
    if _saida and (_saida.encoding or '').lower() not in ('utf-8', 'utf8'):
        try:
            _saida.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass

RAIZ = Path(__file__).resolve().parent.parent
PROJETOS = RAIZ / 'projects'
FILA = RAIZ / 'fila.jsonl'

TIPOS_NO = ('brief', 'tela', 'pedido', 'imagem', 'referencia', 'video', 'modelo')
ESTADOS = ('neutra', 'favorita', 'aprovada', 'descartada')
MODELOS = {
    'openai/gpt-image-2': {'nome': 'GPT Image 2', 'preco': 0.14},
    'openai/gpt-image-2.5-sunburst': {'nome': 'GPT Image 2.5 Sunburst', 'preco': 0.14},
    'openai/gpt-image-2.5-flare': {'nome': 'GPT Image 2.5 Flare', 'preco': 0.14},
    'google/gemini-3-pro-image': {'nome': 'Nano Banana Pro', 'preco': 0.14},
    'google/gemini-3.1-flash-image': {'nome': 'Nano Banana Flash', 'preco': 0.04},
    'bytedance-seed/seedream-5-0-pro': {'nome': 'Seedream 5 Pro', 'preco': 0.05},
    'black-forest-labs/flux.2-pro': {'nome': 'Flux 2 Pro', 'preco': 0.05},
}
ALIASES = {'gpt': 'openai/gpt-image-2', 'gpt2': 'openai/gpt-image-2', 'sunburst': 'openai/gpt-image-2.5-sunburst',
           'flare': 'openai/gpt-image-2.5-flare', 'pro': 'google/gemini-3-pro-image',
           'flash': 'google/gemini-3.1-flash-image', 'seedream': 'bytedance-seed/seedream-5-0-pro',
           'flux': 'black-forest-labs/flux.2-pro'}
ASPECTOS = ('16:9', '9:16', '4:3', '3:4', '1:1', '21:9', '2:3', '3:2')
PADROES_POR_TIPO = {
    'site': {'aspecto': '16:9'}, 'webapp': {'aspecto': '16:9'}, 'dashboard': {'aspecto': '16:9'},
    'app': {'aspecto': '9:16'},
}
PADROES = {'modelo': 'openai/gpt-image-2', 'aspecto': '16:9', 'resolucao': '1K', 'quantidade': 3}
TETOS = {'imagens_por_pedido': 6, 'diario_usd': 20.0, 'video_por_pedido_usd': 2.0}
# pedidos de vídeo (image-to-video): o catálogo vem do OpenRouter e fica em ferramentas/dados/modelos_video.json
VIDEO_PADRAO = {'modelos': ['alibaba/wan-3.0'], 'duracao': 4, 'resolucao': '720p'}
# os que o app oferece (na ordem do menu), com a nota que aparece ao escolher; o resto do catálogo só pelo gerar_video.py
VIDEO_NO_APP = {
    'x-ai/grok-imagine-video-1.5-lite': 'rápido e barato',
    'alibaba/wan-3.0': 'padrão',
    'alibaba/wan-3.0-prime': '',
    'minimax/hailuo-3': '',
    'bytedance/seedance-2.5': 'poderoso e caro',
}
SUBPASTAS = ('nodes', 'images', 'thumbs', 'refs', 'videos', 'models')
LAYOUTS = ('pilha', 'grade', 'grade3', 'grade4', 'grade5')
CODIGO = re.compile(r'\b([A-Z]{2,5})-(\d{3,})\b')
CATALOGO_VIDEO = Path(__file__).parent / 'dados' / 'modelos_video.json'
_catalogo: tuple[int, dict] = (0, {})


def modelos_video(todos: bool = False) -> dict:
    """{id: {nome, duracoes, resolucoes, custo_6s, …, nota}} — por padrão, só os que o app oferece no pedido de vídeo.
    O JSON só é relido quando muda no disco."""
    global _catalogo
    try:
        mtime = CATALOGO_VIDEO.stat().st_mtime_ns
    except FileNotFoundError:
        return {}
    if _catalogo[0] != mtime:
        _catalogo = (mtime, ler_json(CATALOGO_VIDEO, {}))
    cat = _catalogo[1]
    if todos:
        return cat
    return {m: {**cat[m], 'nota': nota} for m, nota in VIDEO_NO_APP.items() if m in cat}


def json_ou_arquivo(valor: str) -> str:
    """O argumento --json aceita o JSON direto ou o caminho de um arquivo com ele."""
    return valor if valor.lstrip()[:1] in '[{' else Path(valor).read_text(encoding='utf-8')


def agora() -> str:
    return datetime.now().isoformat(timespec='seconds')


def modelo(nome: str | None) -> str:
    nome = (nome or '').strip()
    return ALIASES.get(nome.lower(), nome) or PADROES['modelo']


# ---------- JSON e trava ----------

def ler_json(caminho: Path, padrao=None):
    try:
        return json.loads(Path(caminho).read_text(encoding='utf-8'))
    except (FileNotFoundError, ValueError):
        return padrao


def gravar_json(caminho: Path, dados) -> None:
    """Grava de uma vez (temporário + rename): quem lê nunca vê um JSON pela metade."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=caminho.parent, suffix='.tmp', delete=False) as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
    # no Windows o rename falha enquanto alguém (o servidor servindo, o antivírus) está com o destino aberto: tenta de novo
    for tentativa in range(50):
        try:
            os.replace(f.name, caminho)
            return
        except PermissionError:
            if tentativa == 49:
                raise
            time.sleep(0.02)


def _trancar(f) -> None:
    if os.name == 'nt':
        f.seek(0)
        while True:  # LK_LOCK desiste em 10 s; aqui espera o quanto precisar, como o flock
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                time.sleep(0.01)
    fcntl.flock(f, fcntl.LOCK_EX)


def _destrancar(f) -> None:
    if os.name == 'nt':
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(f, fcntl.LOCK_UN)


@contextmanager
def trava_arquivo(caminho: Path):
    with open(caminho, 'a+') as f:
        _trancar(f)
        try:
            yield
        finally:
            _destrancar(f)


@contextmanager
def travado(slug: str):
    """Trava exclusiva do projeto (servidor e scripts): ler → mudar → gravar sem corrida."""
    pasta(slug).mkdir(parents=True, exist_ok=True)
    with trava_arquivo(pasta(slug) / '.lock'):
        yield


# ---------- projetos ----------

def pasta(slug: str) -> Path:
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', slug or ''):
        raise ValueError(f'slug inválido: {slug!r}')
    return PROJETOS / slug


def slugify(texto: str) -> str:
    t = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-') or 'projeto'


def projetos() -> list[str]:
    if not PROJETOS.exists():
        return []
    return sorted(p.name for p in PROJETOS.iterdir() if (p / 'projeto.json').exists())


def ler_projeto(slug: str) -> dict:
    p = ler_json(pasta(slug) / 'projeto.json')
    if p is None:
        raise KeyError(f'projeto não encontrado: {slug}')
    return p


def gravar_projeto(slug: str, dados: dict) -> None:
    gravar_json(pasta(slug) / 'projeto.json', dados)


def prefixo_livre(nome: str) -> str:
    usados = {ler_projeto(s).get('prefixo') for s in projetos()}
    letras = re.sub(r'[^A-Z]', '', unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode().upper()) or 'NEO'
    candidatos = [letras[:3]] + [letras[0] + letras[i] + letras[j] for i in range(1, len(letras)) for j in range(i + 1, len(letras))]
    for c in candidatos:
        if len(c) == 3 and c not in usados:
            return c
    n = 1
    while f'{letras[:2]}{n}' in usados:
        n += 1
    return f'{letras[:2]}{n}'.ljust(3, 'X')


def criar_projeto(nome: str, tipo: str = 'webapp', descricao: str = '', prefixo: str | None = None,
                  tela: str = 'Principal', slug: str | None = None) -> dict:
    """Cria o projeto com o nó Brief e a primeira Tela. Devolve o projeto.json."""
    slug = slug or slugify(nome)
    base_slug, n = slug, 2
    while (PROJETOS / slug).exists():
        slug, n = f'{base_slug}-{n}', n + 1
    tipo = tipo if tipo in PADROES_POR_TIPO else 'webapp'
    projeto = {
        'slug': slug, 'nome': nome.strip(), 'prefixo': (prefixo or prefixo_livre(nome)).upper(), 'tipo': tipo,
        'criado': agora(), 'padroes': {**PADROES, **PADROES_POR_TIPO[tipo]}, 'tetos': dict(TETOS), 'contador': 0,
    }
    with travado(slug):
        for sub in SUBPASTAS:
            (pasta(slug) / sub).mkdir(parents=True, exist_ok=True)
        gravar_projeto(slug, projeto)
        (pasta(slug) / 'brief.md').write_text(f'# {projeto["nome"]}\n\n{descricao.strip()}\n', encoding='utf-8')
        (pasta(slug) / 'diario.md').write_text(f'# Diário · {projeto["nome"]}\n', encoding='utf-8')
        brief = novo_no(slug, 'brief', titulo=projeto['nome'], status='rascunho', direcoes=[], pos={'x': 0, 'y': 0})
        novo_no(slug, 'tela', titulo=tela, pai=brief['id'], pos={'x': 460, 'y': 0})
    return ler_projeto(slug)


# ---------- códigos e nós ----------

def proximo_codigo(slug: str) -> str:
    """Chame com a trava do projeto. Um código é dado uma vez e nunca é reaproveitado."""
    p = ler_projeto(slug)
    p['contador'] = int(p.get('contador', 0)) + 1
    gravar_projeto(slug, p)
    return f'{p["prefixo"]}-{p["contador"]:03d}'


def caminho_no(slug: str, id_: str) -> Path:
    if not CODIGO.fullmatch(id_ or ''):
        raise ValueError(f'código inválido: {id_!r}')
    return pasta(slug) / 'nodes' / f'{id_}.json'


def ler_no(slug: str, id_: str) -> dict:
    no = ler_json(caminho_no(slug, id_))
    if no is None:
        raise KeyError(f'nó não encontrado: {id_}')
    return no


def gravar_no(slug: str, no: dict) -> dict:
    no['atualizado'] = agora()
    gravar_json(caminho_no(slug, no['id']), no)
    return no


def novo_no(slug: str, tipo: str, **campos) -> dict:
    """Chame com a trava do projeto."""
    if tipo not in TIPOS_NO:
        raise ValueError(f'tipo inválido: {tipo}')
    no = {'id': proximo_codigo(slug), 'tipo': tipo, 'criado': agora(), 'pos': None, 'comentarios': [], **campos}
    if tipo in ('imagem', 'video'):
        no.setdefault('estado', 'neutra')
    if tipo == 'pedido':
        if no.setdefault('midia', 'imagem') == 'video':
            for k, v in VIDEO_PADRAO.items():
                no.setdefault(k, list(v) if isinstance(v, list) else v)
        p = ler_projeto(slug)['padroes']
        for k in ('modelo', 'aspecto', 'resolucao', 'quantidade'):
            no.setdefault(k, p[k])
        for k, v in (('entradas', []), ('intencao', ''), ('literal', False), ('status', 'rascunho'), ('saidas', [])):
            no.setdefault(k, v)
    return gravar_no(slug, no)


def comentar(slug: str, id_: str, autor: str, texto: str, pin: dict | None = None) -> dict:
    """Chame com a trava do projeto. `pin` = {x, y} de 0 a 1 sobre a imagem (+ t, o segundo, num vídeo)."""
    no = ler_no(slug, id_)
    c = {'id': uuid.uuid4().hex[:8], 'autor': autor, 'texto': texto, 'pin': pin, 'criado': agora()}
    no.setdefault('comentarios', []).append(c)
    gravar_no(slug, no)
    return c


def nos(slug: str) -> list[dict]:
    d = pasta(slug) / 'nodes'
    if not d.exists():
        return []
    out = []
    for f in sorted(d.glob('*.json')):
        no = ler_json(f)
        if no:
            out.append(no)
    return out


def rev(slug: str) -> str:
    """Muda sempre que algum arquivo do projeto que o app mostra muda (o app só recarrega quando muda)."""
    d = pasta(slug)
    marcas = []
    # impl/: uma versão nova muda a pasta da imagem; impl.json (ou origem.json) diz quem faz, de qual vídeo e em que pé está
    impl = [*sorted((d / 'impl').glob('*')), *sorted((d / 'impl').glob('*/*/impl.json')), *sorted((d / 'impl').glob('*/*/origem.json'))]
    for f in [d / 'projeto.json', d / 'brief.md', d / 'diario.md', *sorted((d / 'nodes').glob('*.json')), *impl]:
        try:
            marcas.append(f'{f.relative_to(d)}:{f.stat().st_mtime_ns}')
        except FileNotFoundError:
            pass
    marcas.append(f'ouvinte:{ouvinte_vivo()}')
    return hashlib.md5('|'.join(marcas).encode()).hexdigest()[:12]


def resolver_codigo(cod: str) -> tuple[str, str]:
    """'JAR-042' → ('jarvisos', 'JAR-042'), procurando o projeto pelo prefixo."""
    m = CODIGO.search((cod or '').upper())
    if not m:
        raise ValueError(f'código inválido: {cod!r}')
    for s in projetos():
        if ler_projeto(s).get('prefixo') == m.group(1):
            return s, m.group(0)
    raise KeyError(f'nenhum projeto com prefixo {m.group(1)}')


# ---------- custos ----------

def custos(slug: str, lista: list[dict] | None = None) -> dict:
    hoje = date.today().isoformat()
    total = dia = 0.0
    for no in lista if lista is not None else nos(slug):
        if no.get('tipo') in ('imagem', 'video') and no.get('custo'):
            total += no['custo']
            if (no.get('criado') or '').startswith(hoje) and not no.get('legado'):
                dia += no['custo']
    return {'total': round(total, 4), 'hoje': round(dia, 4)}


# ---------- avanços ("fogo": a imagem virou algo maior — vídeo, tentativas de HTML) ----------

def avancos(slug: str, lista: list[dict] | None = None) -> dict:
    """{código da imagem: {videos: [códigos], impl: [versões], origens: {versão: vídeo}}} — só as imagens que já avançaram.

    Vídeo conta quando sai de um pedido de vídeo cuja 1ª entrada é a imagem (e não deu erro); `impl` são as pastas
    projects/<slug>/impl/<código>/vN/ (as tentativas de HTML). Cada versão traz `impl.json` (docs/AGENTES.md: agente, vídeo,
    status, etapa, progresso; vai em `trabalhos`) ou, nas antigas, só `origem.json` com {"video"}. Com vídeo, a versão
    deriva do vídeo, não da imagem (img-to-html não tem origem).
    """
    lista = lista if lista is not None else nos(slug)
    por_id = {n['id']: n for n in lista}
    out: dict[str, dict] = {}
    for p in lista:
        if p.get('tipo') != 'pedido' or p.get('midia') != 'video' or not p.get('entradas'):
            continue
        img = p['entradas'][0]
        if por_id.get(img, {}).get('tipo') != 'imagem':
            continue
        vids = [v for v in p.get('saidas') or [] if por_id.get(v, {}).get('tipo') == 'video' and not por_id[v].get('erro')]
        if vids:
            out.setdefault(img, novo_avanco())['videos'] += vids
    impl = pasta(slug) / 'impl'
    if impl.is_dir():
        for d in sorted(impl.iterdir()):
            versoes = sorted((v.name for v in d.iterdir() if v.is_dir()), key=ordem_versao) if d.is_dir() else []
            if d.name in por_id and versoes:
                a = out.setdefault(d.name, novo_avanco())
                a['impl'] = versoes
                for v in versoes:
                    ficha = ler_json(d / v / 'impl.json', None) or ler_json(d / v / 'origem.json', None) or {}
                    if ficha.get('video') in a['videos']:
                        a['origens'][v] = ficha['video']
                    if ficha.get('agente'):
                        a['trabalhos'][v] = {k: ficha.get(k) for k in TRABALHO}
    return out


def novo_avanco() -> dict:
    return {'videos': [], 'impl': [], 'origens': {}, 'trabalhos': {}}


# o que o app mostra de impl.json (o contrato completo em docs/AGENTES.md); base/pedido: evolução (v1 → v1.1);
# entradas: as imagens tiradas do vídeo de onde a versão parte (ex.: a estática e a viva);
# estado: a aprovação do usuário (só o app escreve)
TRABALHO = ('agente', 'status', 'etapa', 'progresso', 'inicio', 'atualizado', 'fim', 'nota', 'erro', 'base', 'pedido', 'estado', 'entradas')


def ordem_versao(nome: str) -> tuple:
    """'v1' < 'v1.1' < 'v1.2' < 'v1.10' < 'v2' (os nomes que não seguem vN[.M] vão para o fim)."""
    m = re.fullmatch(r'v(\d+)(?:\.(\d+))?', nome)
    return (0, int(m.group(1)), int(m.group(2) or 0)) if m else (1, 0, 0, nome)


# ---------- fila (o Claude observa com tail -F) ----------

OUVINTE = RAIZ / '.ouvinte'


def ouvinte_vivo() -> bool:
    """O ouvir.sh do Claude toca este arquivo a cada 20 s enquanto observa a fila."""
    try:
        return (datetime.now().timestamp() - OUVINTE.stat().st_mtime) < 60
    except FileNotFoundError:
        return False


def enfileirar(slug: str, id_: str, acao: str) -> None:
    linha = json.dumps({'ts': agora(), 'projeto': slug, 'id': id_, 'acao': acao}, ensure_ascii=False)
    # trava num arquivo à parte: no Windows a trava é obrigatória e o tail -F do ouvinte não pode tropeçar nela
    with trava_arquivo(RAIZ / '.fila.lock'), open(FILA, 'a', encoding='utf-8', newline='\n') as f:
        f.write(linha + '\n')


# ---------- arquivos ----------
# sips no macOS (sem dependências); no resto, ffmpeg/ffprobe no PATH

def _ffmpeg(*args: str) -> None:
    if not shutil.which('ffmpeg'):
        raise RuntimeError('ffmpeg não encontrado no PATH (instale: winget install Gyan.FFmpeg)')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *args], capture_output=True, check=True)


def miniatura(origem: Path, destino: Path, lado: int = 640) -> None:
    """JPEG reduzido: o lado maior vira `lado`."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which('sips'):
        subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '82', '-Z', str(lado), str(origem),
                        '--out', str(destino)], capture_output=True, check=True)
        return
    _ffmpeg('-i', str(origem), '-vf', f'scale={lado}:{lado}:force_original_aspect_ratio=decrease', '-frames:v', '1',
            '-q:v', '3', str(destino))


def para_png(origem: Path, destino: Path) -> None:
    if shutil.which('sips'):
        subprocess.run(['sips', '-s', 'format', 'png', str(origem), '--out', str(destino)], capture_output=True, check=True)
        return
    _ffmpeg('-i', str(origem), '-frames:v', '1', str(destino))


def medidas(arquivo: Path) -> tuple[int, int] | None:
    if shutil.which('sips'):
        r = subprocess.run(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', str(arquivo)], capture_output=True, text=True)
        w = re.search(r'pixelWidth:\s*(\d+)', r.stdout)
        h = re.search(r'pixelHeight:\s*(\d+)', r.stdout)
        return (int(w.group(1)), int(h.group(1))) if w and h else None
    if not shutil.which('ffprobe'):
        return None
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                        '-of', 'csv=p=0:s=x', str(arquivo)], capture_output=True, text=True)
    m = re.match(r'(\d+)x(\d+)', r.stdout.strip())
    return (int(m.group(1)), int(m.group(2))) if m else None


def para_lixeira(slug: str, id_: str, junto: list[str] | None = None) -> None:
    """Nada sai do disco: o nó (e os de `junto`, num lote só) vão para projects/<slug>/lixeira/<id>-<ts>/<pasta>/.
    restaurar_da_lixeira(id) traz o lote inteiro de volta."""
    d = pasta(slug)
    destino = d / 'lixeira' / f'{id_}-{datetime.now():%Y%m%d%H%M%S%f}'
    for i in [id_, *(junto or [])]:
        for sub in SUBPASTAS:
            for f in (d / sub).glob(f'{i}.*'):
                (destino / sub).mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), destino / sub / f.name)


def galho(todos: list[dict], id_: str) -> list[str]:
    """Os descendentes de um nó na árvore de ideias (a mesma regra do app, layout.ts → arvore):
    brief → telas; tela → pedidos sem entrada de imagem (ou a referência que abre o galho); imagem → pedidos que saíram
    dela (1ª entrada que é imagem); pedido → suas imagens. Referências soltas usadas só por pedidos do galho vão junto."""
    por_id = {n['id']: n for n in todos}
    pai: dict[str, str] = {}
    brief = next((n['id'] for n in todos if n['tipo'] == 'brief'), None)
    for n in sorted(todos, key=lambda x: x['id']):
        if n['tipo'] == 'tela':
            pai.setdefault(n['id'], n.get('pai') or brief)
        elif n['tipo'] == 'pedido':
            ent = [por_id[e] for e in n.get('entradas') or [] if e in por_id]
            img = next((e for e in ent if e['tipo'] == 'imagem'), None)
            ref = next((e for e in ent if e['tipo'] == 'referencia'), None)
            if img:
                pai.setdefault(n['id'], img['id'])
            elif ref and not ref.get('pos'):
                pai.setdefault(ref['id'], n.get('tela') or ref.get('tela'))
                pai.setdefault(n['id'], ref['id'])
            elif n.get('tela'):
                pai.setdefault(n['id'], n['tela'])
        elif n['tipo'] in ('imagem', 'video') and n.get('pedido'):
            pai.setdefault(n['id'], n['pedido'])
    filhos: dict[str, list[str]] = {}
    for f, p in pai.items():
        filhos.setdefault(p, []).append(f)
    out: list[str] = []
    pilha = list(filhos.get(id_, []))
    while pilha:
        f = pilha.pop()
        if f not in out:
            out.append(f)
            pilha.extend(filhos.get(f, []))
    dentro = set(out) | {id_}
    for n in todos:  # referências soltas que só pedidos do galho usam
        if n['tipo'] == 'referencia' and n['id'] not in pai and n['id'] not in dentro:
            usos = [p['id'] for p in todos if p['tipo'] == 'pedido' and n['id'] in (p.get('entradas') or [])]
            if usos and all(u in dentro for u in usos):
                out.append(n['id'])
    return out


def restaurar_da_lixeira(slug: str, id_: str) -> dict:
    """Desfaz o último para_lixeira daquele nó (o ⌘Z do app). Devolve o nó."""
    d = pasta(slug)
    entradas = sorted((d / 'lixeira').glob(f'{id_}-*'))
    if not entradas:
        raise KeyError(f'{id_} não está na lixeira')
    origem = entradas[-1]
    for sub in SUBPASTAS:
        for f in (origem / sub).glob('*') if (origem / sub).exists() else []:
            (d / sub).mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), d / sub / f.name)
    shutil.rmtree(origem, ignore_errors=True)
    return ler_no(slug, id_)


def anexar_diario(slug: str, texto: str) -> None:
    arq = pasta(slug) / 'diario.md'
    atual = arq.read_text(encoding='utf-8') if arq.exists() else ''
    if f'\n## {date.today().isoformat()}' not in atual:
        atual = atual.rstrip() + f'\n\n## {date.today().isoformat()}\n'
    arq.write_text(atual.rstrip() + f'\n- {datetime.now():%H:%M} · {texto.strip()}\n', encoding='utf-8')
