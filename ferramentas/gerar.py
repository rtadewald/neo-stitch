# /// script
# requires-python = ">=3.11"
# ///
"""Gera as imagens de um pedido (OpenRouter /api/v1/images) e as pendura no canvas.

    uv run ferramentas/gerar.py <PEDIDO> --prompt "…" [--prompt "…"]… [--nome "…"]…
    uv run ferramentas/gerar.py <PEDIDO> --json variacoes.json      [{"nome": "…", "prompt": "…"}, …]
    uv run ferramentas/gerar.py <PEDIDO> --prompt "…" --quantidade 4  (o mesmo prompt N vezes)

Opções: --modelo (alias ou slug; padrão: o do pedido) · --aspecto · --resolucao · --qualidade · --confirmado
(passa por cima dos tetos de custo; só depois do usuário dizer sim).

O que faz:
1. Grava as variações no pedido e cria os nós de imagem já com `gerando: true` (o canvas mostra os placeholders).
2. Manda TODAS as entradas do pedido (imagens e referências) como `input_references` e gera em paralelo.
3. Cada imagem: images/<COD>.png + thumbs/<COD>.jpg, prompt, modelo, custo, tempo. O pedido fecha como `concluido`
   (ou `erro`, se nenhuma saiu). Nada é apagado: uma imagem que falhou fica com `erro`.

Saída 3 = bloqueado pelo teto de custo (pergunte ao usuário e rode de novo com --confirmado).
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import base as B  # noqa: E402
from openrouter import chave, data_url, pedir  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('pedido')
    ap.add_argument('--prompt', action='append', default=[])
    ap.add_argument('--nome', action='append', default=[])
    ap.add_argument('--json')
    ap.add_argument('--quantidade', type=int)
    ap.add_argument('--modelo')
    ap.add_argument('--aspecto')
    ap.add_argument('--resolucao')
    ap.add_argument('--qualidade')
    ap.add_argument('--confirmado', action='store_true')
    a = ap.parse_args()

    slug, pid = B.resolver_codigo(a.pedido)
    pedido = B.ler_no(slug, pid)
    if pedido['tipo'] != 'pedido':
        sys.exit(f'ERRO: {pid} é {pedido["tipo"]}, não pedido.')

    if a.json:
        variacoes = [{'nome': v.get('nome', ''), 'prompt': v['prompt']} for v in json.loads(B.json_ou_arquivo(a.json))]
    elif a.prompt:
        if len(a.prompt) == 1 and (a.quantidade or 1) > 1:
            a.prompt = a.prompt * a.quantidade
        variacoes = [{'nome': a.nome[i] if i < len(a.nome) else '', 'prompt': p} for i, p in enumerate(a.prompt)]
    else:
        sys.exit('ERRO: passe --prompt ou --json.')

    projeto = B.ler_projeto(slug)
    mod = B.modelo(a.modelo or pedido.get('modelo'))
    aspecto = a.aspecto or pedido.get('aspecto') or projeto['padroes']['aspecto']
    resolucao = a.resolucao or pedido.get('resolucao') or projeto['padroes']['resolucao']
    preco = B.MODELOS.get(mod, {}).get('preco', 0.15)
    tetos = projeto.get('tetos', B.TETOS)
    estimativa = preco * len(variacoes)
    hoje = B.custos(slug)['hoje']
    if not a.confirmado:
        if len(variacoes) > tetos['imagens_por_pedido']:
            print(f'BLOQUEADO: {len(variacoes)} imagens (teto por pedido: {tetos["imagens_por_pedido"]}). '
                  f'Estimativa ${estimativa:.2f}. Pergunte ao usuário e rode com --confirmado.')
            sys.exit(3)
        if hoje + estimativa > tetos['diario_usd']:
            print(f'BLOQUEADO: hoje ${hoje:.2f} + ${estimativa:.2f} passa do teto diário ${tetos["diario_usd"]:.2f}. '
                  'Pergunte ao usuário e rode com --confirmado.')
            sys.exit(3)

    pasta = B.pasta(slug)
    refs = []
    for e in pedido.get('entradas', []):     # nós com arquivo e páginas IMG/vN (pelo print delas)
        if f := B.arquivo_entrada(slug, e):
            refs.append(f)

    teses = {v.get('nome'): v.get('tese') for v in pedido.get('variacoes') or [] if v.get('tese')}
    for v in variacoes:
        if teses.get(v['nome']):
            v['tese'] = teses[v['nome']]

    # 1. variações no pedido + placeholders
    with B.travado(slug):
        pedido = B.ler_no(slug, pid)
        imagens = []
        for v in variacoes:
            img = B.novo_no(slug, 'imagem', pedido=pid, nome=v['nome'], prompt=v['prompt'], modelo=mod, aspecto=aspecto,
                            resolucao=resolucao, gerando=True)
            imagens.append(img['id'])
        pedido.update({'status': 'trabalhando', 'variacoes': variacoes, 'modelo': mod, 'aspecto': aspecto,
                       'resolucao': resolucao, 'saidas': pedido.get('saidas', []) + imagens,
                       'iniciado_em': B.agora()})
        pedido.pop('erro', None)
        B.gravar_no(slug, pedido)

    key = chave()
    entradas = [{'type': 'image_url', 'image_url': {'url': data_url(r)}} for r in refs]

    def uma(par):
        iid, v = par
        corpo = {'model': mod, 'prompt': v['prompt'], 'n': 1, 'aspect_ratio': aspecto, 'resolution': resolucao}
        if a.qualidade:
            corpo['quality'] = a.qualidade
        if entradas:
            corpo['input_references'] = entradas
        t0 = time.time()
        try:
            dados = pedir('POST', '/images', key, corpo, timeout=600)
            item = (dados.get('data') or [{}])[0]
            if not item.get('b64_json'):
                raise RuntimeError(f'sem imagem na resposta: {json.dumps(dados)[:300]}')
            arq = pasta / 'images' / f'{iid}.png'
            arq.write_bytes(base64.b64decode(item['b64_json']))
            B.miniatura(arq, pasta / 'thumbs' / f'{iid}.jpg')
            med = B.medidas(arq) or (None, None)
            campos = {'arquivo': f'images/{iid}.png', 'thumb': f'thumbs/{iid}.jpg', 'largura': med[0], 'altura': med[1],
                      'custo': (dados.get('usage') or {}).get('cost'), 'segundos': round(time.time() - t0, 1)}
            ok = True
        except Exception as e:  # noqa: BLE001
            campos, ok = {'erro': str(e)[:600]}, False
        with B.travado(slug):
            img = B.ler_no(slug, iid)
            img.pop('gerando', None)
            img.update(campos)
            B.gravar_no(slug, img)
        print(f'{iid} {"ok" if ok else "ERRO"} {campos.get("custo") or campos.get("erro", "")}', flush=True)
        return ok

    with ThreadPoolExecutor(max_workers=min(6, len(variacoes))) as ex:
        resultados = list(ex.map(uma, zip(imagens, variacoes)))

    with B.travado(slug):
        pedido = B.ler_no(slug, pid)
        custo = sum((B.ler_no(slug, i).get('custo') or 0) for i in imagens)
        pedido['custo'] = round((pedido.get('custo') or 0) + custo, 4)
        pedido['status'] = 'concluido' if any(resultados) else 'erro'
        if not any(resultados):
            pedido['erro'] = 'Nenhuma imagem foi gerada (veja o erro nas imagens).'
        pedido['concluido_em'] = B.agora()
        B.gravar_no(slug, pedido)
    print(f'{pid}: {sum(resultados)}/{len(resultados)} imagens · ${custo:.3f} · {", ".join(imagens)}')
    sys.exit(0 if any(resultados) else 1)


if __name__ == '__main__':
    main()
