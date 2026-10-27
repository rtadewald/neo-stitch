# /// script
# requires-python = ">=3.11"
# ///
"""Implementações (vídeo → HTML) feitas por qualquer agente: Claude Code, Codex, OpenCode… Spec: docs/AGENTES.md.

    uv run ferramentas/impl.py iniciar <VÍDEO> --agente "Codex 5.6" [--nota "…"]   reserva impl/<IMAGEM>/vN/ e diz onde trabalhar
    uv run ferramentas/impl.py evoluir <IMAGEM/vN> --agente "…" --pedido "…"       uma alteração pedida: copia para a próxima vN.M
    uv run ferramentas/impl.py etapa <IMAGEM/vN> "o que está fazendo" [--progresso 0.4]
    uv run ferramentas/impl.py vivo <IMAGEM/vN>                                   só renova o "atualizado" (sinal de vida)
    uv run ferramentas/impl.py pronto <IMAGEM/vN> [--nota "…"]                    exige index.html na pasta
    uv run ferramentas/impl.py erro <IMAGEM/vN> "motivo"
    uv run ferramentas/impl.py abandonar <IMAGEM/vN> [--nota "…"]
    uv run ferramentas/impl.py asset <IMAGEM/vN> <arquivo.png> --nome "…" [--nota "…"] [--custo 0.04]
                                                                                   registra uma imagem gerada no trabalho (placa de fundo,
                                                                                   personagem limpo…) como nó de imagem saindo do vídeo
    uv run ferramentas/impl.py asset <IMAGEM/vN> <modelo.glb> --nome "…" --de <CÓD. da imagem> --capa <render.png>
                                  [--giro 0] [--custo 0.40] [--estado aprovada]    um modelo 3D (imagem → 3D) sai da imagem que o gerou
    uv run ferramentas/impl.py ver [slug]                                          quem está trabalhando em quê

O contrato é o arquivo impl/<IMAGEM>/vN/impl.json (o app lê e mostra o agente, a etapa e o progresso no cartão do site).
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import base as B  # noqa: E402

STATUS = ('trabalhando', 'pronto', 'erro', 'abandonado')
PARADO_MIN = 15  # sem atualizar há mais que isso, trabalhando = "parado?" no app


def achar_versao(cod: str, ficha: bool = True) -> tuple[str, Path]:
    """'JAR-043/v4' (ou 'JAR-043/v4.1') → (slug, pasta da versão)."""
    img, _, v = cod.partition('/')
    if not v:
        sys.exit(f'use IMAGEM/vN (ex.: JAR-043/v4), não {cod!r}')
    slug, img = B.resolver_codigo(img)
    d = B.pasta(slug) / 'impl' / img / v
    if not d.is_dir():
        sys.exit(f'{cod}: a pasta não existe')
    if ficha and not (d / 'impl.json').exists():
        sys.exit(f'{cod}: sem impl.json (comece com `impl.py iniciar <VÍDEO> --agente …`)')
    return slug, d


def mudar(cod: str, **campos) -> dict:
    slug, d = achar_versao(cod)
    with B.travado(slug):
        f = d / 'impl.json'
        dados = B.ler_json(f, {})
        dados.update({k: v for k, v in campos.items() if v is not None}, atualizado=B.agora())
        B.gravar_json(f, dados)
    return dados


def cmd_iniciar(a):
    slug, vid = B.resolver_codigo(a.video)
    video = B.ler_no(slug, vid)
    if video['tipo'] != 'video' or not video.get('arquivo'):
        sys.exit(f'{vid} não é um vídeo pronto')
    pedido = B.ler_no(slug, video['pedido'])
    img_id = (pedido.get('entradas') or [None])[0]
    img = B.ler_no(slug, img_id)
    agente = ' '.join(a.agente.split())[:24]
    if not agente:
        sys.exit('--agente é obrigatório (nome curto: "Codex 5.6", "Claude Opus 5.5", "OpenCode")')
    raiz = B.pasta(slug) / 'impl' / img_id
    with B.travado(slug):  # a reserva da vN é atômica: dois agentes ao mesmo tempo ganham versões diferentes
        raiz.mkdir(parents=True, exist_ok=True)
        n = max([int(p.name[1:]) for p in raiz.glob('v*') if p.name[1:].isdigit()] or [0]) + 1
        d = raiz / f'v{n}'
        (d / 'analise').mkdir(parents=True)
        shutil.copy2(B.pasta(slug) / img['arquivo'], d / 'reference.png')
        shutil.copy2(B.pasta(slug) / video['arquivo'], d / 'analise' / 'video-ref.mp4')
        agora = B.agora()
        B.gravar_json(d / 'impl.json', {
            'agente': agente, 'video': vid, 'imagem': img_id, 'versao': f'v{n}', 'status': 'trabalhando',
            'etapa': 'começando', 'progresso': 0, 'inicio': agora, 'atualizado': agora, 'nota': a.nota or '',
        })
    cod = f'{img_id}/v{n}'
    print(f"""{cod} reservada para {agente}.
  pasta:      {d}
  imagem:     {d / 'reference.png'}  (o conteúdo da tela: textos, layout)
  vídeo:      {d / 'analise' / 'video-ref.mp4'}  (o movimento: inspiração, não especificação)
  pedido do vídeo: {pedido.get('intencao') or '-'}
  abrir:      http://localhost:8730/projects/{slug}/impl/{img_id}/v{n}/index.html
A cada etapa: uv run ferramentas/impl.py etapa {cod} "…" --progresso 0.3   ·   no fim: uv run ferramentas/impl.py pronto {cod}""")


def cmd_evoluir(a):
    """Uma alteração pedida numa versão vira a próxima vN.M (v1 → v1.1 → v1.2), cópia da base, que segue intacta."""
    slug, base = achar_versao(a.versao, ficha=False)
    m = re.fullmatch(r'v(\d+)(?:\.\d+)?', base.name)
    if not m:
        sys.exit(f'{a.versao}: o nome da versão precisa ser vN ou vN.M')
    agente = ' '.join(a.agente.split())[:24]
    antiga = B.ler_json(base / 'impl.json', None) or B.ler_json(base / 'origem.json', None) or {}
    with B.travado(slug):
        livres = [int(p.name.split('.')[1]) for p in base.parent.glob(f'v{m.group(1)}.*') if p.name.split('.')[1].isdigit()]
        nova = base.parent / f'v{m.group(1)}.{max(livres or [0]) + 1}'
        shutil.copytree(base, nova, ignore=shutil.ignore_patterns('verificacao', 'impl.json', 'origem.json', '.DS_Store'))
        agora = B.agora()
        B.gravar_json(nova / 'impl.json', {
            'agente': agente, 'video': antiga.get('video'), 'imagem': base.parent.name, 'versao': nova.name, 'base': base.name,
            'pedido': a.pedido, 'status': 'trabalhando', 'etapa': 'começando', 'progresso': 0, 'inicio': agora, 'atualizado': agora,
            'nota': '',
        })
    cod = f'{base.parent.name}/{nova.name}'
    print(f"""{cod} (evolução da {base.name}) reservada para {agente}.
  pasta:   {nova}   (cópia da {base.name}, que não muda)
  pedido:  {a.pedido}
  abrir:   http://localhost:8730/projects/{slug}/impl/{base.parent.name}/{nova.name}/index.html
Trabalhe só nela; no fim: uv run ferramentas/impl.py pronto {cod} --nota '<o que mudou>'""")


def cmd_etapa(a):
    if a.progresso is not None and not 0 <= a.progresso <= 1:
        sys.exit('--progresso vai de 0 a 1')
    d = mudar(a.versao, etapa=a.texto, progresso=a.progresso, status='trabalhando')
    print(f'{a.versao}: {d["etapa"]} ({round((d.get("progresso") or 0) * 100)}%)')


def cmd_vivo(a):
    mudar(a.versao)
    print('ok')


def cmd_pronto(a):
    _, d = achar_versao(a.versao)
    if not (d / 'index.html').exists():
        sys.exit(f'{a.versao}: falta index.html em {d}')
    mudar(a.versao, status='pronto', etapa='pronto', progresso=1, nota=a.nota, fim=B.agora())
    print(f'{a.versao} pronto')


def cmd_erro(a):
    mudar(a.versao, status='erro', erro=a.motivo)
    print('ok')


def cmd_abandonar(a):
    mudar(a.versao, status='abandonado', nota=a.nota)
    print('ok')


def cmd_asset(a):
    """Uma imagem gerada durante a implementação é um asset do projeto: vira nó de imagem num pedido (um por versão) que sai
    do vídeo da versão, para aparecer no canvas e servir de base para iterar."""
    slug, d = achar_versao(a.versao)
    origem = Path(a.arquivo)
    if not origem.is_file():
        sys.exit(f'arquivo não encontrado: {origem}')
    if origem.suffix.lower() == '.glb':
        return asset_modelo(a, slug, d, origem)
    pasta = B.pasta(slug)
    with B.travado(slug):
        ficha = B.ler_json(d / 'impl.json', {})
        video = ficha.get('video')
        if not video:
            sys.exit(f'{a.versao}: o impl.json não diz o vídeo')
        pid = ficha.get('assets_pedido')
        if not pid or not (pasta / 'nodes' / f'{pid}.json').exists():
            tela = B.ler_no(slug, B.ler_no(slug, video)['pedido']).get('tela')
            ped = B.novo_no(slug, 'pedido', tela=tela, entradas=[video], literal=True, status='concluido', quantidade=0,
                            intencao=f'Assets da implementação {a.versao} ({ficha.get("agente", "agente")}): imagens geradas no trabalho.')
            pid = ped['id']
            ficha['assets_pedido'] = pid
            B.gravar_json(d / 'impl.json', ficha)
        img = B.novo_no(slug, 'imagem', pedido=pid, nome=a.nome, prompt=a.nota or a.nome, origem=f'{a.versao} · {origem.name}',
                        custo=a.custo, modelo='asset')
        arq = pasta / 'images' / f"{img['id']}.png"
        if origem.suffix.lower() == '.png':
            shutil.copyfile(origem, arq)
        else:
            B.para_png(origem, arq)
        B.miniatura(arq, pasta / 'thumbs' / f"{img['id']}.jpg")
        larg, alt = B.medidas(arq) or (None, None)
        img.update({'arquivo': f"images/{img['id']}.png", 'thumb': f"thumbs/{img['id']}.jpg", 'largura': larg, 'altura': alt})
        B.gravar_no(slug, img)
        ped = B.ler_no(slug, pid)
        ped['saidas'] = ped.get('saidas', []) + [img['id']]
        ped['quantidade'] = len(ped['saidas'])
        ped['custo'] = round((ped.get('custo') or 0) + (a.custo or 0), 4)
        ped['concluido_em'] = B.agora()
        B.gravar_no(slug, ped)
    print(f"{img['id']} ({a.nome}) registrada no pedido {pid}, saindo do vídeo {video}")


def asset_modelo(a, slug: str, d: Path, origem: Path) -> None:
    """Um modelo 3D gerado de uma imagem: nó "modelo" num pedido (um por imagem de origem) que sai dessa imagem.
    A capa é um render no ângulo do quadro; `giro` é o quanto girar o modelo para ficar de frente no visualizador."""
    if not a.de or not a.capa:
        sys.exit('um modelo 3D precisa de --de <imagem de origem> e --capa <render.png>')
    pasta = B.pasta(slug)
    with B.travado(slug):
        fonte = B.ler_no(slug, a.de)
        ficha = B.ler_json(d / 'impl.json', {})
        pedidos = ficha.setdefault('pedidos_modelo', {})
        pid = pedidos.get(a.de)
        if not pid or not (pasta / 'nodes' / f'{pid}.json').exists():
            tela = fonte.get('tela') or B.ler_no(slug, fonte['pedido']).get('tela')
            ped = B.novo_no(slug, 'pedido', tela=tela, entradas=[a.de], midia='3d', literal=True, status='concluido', quantidade=0,
                            intencao=f'Modelos 3D (imagem → 3D) da imagem {a.de}, para a implementação {a.versao}.')
            pid = pedidos[a.de] = ped['id']
            B.gravar_json(d / 'impl.json', ficha)
        no = B.novo_no(slug, 'modelo', pedido=pid, nome=a.nome, prompt=a.nota or a.nome, origem=f'{a.versao} · {origem.name}',
                       custo=a.custo, giro=a.giro or 0, modelo='image-to-3d')
        (pasta / 'models').mkdir(exist_ok=True)
        shutil.copyfile(origem, pasta / 'models' / f"{no['id']}.glb")
        B.miniatura(Path(a.capa), pasta / 'thumbs' / f"{no['id']}.jpg")
        larg, alt = B.medidas(pasta / 'thumbs' / f"{no['id']}.jpg") or (None, None)
        no.update({'arquivo': f"models/{no['id']}.glb", 'thumb': f"thumbs/{no['id']}.jpg", 'largura': larg, 'altura': alt,
                   'estado': a.estado or 'neutra'})
        B.gravar_no(slug, no)
        ped = B.ler_no(slug, pid)
        ped['saidas'] = ped.get('saidas', []) + [no['id']]
        ped['quantidade'] = len(ped['saidas'])
        ped['custo'] = round((ped.get('custo') or 0) + (a.custo or 0), 4)
        ped['concluido_em'] = B.agora()
        B.gravar_no(slug, ped)
    print(f"{no['id']} ({a.nome}) registrado no pedido {pid}, saindo da imagem {a.de}")


def cmd_ver(a):
    for slug in [a.slug] if a.slug else B.projetos():
        for f in sorted((B.pasta(slug) / 'impl').glob('*/*/impl.json')):
            d = B.ler_json(f, {})
            parado = ''
            if d.get('status') == 'trabalhando':
                idade = (datetime.now() - datetime.fromisoformat(d['atualizado'])).total_seconds() / 60
                parado = f' · parado há {idade:.0f} min?' if idade > PARADO_MIN else ''
            print(f'{f.parent.parent.name}/{f.parent.name:<4} {d.get("agente", "?"):<18} {d.get("status", "?"):<11} '
                  f'{round((d.get("progresso") or 0) * 100):>3}%  {d.get("etapa", "")}{parado}  ← {d.get("video", "-")}')


def main():
    ap = argparse.ArgumentParser(description='Implementações vídeo → HTML por qualquer agente (spec: docs/AGENTES.md)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('iniciar'); s.add_argument('video'); s.add_argument('--agente', required=True); s.add_argument('--nota')
    s.set_defaults(fn=cmd_iniciar)
    s = sub.add_parser('evoluir'); s.add_argument('versao'); s.add_argument('--agente', required=True); s.add_argument('--pedido', required=True)
    s.set_defaults(fn=cmd_evoluir)
    s = sub.add_parser('etapa'); s.add_argument('versao'); s.add_argument('texto'); s.add_argument('--progresso', type=float)
    s.set_defaults(fn=cmd_etapa)
    s = sub.add_parser('vivo'); s.add_argument('versao'); s.set_defaults(fn=cmd_vivo)
    s = sub.add_parser('pronto'); s.add_argument('versao'); s.add_argument('--nota'); s.set_defaults(fn=cmd_pronto)
    s = sub.add_parser('erro'); s.add_argument('versao'); s.add_argument('motivo'); s.set_defaults(fn=cmd_erro)
    s = sub.add_parser('abandonar'); s.add_argument('versao'); s.add_argument('--nota'); s.set_defaults(fn=cmd_abandonar)
    s = sub.add_parser('asset'); s.add_argument('versao'); s.add_argument('arquivo'); s.add_argument('--nome', required=True)
    s.add_argument('--nota'); s.add_argument('--custo', type=float); s.add_argument('--de', help='modelo 3D: a imagem de origem')
    s.add_argument('--capa', help='modelo 3D: um render (png)'); s.add_argument('--giro', type=float, help='modelo 3D: graus para ficar de frente')
    s.add_argument('--estado', choices=['neutra', 'aprovada', 'descartada']); s.set_defaults(fn=cmd_asset)
    s = sub.add_parser('ver'); s.add_argument('slug', nargs='?'); s.set_defaults(fn=cmd_ver)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
