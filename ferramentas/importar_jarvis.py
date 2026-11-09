# /// script
# requires-python = ">=3.11"
# ///
"""Importa os protótipos do JarvisOS (20-jarvisOS/prototipos) como o projeto "JarvisOS" (prefixo JAR).

    uv run ferramentas/importar_jarvis.py [--de <pasta prototipos>] [--refazer]

A origem não é alterada (tudo é copiado). Os prompts vêm de ferramentas/dados/jarvis_prompts.json, recuperados da
transcrição da sessão que gerou as imagens (nunca inventados). Linhagem:
- idle (10 direções) → idle-v2-stark (a partir de 02-stark-hud) · idle-v3-eve (referência EVE)
- pinterest/NN-pin-*: referência + hint → 5 variações · neuronio / neuronio-02: layout aprovado + referência do neurônio
- _descartados/ → descartada · aprovados/ → aprovada (casando pelo conteúdo, md5)
Tudo fica `legado: true` (o custo vem dos .log e não conta no "hoje").
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import base as B  # noqa: E402

ORIGEM = Path('/Users/rtadewald/Projetos Locais/Tools/20-jarvisOS/prototipos')
PROMPTS = Path(__file__).parent / 'dados' / 'jarvis_prompts.json'
SLUG = 'jarvisos'

BRIEF = """# JarvisOS

O **JARVIS OS** é a tela "idle" de um orquestrador por voz que comanda vários agentes do Claude Code.

- **Centro:** um núcleo de IA vivo (o orquestrador) que "respira".
- **Arco de agentes:** 12 nós orbitando, cada um uma sessão de agente com rótulo (Agente Principal, Reels Editor, VSL Isca, Ad, Agendador, Storytelling, Skills Tip, Landing FIA, Dev, Copywriter, Pesquisa, Thumbs). Os ativos brilham e pulsam.
- **Esquerda:** telemetria discreta (CPU, memória, rede, fila de tarefas "3 ativas / 9 em espera").
- **Direita:** um painel de chat compacto do JARVIS com campo "Fale ou digite…" e microfone.
- **Topo:** wordmark "JARVIS" à esquerda e hora (21:47) à direita.
- Pouquíssimo texto: sem saudações nem frases de status.

Formato: desktop 16:9, tela cheia, sem moldura de navegador.

> Importado de `20-jarvisOS/prototipos` (2026-10-22). Os prompts originais foram recuperados da sessão que gerou as imagens.
"""


def md5(arq: Path) -> str:
    return hashlib.md5(arq.read_bytes()).hexdigest()


def quando(arq: Path) -> str:
    st = arq.stat()
    return datetime.fromtimestamp(getattr(st, 'st_birthtime', st.st_mtime)).isoformat(timespec='seconds')


def nome_legivel(stem: str) -> str:
    s = re.sub(r'^(\d+[a-z]?-|v\d+[a-z]?-|[a-e]-)', '', stem)
    return s.replace('-', ' ').strip()


def custo_do_log(arq_png: Path) -> float | None:
    log = arq_png.with_suffix('.log')
    if log.exists():
        m = re.search(r'usage\.cost\):\s*\$([\d.]+)', log.read_text(encoding='utf-8', errors='ignore'))
        if m:
            return float(m.group(1))
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--de', default=str(ORIGEM))
    ap.add_argument('--refazer', action='store_true', help='apaga o projeto jarvisos já importado e importa de novo')
    a = ap.parse_args()
    origem = Path(a.de)
    prompts: dict = json.loads(PROMPTS.read_text(encoding='utf-8'))

    pasta = B.PROJETOS / SLUG
    if pasta.exists():
        if not a.refazer:
            sys.exit(f'{pasta} já existe (use --refazer para importar de novo).')
        shutil.rmtree(pasta)

    B.criar_projeto('JarvisOS', 'webapp', prefixo='JAR', tela='Idle', slug=SLUG)
    (pasta / 'brief.md').write_text(BRIEF, encoding='utf-8')
    nos = {n['tipo']: n for n in B.nos(SLUG)}
    tela_id = nos['tela']['id']

    # hash → arquivo atual, para achar onde cada imagem gerada está hoje (algumas foram movidas à mão)
    por_hash: dict[str, list[Path]] = defaultdict(list)
    for f in origem.rglob('*.png'):
        por_hash[md5(f)].append(f)

    criados_por_hash: dict[str, str] = {}   # md5 → id do nó (imagem ou referência)

    def copiar_arquivo(no_id: str, arq: Path, sub: str) -> dict:
        destino = pasta / sub / f'{no_id}{arq.suffix.lower()}'
        shutil.copy2(arq, destino)
        B.miniatura(destino, pasta / 'thumbs' / f'{no_id}.jpg')
        w, h = B.medidas(destino) or (None, None)
        return {'arquivo': f'{sub}/{destino.name}', 'thumb': f'thumbs/{no_id}.jpg', 'largura': w, 'altura': h}

    def referencia(arq: Path, titulo: str) -> str:
        hsh = md5(arq)
        if hsh in criados_por_hash:
            return criados_por_hash[hsh]
        with B.travado(SLUG):
            no = B.novo_no(SLUG, 'referencia', titulo=titulo, tela=tela_id, legado=True,
                           origem=str(arq.relative_to(origem)))
            no.update(copiar_arquivo(no['id'], arq, 'refs'))
            no['criado'] = quando(arq)
            B.gravar_no(SLUG, no)
        criados_por_hash[hsh] = no['id']
        return no['id']

    def entrada(caminho_rel: str) -> str:
        """Uma entrada de pedido: uma imagem já importada (pelo conteúdo) ou uma referência nova."""
        arq = origem / caminho_rel
        if arq.exists() and md5(arq) in criados_por_hash:
            return criados_por_hash[md5(arq)]
        titulo = 'Pinterest' if 'pinterest/' in caminho_rel else nome_legivel(arq.stem.replace('referencia', 'referência').replace('ref-', ''))
        return referencia(arq, titulo)

    def pedido(chaves: list[str], intencao: str) -> str | None:
        chaves = [k for k in chaves if k in prompts]
        if not chaves:
            return None
        p0 = prompts[chaves[0]]
        ents = [entrada(i) for i in p0.get('input_images') or []]
        primeiro = min((origem / c for c in prompts[chaves[0]]['current_paths']), key=lambda f: f.stat().st_mtime, default=None)
        with B.travado(SLUG):
            ped = B.novo_no(SLUG, 'pedido', tela=tela_id, entradas=ents, intencao=intencao, legado=True,
                            modelo=B.modelo(p0.get('model') or 'gpt2'), aspecto=p0.get('aspect_ratio') or '16:9',
                            resolucao=p0.get('resolution') or '2K', quantidade=len(chaves), status='concluido')
        variacoes, saidas, custo_ped = [], [], 0.0
        for k in chaves:
            p = prompts[k]
            atuais = [origem / c for c in p['current_paths'] if (origem / c).exists()]
            if not atuais:
                print(f'  ! sem arquivo para {k}')
                continue
            arq = atuais[0]
            hsh = md5(arq)
            stem = Path(k).stem
            descartada = any('_descartados' in str(c) for c in atuais)
            aprovada = any('/aprovados/' in str(c) for c in por_hash.get(hsh, []))
            custo = next((c for c in (custo_do_log(x) for x in atuais) if c is not None), None)
            with B.travado(SLUG):
                img = B.novo_no(SLUG, 'imagem', pedido=ped['id'], nome=nome_legivel(stem), prompt=p['prompt'],
                                modelo=B.modelo(p.get('model') or 'gpt2'), aspecto=p.get('aspect_ratio') or '16:9',
                                resolucao=p.get('resolution'), legado=True, custo=custo, origem=k,
                                estado='aprovada' if aprovada else 'descartada' if descartada else 'neutra')
                img.update(copiar_arquivo(img['id'], arq, 'images'))
                img['criado'] = quando(arq)
                B.gravar_no(SLUG, img)
            criados_por_hash[hsh] = img['id']
            variacoes.append({'nome': nome_legivel(stem), 'prompt': p['prompt']})
            saidas.append(img['id'])
            custo_ped += custo or 0
        with B.travado(SLUG):
            ped = B.ler_no(SLUG, ped['id'])
            ped.update(variacoes=variacoes, saidas=saidas, custo=round(custo_ped, 4),
                       criado=quando(primeiro) if primeiro else ped['criado'])
            B.gravar_no(SLUG, ped)
        nonlocal_total[0] += custo_ped
        print(f'{ped["id"]} {intencao[:50]!r}: {len(saidas)} imagens, entradas {ents}')
        return ped['id']

    nonlocal_total = [0.0]
    grupos: dict[str, list[str]] = defaultdict(list)
    for k in prompts:
        grupos[k.split('/')[0] if not k.startswith('pinterest/') else '/'.join(k.split('/')[:2])].append(k)
    for g in grupos.values():
        g.sort()

    pedido(grupos['idle'], 'Idle: 10 direções de estilo para a tela inicial do orquestrador')
    pedido(grupos['idle-v2-stark'], 'Refinar a Stark HUD: menos texto, arco de agentes mais limpo, chat discreto')
    pedido(grupos['idle-v3-eve'], 'Usar o pôster da EVE como identidade visual (papel, desenho técnico, robô EVE como núcleo)')
    for pasta_pin in sorted(p for p in (origem / 'pinterest').iterdir() if p.is_dir()):
        rel = f'pinterest/{pasta_pin.name}'
        hint = (pasta_pin / 'hint.txt').read_text(encoding='utf-8').strip() if (pasta_pin / 'hint.txt').exists() else ''
        if grupos.get(rel):
            pedido(grupos[rel], f'Reinterpretar a referência do Pinterest: {hint}' if hint else 'Reinterpretar a referência do Pinterest')
        elif (pasta_pin / 'referencia.png').exists():
            referencia(pasta_pin / 'referencia.png', 'Pinterest')
    for g in ('neuronio', 'neuronio-02'):
        for tema in ('escuro', 'claro'):
            chaves = [k for k in grupos.get(g, []) if f'-{tema}-' in k]
            pedido(chaves, f'Manter o layout aprovado e trocar o núcleo pelo neurônio da referência · tema {tema}')

    # aprovados que não casaram com nenhuma imagem gerada (não deve sobrar nenhum)
    sobras = [f for f in (origem / 'aprovados').glob('*.png') if md5(f) not in criados_por_hash]
    for f in sobras:
        print(f'  ! aprovado sem origem: {f.name}')

    print(f'ok · {len(B.nos(SLUG))} nós · ${nonlocal_total[0]:.2f}')


if __name__ == '__main__':
    main()
