# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "pillow", "playwright"]
# ///
"""Calibra cada texto da página pela CAIXA DE TINTA da referência: posição, tamanho e espaçamento, até ±1 px.

    uv run calibrar_texto.py <url ?estatico> <textos.json> <saida.css> --ref reference.png [--rodadas 4]

textos.json:
  {"elementos": [
    {"id": "t-cpu", "caixa_ref": [52, 205, 82, 13], "ancora": "esq", "x": 52, "y": 200, "tamanho": 17},
    {"id": "t-titulo", "caixa_ref": [44, 44, 210, 22], "ancora": "esq", "x": 44, "y": 38, "tamanho": 31,
     "espaco": 14, "largura": true},
    {"id": "t-msg1", "caixa_ref": [1212, 244, 199, 65], "ancora": "esq", "x": 1212, "y": 240, "tamanho": 15,
     "so_posicao": true}
  ]}
  caixa_ref  a caixa de tinta do texto na referência (o detector de texto dá; ou meça no recorte)
  ancora     esq | dir | centro: qual borda prende (relógio à direita = dir)
  largura    também ajusta letter-spacing ("espaco", px) para a largura bater (título espaçado)
  so_posicao não mexe no tamanho (parágrafo de várias linhas: a altura depende do line-height, não da fonte)

Cada rodada: fotografa a página (relógio virtual), mede a tinta de cada #id dentro da caixa da referência com folga,
corrige x/y/tamanho/espaco no JSON e reescreve <saida.css> com `#id { left; top; font-size; letter-spacing }`.
A página precisa carregar esse CSS (link no index.html) e posicionar os textos com position: absolute.
Para quando todos ficam dentro de ±1 px e ±2 % de altura, ou nas --rodadas.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from scipy import ndimage

import _comum as C
from filmar import abrir, passo


def tinta(lum: np.ndarray) -> np.ndarray:
    """O mesmo detector usado para achar o texto na referência: mais escuro que o fundo local."""
    return (ndimage.maximum_filter(lum, 15) - lum) > 45


def caixa_de(m: np.ndarray):
    ys, xs = np.where(m)
    if not len(xs):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)]


def escrever_css(elementos: list[dict], saida: Path) -> None:
    linhas = ['/* gerado por calibrar_texto.py: posição e tamanho medidos contra a caixa de tinta da referência */']
    for e in elementos:
        regra = f'left: {e["x"]:.2f}px; top: {e["y"]:.2f}px; font-size: {e["tamanho"]:.3f}px;'
        if 'espaco' in e:
            regra += f' letter-spacing: {e["espaco"]:.3f}px;'
        linhas.append(f'#{e["id"]} {{ {regra} }}')
    saida.write_text('\n'.join(linhas) + '\n', encoding='utf-8')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('url')
    ap.add_argument('textos', type=Path)
    ap.add_argument('saida', type=Path)
    ap.add_argument('--ref', type=Path, required=True)
    ap.add_argument('--rodadas', type=int, default=4)
    ap.add_argument('--folga', type=int, default=8, help='px em volta da caixa da referência onde se procura a tinta')
    a = ap.parse_args()

    dados = C.ler_json(a.textos)
    els = dados['elementos']
    ref_lum = np.asarray(Image.open(a.ref).convert('L'), np.float32)
    H, W = ref_lum.shape
    escrever_css(els, a.saida)
    relatorio = []
    with sync_playwright() as p:
        for rodada in range(1, a.rodadas + 1):
            nav, pag, log = abrir(p, a.url, W, H, 7)
            passo(pag, 500)
            foto = np.asarray(Image.open(io.BytesIO(pag.screenshot(type='png'))).convert('L'), np.float32)
            nav.close()
            m = tinta(foto)
            pior = 0.0
            relatorio = []
            for e in els:
                x, y, w, h = e['caixa_ref']
                f = a.folga
                sub = m[max(0, y - f):y + h + f, max(0, x - f):x + w + f]
                cx = caixa_de(sub)
                if not cx:
                    relatorio.append(f'  {e["id"]}: SEM TINTA na caixa (fonte não carregou? posição muito longe?)')
                    pior = 99
                    continue
                gx, gy, gw, gh = cx[0] + max(0, x - f), cx[1] + max(0, y - f), cx[2], cx[3]
                if e.get('ancora') == 'dir':
                    dx = (x + w) - (gx + gw)
                elif e.get('ancora') == 'centro':
                    dx = (x + w / 2) - (gx + gw / 2)
                else:
                    dx = x - gx
                dy = y - gy
                esc = h / gh if not e.get('so_posicao') else 1.0
                e['x'] += dx
                e['y'] += dy
                if abs(esc - 1) > 0.015:
                    e['tamanho'] *= esc
                    # mudar o tamanho desloca a tinta dentro da caixa da linha: o y é refeito na próxima rodada
                if e.get('largura') and 'espaco' in e:
                    n = max(1, len(e.get('texto', 'x' * 6)) - 1)
                    e['espaco'] += (w - gw * (esc if not e.get('so_posicao') else 1)) / n
                pior = max(pior, abs(dx), abs(dy), abs(esc - 1) * h, abs(w - gw) if e.get('largura') else 0)
                relatorio.append(f'  {e["id"]}: ref {x},{y} {w}x{h} · página {gx},{gy} {gw}x{gh} · '
                                 f'Δ ({dx:+.1f}, {dy:+.1f}) px · altura {gh / h:.3f}x')
            escrever_css(els, a.saida)
            C.gravar_json(a.textos, dados)
            print(f'rodada {rodada}: maior erro {pior:.1f} px' + (' (erros de console: ' + str(len(log["erros"])) + ')' if log['erros'] else ''))
            if pior <= 1.0:
                break
    print('\n'.join(relatorio))
    sys.exit(0 if pior <= 1.5 else 1)


if __name__ == '__main__':
    main()
