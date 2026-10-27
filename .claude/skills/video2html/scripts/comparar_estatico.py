# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow"]
# ///
"""Fase estática: a foto da página no ?estatico contra a reference.png. Diz QUANTO difere, ONDE e se está DESLOCADO.

    uv run comparar_estatico.py <reference.png> <foto.png> <pasta> [--grade 8x6] [--limite 5] [--celula 14]

Saídas em <pasta>:
  estatico.json      média (0-255), média por canal, deslocamento global (dx, dy), as células da grade e as piores
  calor.png          a diferença amplificada 4x sobre a referência esmaecida, com a grade e as notas por célula
  piores/cNN.png     zoom 2x das piores células: referência | página | diferença

Passa (saída 0) quando a média <= --limite e nenhuma célula > --celula. Sai com 1 caso contrário.
Deslocamento global diferente de (0, 0) quase sempre é escala ou viewport errados: corrija isso antes de qualquer
ajuste fino. Diferença que sobra só em textura fina (grão do papel, ruído de IA) é irredutível: anote, não persiga.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import _comum as C


def deslocamento(a: np.ndarray, b: np.ndarray) -> tuple[int, int]:
    """(dx, dy) que leva b até a, por correlação de fase (escala reduzida pela metade)."""
    fa = np.fft.fft2(a - a.mean())
    fb = np.fft.fft2(b - b.mean())
    r = fa * np.conj(fb)
    r /= np.abs(r) + 1e-9
    c = np.fft.ifft2(r).real
    y, x = np.unravel_index(int(np.argmax(c)), c.shape)
    if y > c.shape[0] // 2:
        y -= c.shape[0]
    if x > c.shape[1] // 2:
        x -= c.shape[1]
    return int(x * 2), int(y * 2)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('ref', type=Path)
    ap.add_argument('foto', type=Path)
    ap.add_argument('pasta', type=Path)
    ap.add_argument('--grade', default='8x6')
    ap.add_argument('--limite', type=float, default=5.0, help='média máxima aceita (0-255)')
    ap.add_argument('--celula', type=float, default=14.0, help='máximo aceito numa célula da grade')
    ap.add_argument('--ignorar', action='append', default=[], metavar='x,y,w,h',
                    help='área com desvio PEDIDO (ex.: fonte trocada a pedido); sai da conta. Repetível; anote no README')
    a = ap.parse_args()

    ref = Image.open(a.ref).convert('RGB')
    foto = Image.open(a.foto).convert('RGB')
    if foto.size != ref.size:
        print(f'aviso: foto {foto.size} ≠ referência {ref.size}; redimensionando a foto (fotografe no tamanho da referência)')
        foto = foto.resize(ref.size, Image.LANCZOS)
    R = np.asarray(ref, np.float32)
    F = np.asarray(foto, np.float32)
    dif = np.abs(R - F)
    H, W = dif.shape[:2]
    valido = np.ones((H, W), bool)
    for caixa in a.ignorar:
        x, y, w, h = (int(v) for v in caixa.split(','))
        valido[y:y + h, x:x + w] = False
    dif[~valido] = 0
    lum = np.ma.masked_array(dif.mean(axis=2), ~valido)
    gx, gy = (int(v) for v in a.grade.lower().split('x'))
    celulas = []
    for j in range(gy):
        for i in range(gx):
            x0, x1 = W * i // gx, W * (i + 1) // gx
            y0, y1 = H * j // gy, H * (j + 1) // gy
            m = lum[y0:y1, x0:x1].mean()
            celulas.append({'id': f'c{j * gx + i + 1:02d}', 'caixa': [x0, y0, x1 - x0, y1 - y0],
                            'media': 0.0 if m is np.ma.masked else round(float(m), 2)})
    piores = sorted(celulas, key=lambda c: c['media'], reverse=True)[:4]
    pequeno = lambda m: np.asarray(Image.fromarray(m.astype(np.uint8)).convert('L').resize((W // 2, H // 2)), np.float32)
    dx, dy = deslocamento(pequeno(R), pequeno(F))

    a.pasta.mkdir(parents=True, exist_ok=True)
    (a.pasta / 'piores').mkdir(exist_ok=True)
    fundo = R * 0.35 + 255 * 0.65
    calor = fundo.copy()
    amp = np.clip(lum.filled(0) * 4, 0, 255)
    calor[..., 0] = np.clip(fundo[..., 0] * (1 - amp / 255) + amp, 0, 255)
    calor[..., 1] = fundo[..., 1] * (1 - amp / 255)
    calor[..., 2] = fundo[..., 2] * (1 - amp / 255)
    img = Image.fromarray(calor.astype(np.uint8))
    d = ImageDraw.Draw(img)
    for c in celulas:
        x, y, w, h = c['caixa']
        ruim = c['media'] > a.celula
        d.rectangle([x, y, x + w, y + h], outline='#c2502e' if ruim else '#b8b0a0', width=3 if ruim else 1)
        d.text((x + 6, y + 6), f"{c['id']} {c['media']:.1f}", fill='#14302a')
    img.save(a.pasta / 'calor.png')
    for c in piores:
        x, y, w, h = c['caixa']
        corte = lambda im: im.crop((x, y, x + w, y + h)).resize((w * 2, h * 2), Image.LANCZOS)
        dimg = Image.fromarray(np.clip(dif * 4, 0, 255).astype(np.uint8))
        tira = Image.new('RGB', (w * 6 + 20, h * 2), 'white')
        for k, im in enumerate((ref, foto, dimg)):
            tira.paste(corte(im), (k * (w * 2 + 10), 0))
        tira.save(a.pasta / 'piores' / f"{c['id']}.png")

    media = float(lum.mean())
    canais = [round(float(dif[..., k].mean()), 2) for k in range(3)]
    passou = media <= a.limite and all(c['media'] <= a.celula for c in celulas)
    C.gravar_json(a.pasta / 'estatico.json', {
        'media': round(media, 2), 'canais_rgb': canais, 'deslocamento': [dx, dy], 'limite': a.limite,
        'celula_max': a.celula, 'passou': passou, 'piores': piores, 'celulas': celulas})
    print(f'média {media:.2f}/255 (limite {a.limite}) · RGB {canais} · deslocamento global ({dx}, {dy}) px · '
          f'{"PASSOU" if passou else "NÃO PASSOU"}')
    print('piores: ' + ', '.join(f"{c['id']} {c['media']:.1f}" for c in piores) + f' · abra {a.pasta / "calor.png"}')
    if (dx, dy) != (0, 0):
        print('  deslocamento ≠ 0: confira escala, viewport e a origem do palco antes do ajuste fino')
    sys.exit(0 if passou else 1)


if __name__ == '__main__':
    main()
