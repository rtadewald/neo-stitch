# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "pillow"]
# ///
"""Apaga da placa o que vai virar HTML/SVG (texto, linhas, barras, brilho), preenchendo pelo fundo em volta.

    uv run limpar_placa.py <entrada.png> <saida.png> --apagar escuro:x,y,w,h --apagar verde:x,y,w,h ...
                           [--origem x,y] [--dilatar 2] [--mascara saida-mascara.png]

Modos de cada --apagar (repetível, caixas em px da referência):
  escuro   só os pixels mais escuros que o fundo local (texto e traço escuro sobre papel ou cartão)
  claro    só os pixels mais claros que o fundo local (brilho, texto claro)
  verde    só os pixels com verde saturado (linhas e halos do acento), claros ou escuros
  tudo     a caixa inteira
O buraco é preenchido por difusão (o valor dos vizinhos entra até o centro), o que some com traço fino sem deixar
mancha; o grão do papel não volta dentro do traço, o que é imperceptível em traços de até ~4 px.
--origem: quando a entrada é um recorte (ex.: a escura.png do isolar_camada), o canto dele em px da referência.
Imprime quantos px apagou por caixa: 0 numa caixa = a caixa ou o modo estão errados.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

import _comum  # noqa: F401  (saída UTF-8 no Windows)


def difundir(img: np.ndarray, buraco: np.ndarray, iteracoes: int = 400) -> np.ndarray:
    """Preenche o buraco com a média dos vizinhos válidos, de fora para dentro (multiescala para ser rápido)."""
    saida = img.copy()
    valido = (~buraco).astype(np.float32)
    # chute inicial: a média dos válidos, do raio maior ao menor (o maior cobre o centro de caixas grandes; sem isso o
    # miolo guarda a tinta original e a difusão só a espalha em cinza)
    for raio in (151, 61, 31, 15, 7):
        soma = np.stack([ndimage.uniform_filter(saida[..., k] * valido, raio) for k in range(3)], axis=-1)
        peso = ndimage.uniform_filter(valido, raio)[..., None]
        chute = soma / np.clip(peso, 1e-6, None)
        sel = buraco & (peso[..., 0] > 1e-3)
        saida[sel] = chute[sel]
    for _ in range(iteracoes):
        media = np.stack([ndimage.uniform_filter(saida[..., k], 3) for k in range(3)], axis=-1)
        saida[buraco] = media[buraco]
    return saida


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('entrada', type=Path)
    ap.add_argument('saida', type=Path)
    ap.add_argument('--apagar', action='append', default=[], required=True, metavar='modo:x,y,w,h')
    ap.add_argument('--origem', default='0,0')
    ap.add_argument('--dilatar', type=int, default=2, help='px de folga em volta do que foi detectado (antisserrilhado)')
    ap.add_argument('--limiar', type=float, default=0.06, help='diferença mínima para o fundo local (0-1) nos modos escuro/claro')
    ap.add_argument('--verde', type=float, default=0.05, help='modo verde: G acima de max(R, B) por pelo menos isto (0-1)')
    ap.add_argument('--verde-lum', type=float, default=0.38, help='modo verde: luminância mínima (exclui tinta escura)')
    ap.add_argument('--grao-de', metavar='x,y', help='canto de um trecho de papel LIMPO: o grão dele (alta frequência) volta '
                    'por cima das caixas "tudo", que senão ficam lisas demais')
    ap.add_argument('--mascara', type=Path, help='grava a máscara do que foi apagado (para conferir)')
    a = ap.parse_args()

    img = np.asarray(Image.open(a.entrada).convert('RGB'), np.float32) / 255
    H, W, _ = img.shape
    ox, oy = (int(v) for v in a.origem.split(','))
    lum = img.mean(axis=2)
    buraco = np.zeros((H, W), bool)
    caixas_tudo = []
    for item in a.apagar:
        modo, caixa = item.split(':', 1)
        x, y, w, h = (int(v) for v in caixa.split(','))
        x, y = x - ox, y - oy
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
        if x1 <= x0 or y1 <= y0:
            print(f'  {item}: fora da imagem')
            continue
        sub = (slice(y0, y1), slice(x0, x1))
        if modo == 'tudo':
            m = np.ones((y1 - y0, x1 - x0), bool)
            caixas_tudo.append((x0, y0, x1, y1))
        elif modo in ('escuro', 'claro'):
            pad = 12
            py0, px0, py1, px1 = max(0, y0 - pad), max(0, x0 - pad), min(H, y1 + pad), min(W, x1 + pad)
            local = lum[py0:py1, px0:px1]
            fundo = (ndimage.maximum_filter if modo == 'escuro' else ndimage.minimum_filter)(local, 11)
            fundo = ndimage.median_filter(fundo, 9)
            dif = (fundo - local) if modo == 'escuro' else (local - fundo)
            m = (dif > a.limiar)[y0 - py0:y1 - py0, x0 - px0:x1 - px0]
        elif modo == 'verde':
            r, g, b = img[sub][..., 0], img[sub][..., 1], img[sub][..., 2]
            # verde do acento, não a tinta verde-escura (que tem luminância baixa)
            m = (g - np.maximum(r, b) > a.verde) & (lum[sub] > a.verde_lum)
        else:
            raise SystemExit(f'modo desconhecido: {modo}')
        print(f'  {item}: {int(m.sum())} px')
        buraco[sub] |= m
    if a.dilatar:
        buraco = ndimage.binary_dilation(buraco, iterations=a.dilatar)
    saida = difundir(img, buraco)
    if a.grao_de and caixas_tudo:
        sx, sy = (int(v) for v in a.grao_de.split(','))
        for x0, y0, x1, y1 in caixas_tudo:
            fonte = img[sy:sy + (y1 - y0), sx:sx + (x1 - x0)]
            if fonte.shape[:2] != (y1 - y0, x1 - x0):
                print(f'  --grao-de: trecho fora da imagem para a caixa {x0},{y0}')
                continue
            grao = fonte - np.stack([ndimage.gaussian_filter(fonte[..., k], 2) for k in range(3)], axis=-1)
            saida[y0:y1, x0:x1] += grao
    a.saida.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((np.clip(saida, 0, 1) * 255).round().astype(np.uint8)).save(a.saida)
    if a.mascara:
        Image.fromarray((buraco * 255).astype(np.uint8)).save(a.mascara)
    print(f'{a.saida} · {int(buraco.sum())} px apagados')


if __name__ == '__main__':
    main()
