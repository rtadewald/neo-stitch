# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow", "playwright"]
# ///
"""Qual Google Font (e peso) é a do texto da imagem? Renderiza candidatas no Chrome e mede a sobreposição das letras.

    uv run achar_fonte.py <reference.png> --caixa x,y,w,h --texto "Agente Principal" [--familias "A,B,C"] [--pesos 400,500]
                          [--saida pasta] [--espacamento]

A caixa é um recorte justo de UMA linha de texto na referência (escuro sobre claro, ou claro sobre escuro com --claro).
Cada candidata é escrita com o mesmo texto, ajustada para a mesma altura de tinta e a mesma largura (o espaçamento entre
letras é ajustado com --espacamento) e comparada por IoU das máscaras binárias. Sai o ranking e, em --saida, uma folha
com a referência e as 6 melhores, mais o tamanho em px e o letter-spacing que reproduzem a caixa.
Não acha fonte que não está no Google Fonts: a melhor nota abaixo de ~0,6 diz "aproxime e declare".
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

import _comum as C

MONO = ['Spline Sans Mono', 'IBM Plex Mono', 'JetBrains Mono', 'DM Mono', 'Roboto Mono', 'Space Mono', 'Geist Mono',
        'Martian Mono', 'Azeret Mono', 'Fira Code', 'Source Code Pro', 'Red Hat Mono', 'Sometype Mono', 'Ubuntu Mono',
        'Overpass Mono', 'Chivo Mono', 'Kode Mono', 'Reddit Mono', 'Victor Mono', 'Inconsolata']
SANS = ['Hanken Grotesk', 'Inter', 'Manrope', 'Space Grotesk', 'Sora', 'Outfit', 'Plus Jakarta Sans', 'DM Sans',
        'Work Sans', 'IBM Plex Sans', 'Archivo', 'Rubik', 'Figtree', 'Onest', 'Geist', 'Schibsted Grotesk']

PAGINA = """<!doctype html><html><head><link rel="stylesheet" href="https://fonts.googleapis.com/css2?{familias}&display=block">
<style>body{{margin:0;background:#fff}} span{{position:absolute;left:20px;top:20px;white-space:pre;color:#000;line-height:1}}</style>
</head><body><span id=t></span></body></html>"""


def mascara(img: Image.Image, claro: bool) -> np.ndarray:
    g = np.asarray(img.convert('L'), np.float32)
    if claro:
        g = 255 - g
    limiar = (g.min() + np.median(g)) / 2
    return g < limiar


def caixa_tinta(m: np.ndarray):
    ys, xs = np.where(m)
    if not len(xs):
        return None
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('ref', type=Path)
    ap.add_argument('--caixa', required=True)
    ap.add_argument('--texto', required=True)
    ap.add_argument('--familias', help='lista separada por vírgula; padrão: "mono" ou "sans" (atalhos) ou as duas')
    ap.add_argument('--pesos', default='300,400,500,600')
    ap.add_argument('--claro', action='store_true', help='texto claro sobre fundo escuro')
    ap.add_argument('--espacamento', action='store_true', help='ajusta letter-spacing para a largura bater')
    ap.add_argument('--saida', type=Path)
    a = ap.parse_args()

    x, y, w, h = (int(v) for v in a.caixa.split(','))
    recorte = Image.open(a.ref).convert('RGB').crop((x, y, x + w, y + h))
    mref = mascara(recorte, a.claro)
    cx = caixa_tinta(mref)
    if not cx:
        sys.exit('ERRO: nenhuma tinta na caixa')
    mref = mref[cx[1]:cx[3], cx[0]:cx[2]]
    alt_ref, larg_ref = mref.shape

    if not a.familias or a.familias in ('mono', 'sans'):
        familias = MONO if a.familias == 'mono' else SANS if a.familias == 'sans' else MONO + SANS
    else:
        familias = [f.strip() for f in a.familias.split(',') if f.strip()]
    pesos = [int(p) for p in a.pesos.split(',')]
    css = '&'.join(f'family={f.replace(" ", "+")}:wght@{";".join(map(str, pesos))}' for f in familias)

    resultados = []
    with sync_playwright() as p:
        nav = p.chromium.launch(channel='chrome')
        pag = nav.new_page(viewport={'width': 2400, 'height': 400})
        pag.set_content(PAGINA.format(familias=css))
        pag.wait_for_load_state('networkidle')
        pag.evaluate('document.fonts.ready.then(() => 1)')
        for fam in familias:
            for peso in pesos:
                # o Chrome só baixa a fonte quando alguém pede: load() baixa e diz se existe nesse peso
                disponivel = pag.evaluate('([f, p, t]) => document.fonts.load(`${p} 40px "${f}"`, t).then(l => l.length)',
                                          [fam, peso, a.texto])
                if not disponivel:
                    continue
                # 1ª passada em 100 px para medir a proporção; depois no tamanho que dá a altura de tinta da referência
                tam, esp = 100.0, 0.0
                for passada in range(3):
                    pag.evaluate('([f, p, s, e, t]) => { const el = document.getElementById("t"); el.style.fontFamily = `"${f}"`;'
                                 'el.style.fontWeight = p; el.style.fontSize = s + "px"; el.style.letterSpacing = e + "px";'
                                 'el.textContent = t; }', [fam, peso, tam, esp, a.texto])
                    caixa = pag.evaluate('(() => { const r = document.getElementById("t").getBoundingClientRect();'
                                         'return [r.x, r.y, r.width, r.height]; })()')
                    png = pag.screenshot(clip={'x': 0, 'y': 0, 'width': min(2400, caixa[0] + caixa[2] + 40),
                                               'height': min(400, caixa[1] + caixa[3] + 40)})
                    m = mascara(Image.open(io.BytesIO(png)), False)
                    ci = caixa_tinta(m)
                    if not ci:
                        break
                    m = m[ci[1]:ci[3], ci[0]:ci[2]]
                    if passada == 0:
                        tam = tam * alt_ref / m.shape[0]
                        continue
                    if passada == 1 and a.espacamento and len(a.texto) > 1:
                        esp = (larg_ref - m.shape[1]) / (len(a.texto) - 1)
                        continue
                    break
                if not ci:
                    continue
                cand = np.asarray(Image.fromarray(m).resize((larg_ref, alt_ref), Image.NEAREST))
                inter = np.logical_and(cand, mref).sum()
                uniao = np.logical_or(cand, mref).sum()
                razao_larg = m.shape[1] / larg_ref
                nota = inter / max(uniao, 1) * min(razao_larg, 1 / razao_larg) ** 2
                resultados.append({'familia': fam, 'peso': peso, 'nota': round(float(nota), 3), 'font_size': round(tam, 2),
                                   'letter_spacing': round(esp, 2), 'razao_largura': round(razao_larg, 3),
                                   'mascara': cand})
        nav.close()

    resultados.sort(key=lambda r: r['nota'], reverse=True)
    for r in resultados[:10]:
        print(f'  {r["nota"]:.3f}  {r["familia"]} {r["peso"]}  font-size {r["font_size"]}px'
              f'  letter-spacing {r["letter_spacing"]}px  largura {r["razao_largura"]:.2f}x')
    if a.saida:
        a.saida.mkdir(parents=True, exist_ok=True)
        esc = max(1, 600 // max(larg_ref, 1))
        linhas = [('referência', mref)] + [(f'{r["nota"]:.3f} {r["familia"]} {r["peso"]}', r['mascara']) for r in resultados[:6]]
        folha = Image.new('L', (larg_ref * esc + 20, len(linhas) * (alt_ref * esc + 26)), 255)
        d = ImageDraw.Draw(folha)
        for i, (rot, m) in enumerate(linhas):
            yy = i * (alt_ref * esc + 26)
            d.text((4, yy + 2), rot, fill=0)
            folha.paste(Image.fromarray((~m * 255).astype(np.uint8)).resize((larg_ref * esc, alt_ref * esc), Image.NEAREST),
                        (10, yy + 20))
        nome = ''.join(ch for ch in a.texto if ch.isalnum())[:20] or 'texto'
        folha.save(a.saida / f'fonte-{nome}.png')
        C.gravar_json(a.saida / f'fonte-{nome}.json', [{k: v for k, v in r.items() if k != 'mascara'} for r in resultados])
        print(f'folha: {a.saida / f"fonte-{nome}.png"}')


if __name__ == '__main__':
    main()
