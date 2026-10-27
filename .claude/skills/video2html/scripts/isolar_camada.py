# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "pillow"]
# ///
"""Separa um objeto vivo do fundo em camadas que, recompostas, dão a imagem de volta. Sem API, sem recorte à mão.

    uv run isolar_camada.py <reference.png> <pasta> --caixa x,y,w,h [--placa placa.png] [--raio 24] [--margem 40]

Para arte de tinta, fumaça, partículas ou brilho sobre um fundo liso ou de papel, onde recorte por segmentação falha.
Saídas em <pasta>:
  placa.png    o fundo sem o objeto (dentro da caixa, o papel reconstruído; fora, a referência intacta)
  escura.png   o que ESCURECE o fundo (tinta), para mix-blend-mode: multiply. Branco = não faz nada
  clara.png    o que CLAREIA o fundo (brilho), para mix-blend-mode: screen. Preto = não faz nada
  previa.png   placa × escura + clara, recomposta (deve ser a referência) e a diferença média no terminal

Sem --placa, o papel é estimado dentro da caixa: máximo local (some a tinta) + mínimo (volta ao tom) + desfoque
grande, e as bordas da caixa casam com a referência. Para fundo com desenho (grade, textura forte), gere a placa
com o GPT Image 2 apagando o objeto e passe em --placa. As camadas saem só do tamanho da caixa + margem, prontas para
virar <img> ou textura WebGL que gira, deriva ou se desfaz sem mostrar papel errado por baixo.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

import _comum as C


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('ref', type=Path)
    ap.add_argument('pasta', type=Path)
    ap.add_argument('--caixa', required=True, help='x,y,w,h do objeto, em px da referência')
    ap.add_argument('--placa', type=Path, help='fundo sem o objeto, já pronto (mesmo tamanho da referência)')
    ap.add_argument('--raio', type=int, default=24, help='raio do filtro que apaga a tinta (maior que o traço mais grosso)')
    ap.add_argument('--margem', type=int, default=40, help='px em volta da caixa incluídos nas camadas')
    ap.add_argument('--elipse', action='store_true', help='objeto redondo: só a elipse inscrita na caixa vira camada')
    a = ap.parse_args()

    ref = np.asarray(Image.open(a.ref).convert('RGB'), np.float32) / 255
    H, W, _ = ref.shape
    x, y, w, h = (int(v) for v in a.caixa.split(','))
    x0, y0 = max(0, x - a.margem), max(0, y - a.margem)
    x1, y1 = min(W, x + w + a.margem), min(H, y + h + a.margem)

    if a.placa:
        placa = np.asarray(Image.open(a.placa).convert('RGB').resize((W, H)), np.float32) / 255
    else:
        placa = ref.copy()
        trecho = ref[y0:y1, x0:x1]
        hh, ww = trecho.shape[:2]
        # papel = superfície suave de grau 2 ajustada só nos pixels claros (os que não têm tinta)
        lum = trecho.mean(axis=2)
        papel = ndimage.maximum_filter(lum, 2 * a.raio + 1) - lum < 0.03
        papel &= lum > np.percentile(lum, 35)
        yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
        u, v = xx / ww - 0.5, yy / hh - 0.5
        base = np.stack([np.ones_like(u), u, v, u * u, u * v, v * v], axis=-1)
        A = base[papel]
        est = np.stack([base @ np.linalg.lstsq(A, trecho[..., k][papel], rcond=None)[0] for k in range(3)], axis=-1)
        # grão do papel: o da própria referência onde é papel, a superfície onde há tinta
        grao = np.where(papel[..., None], trecho, est)
        grao = np.stack([ndimage.gaussian_filter(grao[..., k], 1.0) for k in range(3)], axis=-1)
        est = np.where(papel[..., None], grao, est)
        # casar com a referência na borda do trecho (sem degrau)
        dist = np.minimum.reduce([xx, yy, (ww - 1) - xx, (hh - 1) - yy])
        peso = np.clip(dist / max(a.margem, 1), 0, 1)[..., None]
        placa[y0:y1, x0:x1] = trecho * (1 - peso) + np.maximum(est, trecho) * peso

    if a.elipse:  # o objeto é redondo: fora da elipse inscrita na caixa, a placa volta a ser a referência
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - (x + w / 2)) / (w / 2)) ** 2 + ((yy - (y + h / 2)) / (h / 2)) ** 2)
        dentro = np.clip((1.06 - r) / 0.06, 0, 1)[..., None]
        placa = ref * (1 - dentro) + placa * dentro

    P = np.clip(placa[y0:y1, x0:x1], 1e-3, 1)
    R = ref[y0:y1, x0:x1]
    escura = np.clip(np.minimum(R, P) / P, 0, 1)             # placa × escura = parte escura
    base = P * escura
    clara = np.clip((R - base) / np.clip(1 - base, 1e-3, 1), 0, 1)  # screen(base, clara) = R
    recomposta = 1 - (1 - base) * (1 - clara)
    erro = float(np.abs(recomposta - R).mean() * 255)

    a.pasta.mkdir(parents=True, exist_ok=True)
    salvar = lambda m, nome: Image.fromarray((np.clip(m, 0, 1) * 255).round().astype(np.uint8)).save(a.pasta / nome)
    salvar(placa, 'placa.png')
    salvar(escura, 'escura.png')
    salvar(clara, 'clara.png')
    prev = ref.copy()
    prev[y0:y1, x0:x1] = recomposta
    salvar(prev, 'previa.png')
    C.gravar_json(a.pasta / 'camadas.json', {'caixa_camadas': [x0, y0, x1 - x0, y1 - y0], 'erro_recomposicao': round(erro, 3),
                                             'placa_estimada': not a.placa})
    print(f'camadas de {x1 - x0}x{y1 - y0} px em ({x0}, {y0}) · erro da recomposição {erro:.2f}/255 · '
          f'posicione escura.png e clara.png em left:{x0}px top:{y0}px sobre placa.png')


if __name__ == '__main__':
    main()
