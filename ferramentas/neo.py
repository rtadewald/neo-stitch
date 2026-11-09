# /// script
# requires-python = ">=3.11"
# ///
"""O lado do Claude no canvas: ler a fila, ler o contexto de um nó, responder, criar e marcar.

    uv run ferramentas/neo.py projetos
    uv run ferramentas/neo.py novo "Nome" [--tipo site|app|dashboard|webapp] [--prefixo ABC] [--descricao "…"]
    uv run ferramentas/neo.py pendentes                       pedidos/briefs enviados (todos os projetos)
    uv run ferramentas/neo.py ver <slug|CÓDIGO>                projeto (árvore compacta) ou nó com todo o contexto
    uv run ferramentas/neo.py pegar <CÓDIGO>                   marca como "trabalhando" (o canvas mostra o loader)
    uv run ferramentas/neo.py direcoes <BRIEF> --json '[{"nome": "…", "tese": "…"}]'
    uv run ferramentas/neo.py tela <slug> "Nome"
    uv run ferramentas/neo.py pedido <slug> [--tela COD] [--entradas A,B] [--intencao "…"] [--quantidade N] [--enviar]
                                       [--midia video --modelos a,b --duracao 6 --resolucao 720p]   (pedido de vídeo de uma imagem)
    uv run ferramentas/neo.py comentar <CÓDIGO> "texto" [--pin x,y]      (x,y de 0 a 1 sobre a imagem)
    uv run ferramentas/neo.py estado <CÓDIGO…> neutra|aprovada|descartada
    uv run ferramentas/neo.py erro <CÓDIGO> "mensagem"         devolve o pedido com erro (volta a ser editável)
    uv run ferramentas/neo.py brief <slug> [--arquivo novo.md]  mostra (ou troca) o brief.md
    uv run ferramentas/neo.py ds <slug> <pasta> --nome "…" --de JCO-011/v1,JCO-012/v1 --capa capa.png [--nota "…"] [--custo 0]
                                       registra um design system pronto: copia a pasta e cria o cartão (categoria "Design Systems")

Gerar imagens: ferramentas/gerar.py · vídeos: ferramentas/gerar_video.py. Contrato dos nós: .claude/skills/neo-stitch/modelo.md.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import base as B  # noqa: E402


def cmd_ds(a):
    """Um design system pronto (uma pasta com design-system.html) vira um cartão: a pasta vai para ds/<código>/ e um pedido
    concluído liga o cartão às páginas de onde ele saiu."""
    origem = Path(a.pasta).expanduser().resolve()
    capa = Path(a.capa).expanduser().resolve()
    if not (origem / 'design-system.html').is_file():
        sys.exit(f'{origem}: não tem design-system.html')
    if not capa.is_file():
        sys.exit(f'{capa}: a capa não existe')
    de = [x.strip() for x in a.de.split(',') if x.strip()]
    pasta = B.pasta(a.slug)
    for e in de:
        ok = (pasta / 'impl' / e).is_dir() if '/' in e else B.caminho_no(a.slug, e).exists()
        if not ok:
            sys.exit(f'{e}: não existe no projeto {a.slug}')
    if any(n['tipo'] == 'ds' and n.get('origem') == str(origem) for n in B.nos(a.slug)):
        sys.exit(f'{origem}: já registrado')
    # a cópia vem antes da trava (o app escreve ao mesmo tempo); no APFS é um clone, sem gastar disco
    (pasta / 'ds').mkdir(exist_ok=True)
    tmp = pasta / 'ds' / f'.novo-{os.getpid()}'
    if subprocess.run(['cp', '-cR', str(origem), str(tmp)], capture_output=True).returncode:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.copytree(origem, tmp)
    with B.travado(a.slug):
        todos = {n['id']: n for n in B.nos(a.slug)}
        n = todos[de[0].split('/')[0]]    # uma página IMG/vN herda a tela da imagem
        tela = n.get('tela') or todos.get(n.get('pedido'), {}).get('tela')
        ped = B.novo_no(a.slug, 'pedido', tela=tela, entradas=de, literal=True, status='concluido', quantidade=1, midia='ds',
                        intencao=a.nota or f'Design system {a.nome}', concluido_em=B.agora(), custo=a.custo)
        no = B.novo_no(a.slug, 'ds', pedido=ped['id'], nome=a.nome, prompt=a.nota or a.nome, origem=str(origem), custo=a.custo, estado='neutra')
        cod = no['id']
        tmp.rename(pasta / 'ds' / cod)
        arq = pasta / 'ds' / cod / f'capa{capa.suffix.lower()}'
        shutil.copyfile(capa, arq)
        B.miniatura(arq, pasta / 'thumbs' / f'{cod}.jpg')
        larg, alt = B.medidas(arq) or (None, None)
        no.update({'pagina': f'ds/{cod}/design-system.html', 'arquivo': f'ds/{cod}/{arq.name}', 'thumb': f'thumbs/{cod}.jpg', 'largura': larg, 'altura': alt})
        B.gravar_no(a.slug, no)
        ped['saidas'] = [cod]
        B.gravar_no(a.slug, ped)
    print(f'{cod} ({a.nome}) registrado no pedido {ped["id"]}, saindo de {", ".join(de)}')


def cmd_projetos(a):
    for s in B.projetos():
        p = B.ler_projeto(s)
        lista = B.nos(s)
        c = B.custos(s, lista)
        n = sum(1 for x in lista if x['tipo'] == 'imagem')
        print(f'{p["prefixo"]:<5} {s:<24} {p["nome"]:<28} {p["tipo"]:<10} {n:>4} imgs  ${c["total"]:.2f} (hoje ${c["hoje"]:.2f})')


def cmd_novo(a):
    p = B.criar_projeto(a.nome, a.tipo, a.descricao or '', a.prefixo)
    print(f'Projeto {p["slug"]} ({p["prefixo"]}) criado. Brief: {p["prefixo"]}-001 · Tela: {p["prefixo"]}-002')


def cmd_pendentes(a):
    achou = False
    for s in B.projetos():
        for n in B.nos(s):
            if n['tipo'] in ('pedido', 'brief') and n.get('status') in ('enviado', 'trabalhando'):
                achou = True
                print(f'{n["id"]:<9} {n["tipo"]:<7} {n["status"]:<11} {s:<20} {(n.get("intencao") or n.get("titulo") or "")[:70]}')
    if not achou:
        print('Nada pendente.')


def linha(n: dict) -> str:
    t = n['tipo']
    if t in ('imagem', 'video', 'ds'):
        extra = f'{n.get("estado")}{" ⏳" if n.get("gerando") else ""}{" ✗" if n.get("erro") else ""} {n.get("nome") or ""}'
    elif t == 'pedido':
        midia = '🎬 ' if n.get('midia') == 'video' else ''
        extra = f'[{n.get("status")}] {midia}{(n.get("intencao") or "")[:60]!r} ← {",".join(n.get("entradas") or []) or "-"}'
    elif t == 'brief':
        extra = f'[{n.get("status")}] {n.get("titulo", "")}'
    else:
        extra = n.get('titulo', '')
    com = f' 💬{len(n["comentarios"])}' if n.get('comentarios') else ''
    return f'{n["id"]} {n["tipo"]}: {extra}{com}'


def cmd_ver(a):
    if B.CODIGO.search(a.alvo.upper()):
        slug, id_ = B.resolver_codigo(a.alvo)
        return ver_no(slug, id_)
    slug = a.alvo
    p = B.ler_projeto(slug)
    lista = B.nos(slug)
    por_id = {n['id']: n for n in lista}
    print(f'# {p["nome"]} ({p["prefixo"]}, {p["tipo"]}) · padrões {p["padroes"]} · custos {B.custos(slug, lista)}')
    filhos: dict[str, list] = {}
    for n in lista:
        pai = n.get('pai') if n['tipo'] in ('tela', 'brief') else n.get('tela') if n['tipo'] in ('pedido', 'referencia') else n.get('pedido')
        filhos.setdefault(pai, []).append(n)

    def arvore(id_, nivel):
        for f in filhos.get(id_, []):
            print('  ' * nivel + linha(f))
            arvore(f['id'], nivel + 1)
    arvore(None, 0)
    soltos = [n for n in lista if n['tipo'] in ('pedido', 'referencia', 'imagem', 'video', 'ds')
              and n.get('pedido' if n['tipo'] in ('imagem', 'video', 'ds') else 'tela') not in por_id]
    for n in soltos:
        print('(solto) ' + linha(n))


def ver_no(slug: str, id_: str):
    """Tudo o que o Claude precisa para atender um nó: o nó, as entradas (arquivo, prompt, comentários), a tela, o brief."""
    d = B.pasta(slug)
    no = B.ler_no(slug, id_)
    todos = {n['id']: n for n in B.nos(slug)}
    print(json.dumps(no, ensure_ascii=False, indent=1))
    if no['tipo'] == 'pedido':
        tela = todos.get(no.get('tela'))
        print(f'\nTela: {tela and tela["titulo"]} ({no.get("tela")})')
        for e in no.get('entradas', []):
            en = todos.get(e, {'tipo': 'página'} if '/' in e else {})
            print(f'\nENTRADA {e} ({en.get("tipo")}) {en.get("nome") or en.get("titulo") or ""} · estado {en.get("estado", "-")}')
            if f := B.arquivo_entrada(slug, e):
                print(f'  arquivo: {f}')
            if en.get('prompt'):
                print(f'  prompt que a gerou: {en["prompt"]}')
            for c in en.get('comentarios', []):
                pin = f' @({c["pin"]["x"]:.2f},{c["pin"]["y"]:.2f})' if c.get('pin') else ''
                print(f'  💬 {c["autor"]}{pin}: {c["texto"]}')
    if no['tipo'] in ('pedido', 'brief'):
        print(f'\nBrief ({d / "brief.md"}):\n' + (d / 'brief.md').read_text(encoding='utf-8')[:3000])
    if no['tipo'] in ('imagem', 'video') and no.get('arquivo'):
        print(f'\narquivo: {d / no["arquivo"]}')
    if no['tipo'] == 'ds':
        print(f'\ncatálogo: {d / no["pagina"]}\ncapa: {d / no["arquivo"]}')


def alterar(slug: str, id_: str, **campos) -> dict:
    with B.travado(slug):
        no = B.ler_no(slug, id_)
        no.update(campos)
        return B.gravar_no(slug, no)


def cmd_pegar(a):
    slug, id_ = B.resolver_codigo(a.codigo)
    alterar(slug, id_, status='trabalhando')
    print(f'{id_} trabalhando')


def cmd_direcoes(a):
    slug, id_ = B.resolver_codigo(a.codigo)
    dirs = json.loads(B.json_ou_arquivo(a.json))
    dirs = [{'nome': d['nome'], 'tese': d.get('tese', ''), 'ativa': True} for d in dirs]
    alterar(slug, id_, direcoes=dirs, status='proposto')
    print(f'{id_}: {len(dirs)} direções propostas')


def cmd_tela(a):
    with B.travado(a.slug):
        brief = next(n for n in B.nos(a.slug) if n['tipo'] == 'brief')
        no = B.novo_no(a.slug, 'tela', titulo=a.nome, pai=brief['id'])
    print(no['id'])


def cmd_pedido(a):
    with B.travado(a.slug):
        todos = {n['id']: n for n in B.nos(a.slug)}
        entradas = [e.strip() for e in (a.entradas or '').split(',') if e.strip()]
        tela = a.tela
        if not tela:
            for e in entradas:
                n = todos[e.split('/')[0]]    # uma página IMG/vN herda a tela da imagem
                tela = n.get('tela') or todos.get(n.get('pedido'), {}).get('tela')
                if tela:
                    break
        tela = tela or next((n['id'] for n in todos.values() if n['tipo'] == 'tela'), None)
        campos = {'tela': tela, 'entradas': entradas, 'intencao': a.intencao or ''}
        if a.quantidade:
            campos['quantidade'] = a.quantidade
        if a.midia == 'video':   # vídeo de uma imagem: a 1ª entrada é o quadro inicial; um vídeo por modelo
            campos['midia'] = 'video'
            if a.modelos:
                campos['modelos'] = [m.strip() for m in a.modelos.split(',') if m.strip()]
            if a.duracao:
                campos['duracao'] = a.duracao
            if a.resolucao:
                campos['resolucao'] = a.resolucao
        if a.enviar:
            campos.update(status='enviado', enviado_em=B.agora())
        no = B.novo_no(a.slug, 'pedido', **campos)
    if a.enviar:
        B.enfileirar(a.slug, no['id'], 'video' if a.midia == 'video' else 'gerar')
    print(no['id'])


def cmd_comentar(a):
    slug, id_ = B.resolver_codigo(a.codigo)
    pin = None
    if a.pin:
        x, y = a.pin.split(',')
        pin = {'x': float(x), 'y': float(y)}
    with B.travado(slug):
        B.comentar(slug, id_, 'claude', a.texto, pin)
    print('ok')


def cmd_estado(a):
    *codigos, estado = a.args
    if estado not in B.ESTADOS:
        sys.exit(f'estado inválido: {estado}')
    for c in codigos:
        slug, id_ = B.resolver_codigo(c)
        alterar(slug, id_, estado=estado)
    print('ok')


def cmd_erro(a):
    slug, id_ = B.resolver_codigo(a.codigo)
    alterar(slug, id_, status='erro', erro=a.mensagem)
    print('ok')


def cmd_brief(a):
    arq = B.pasta(a.slug) / 'brief.md'
    if a.arquivo:
        with B.travado(a.slug):
            arq.write_text(Path(a.arquivo).read_text(encoding='utf-8'), encoding='utf-8')
        print('ok')
    else:
        print(arq.read_text(encoding='utf-8'))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('projetos').set_defaults(fn=cmd_projetos)
    s = sub.add_parser('novo'); s.add_argument('nome'); s.add_argument('--tipo', default='webapp')
    s.add_argument('--prefixo'); s.add_argument('--descricao'); s.set_defaults(fn=cmd_novo)
    sub.add_parser('pendentes').set_defaults(fn=cmd_pendentes)
    s = sub.add_parser('ver'); s.add_argument('alvo'); s.set_defaults(fn=cmd_ver)
    s = sub.add_parser('pegar'); s.add_argument('codigo'); s.set_defaults(fn=cmd_pegar)
    s = sub.add_parser('direcoes'); s.add_argument('codigo'); s.add_argument('--json', required=True); s.set_defaults(fn=cmd_direcoes)
    s = sub.add_parser('tela'); s.add_argument('slug'); s.add_argument('nome'); s.set_defaults(fn=cmd_tela)
    s = sub.add_parser('pedido'); s.add_argument('slug'); s.add_argument('--tela'); s.add_argument('--entradas')
    s.add_argument('--intencao'); s.add_argument('--quantidade', type=int); s.add_argument('--enviar', action='store_true')
    s.add_argument('--midia', choices=['imagem', 'video'], default='imagem'); s.add_argument('--modelos')
    s.add_argument('--duracao', type=int); s.add_argument('--resolucao')
    s.set_defaults(fn=cmd_pedido)
    s = sub.add_parser('comentar'); s.add_argument('codigo'); s.add_argument('texto'); s.add_argument('--pin')
    s.set_defaults(fn=cmd_comentar)
    s = sub.add_parser('estado'); s.add_argument('args', nargs='+'); s.set_defaults(fn=cmd_estado)
    s = sub.add_parser('erro'); s.add_argument('codigo'); s.add_argument('mensagem'); s.set_defaults(fn=cmd_erro)
    s = sub.add_parser('brief'); s.add_argument('slug'); s.add_argument('--arquivo'); s.set_defaults(fn=cmd_brief)
    s = sub.add_parser('ds'); s.add_argument('slug'); s.add_argument('pasta'); s.add_argument('--nome', required=True)
    s.add_argument('--de', required=True); s.add_argument('--capa', required=True); s.add_argument('--nota')
    s.add_argument('--custo', type=float, default=0.0); s.set_defaults(fn=cmd_ds)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
