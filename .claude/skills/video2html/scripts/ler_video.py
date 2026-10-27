# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "pillow"]
# ///
"""Lê um vídeo de referência e diz ONDE algo se mexe, QUANTO e QUANDO. É a régua de tudo que vem depois.

    uv run ler_video.py <video.mp4> <pasta> [--largura-ref 1536] [--limiar 0.15] [--min-area 30]

Saídas em <pasta>:
  quadros/q_00.00.jpg …   um quadro a cada 0,25 s, na resolução do vídeo
  quadros/folha.jpg       folha de contato (16 quadros) para olhar de uma vez
  movimento.png           mapa de calor da energia sobre o 1º quadro, com as regiões numeradas
  curvas.png              a atividade de cada região ao longo do tempo
  regioes.json            cada região: caixa (px da referência), área, energia, curva, picos, período, quadro de pico
  mascaras.npz            a máscara exata de cada região (480x270), que o comparar_vida.py usa
  pico/rNN.jpg            o quadro de maior atividade de cada região, com a caixa marcada
  paleta.json             as cores dominantes do 1º quadro (hex + fração)

"Energia" = desvio temporal da luminância por pixel, menos o piso de ruído do vídeo (0 a 255). É a mesma conta do
comparar_vida.py, então dá para comparar a página com o vídeo região por região.
Não sabe O QUE se mexe nem COMO: isso é o descrever_video.py e os seus olhos na folha.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

import _comum as C

CORES = ['#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4', '#42d4f4', '#f032e6', '#9a6324', '#469990', '#800000',
         '#808000', '#000075']


def periodo(curva: np.ndarray, fps: float) -> float | None:
    """Período dominante (s) pela autocorrelação, se houver um claro."""
    c = curva - curva.mean()
    if c.std() < 1e-6 or len(c) < 12:
        return None
    ac = np.correlate(c, c, 'full')[len(c) - 1:]
    ac /= ac[0]
    minimo, maximo = int(fps * 0.3), len(ac) * 2 // 3
    # o 1º pico de verdade (máximo local), não a borda da busca
    candidatos = [k for k in range(max(minimo, 1), maximo - 1) if ac[k] >= ac[k - 1] and ac[k] >= ac[k + 1]]
    if not candidatos:
        return None
    k = max(candidatos, key=lambda i: ac[i])
    if ac[k] < 0.3:
        return None
    return round(k / fps, 2)


def picos(curva: np.ndarray, fps: float, n: int = 4) -> list[float]:
    if curva.max() <= 0:
        return []
    alto = curva > curva.mean() + curva.std()
    rotulos, qtd = ndimage.label(alto)
    tempos = []
    for i in range(1, qtd + 1):
        idx = np.where(rotulos == i)[0]
        tempos.append((float(curva[idx].max()), idx[int(np.argmax(curva[idx]))] / fps))
    return [round(float(t), 2) for _, t in sorted(tempos, reverse=True)[:n]]


def dividir(suave: np.ndarray, mascara: np.ndarray, corte: float, maximo: int, nivel: int = 0) -> list[np.ndarray]:
    """Componentes da máscara; o que passa de `maximo` px se divide subindo o limiar (núcleo, partículas e barras
    viram regiões diferentes em vez de uma mancha só). O que sobra fraco de uma divisão vira uma região 'difusa'."""
    rotulos, qtd = ndimage.label(mascara)
    partes = []
    for i in range(1, qtd + 1):
        comp = rotulos == i
        if comp.sum() <= maximo or nivel >= 3:
            partes.append(comp)
            continue
        alto = comp & ndimage.binary_opening(suave > corte * 2, iterations=1)
        filhos = dividir(suave, alto, corte * 2, maximo, nivel + 1) if alto.any() else []
        if len(filhos) < 2:
            partes.append(comp)
            continue
        partes += filhos
        resto = comp & ~ndimage.binary_dilation(np.logical_or.reduce(filhos), iterations=2)
        if resto.sum() > maximo // 4:
            partes.append(resto)
    return partes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('video', type=Path)
    ap.add_argument('pasta', type=Path)
    ap.add_argument('--largura-ref', type=int, default=1536, help='largura da reference.png (as caixas saem nessa escala)')
    ap.add_argument('--limiar', type=float, default=0.15, help='fração do p99 da energia que conta como movimento')
    ap.add_argument('--min-area', type=int, default=30, help='área mínima da região, em px da análise (480x270)')
    a = ap.parse_args()

    info = C.info_video(a.video)
    fps = info['fps']
    (a.pasta / 'quadros').mkdir(parents=True, exist_ok=True)
    (a.pasta / 'pico').mkdir(parents=True, exist_ok=True)

    # quadros a cada 0,25 s (resolução cheia) + folha
    C.ffmpeg('-i', str(a.video), '-vf', 'fps=4', '-q:v', '3', str(a.pasta / 'quadros' / 'q_%03d.jpg'))
    for i, q in enumerate(sorted((a.pasta / 'quadros').glob('q_[0-9][0-9][0-9].jpg'))):
        q.replace(q.with_name(f'q_{i * 0.25:05.2f}.jpg'))
    n_folha = 16
    C.ffmpeg('-i', str(a.video), '-vf', f'fps={n_folha / info["duracao"]:.4f},scale=480:-2,tile=4x4', '-frames:v', '1',
             '-q:v', '3', str(a.pasta / 'quadros' / 'folha.jpg'))

    quadros = C.ler_quadros(a.video)
    T, H, W, _ = quadros.shape
    escala = a.largura_ref / W
    energia, piso = C.energia_por_pixel(quadros)
    suave = ndimage.gaussian_filter(energia, 1.2)
    corte = max(float(np.percentile(suave, 99)) * a.limiar, 0.8)
    mascara = ndimage.binary_closing(suave > corte, iterations=1)
    partes = dividir(suave, mascara, corte, maximo=int(W * H * 0.05))

    lum = C.luminancia(quadros)
    mediana = np.median(lum, axis=0)
    regioes = []
    for comp in partes:
        area = int(comp.sum())
        if area < a.min_area:
            continue
        fatia = ndimage.find_objects(comp.astype(np.int32))[0]
        sel = comp[fatia]
        ys, xs = fatia
        curva = np.abs(lum[:, ys, xs] - mediana[ys, xs])[:, sel].mean(axis=1)
        regioes.append({'area_analise': area, 'fatia': (ys.start, ys.stop, xs.start, xs.stop), 'mascara': comp,
                        'energia': float(energia[fatia][sel].mean()), 'curva': curva,
                        'difusa': bool(sel.mean() < 0.25)})
    regioes.sort(key=lambda r: r['energia'] * r['area_analise'], reverse=True)

    saida = []
    base = Image.fromarray(quadros[0]).convert('RGB')
    calor = np.clip(energia / max(float(energia.max()), 1e-6), 0, 1)
    sobre = np.array(base, np.float32) * 0.45
    sobre[..., 0] += calor * 255 * 0.9
    sobre[..., 1] += calor * 120 * 0.9
    mapa = Image.fromarray(np.clip(sobre, 0, 255).astype(np.uint8)).resize((W * 2, H * 2), Image.NEAREST)
    d = ImageDraw.Draw(mapa)
    for n, r in enumerate(regioes, start=1):
        y0, y1, x0, x1 = r['fatia']
        cor = CORES[(n - 1) % len(CORES)]
        d.rectangle([x0 * 2, y0 * 2, x1 * 2, y1 * 2], outline=cor, width=2)
        d.text((x0 * 2 + 3, y0 * 2 + 2), f'r{n:02d}', fill=cor)
        k = int(np.argmax(r['curva']))
        pico = Image.fromarray(quadros[k]).resize((W * 2, H * 2))
        ImageDraw.Draw(pico).rectangle([x0 * 2, y0 * 2, x1 * 2, y1 * 2], outline=cor, width=3)
        pico.save(a.pasta / 'pico' / f'r{n:02d}.jpg', quality=88)
        saida.append({
            'id': f'r{n:02d}',
            'caixa': [round(x0 * escala), round(y0 * escala), round((x1 - x0) * escala), round((y1 - y0) * escala)],
            'caixa_analise': [x0, y0, x1 - x0, y1 - y0],
            'area': round(r['area_analise'] * escala * escala),
            'difusa': r['difusa'],
            'energia': round(r['energia'], 2),
            'pico_s': round(k / fps, 2),
            'picos_s': picos(r['curva'], fps),
            'periodo_s': periodo(r['curva'], fps),
            'curva': [round(float(v), 2) for v in r['curva'][::max(1, round(fps / 12))]],
        })
    mapa.save(a.pasta / 'movimento.png')

    # curvas
    cw, ch = 960, 60 + 34 * max(1, len(saida))
    img = Image.new('RGB', (cw, ch), 'white')
    d = ImageDraw.Draw(img)
    d.text((10, 8), f'atividade por região · {info["duracao"]:.2f} s · {fps:.0f} fps', fill='black')
    for n, r in enumerate(regioes, start=1):
        y = 40 + (n - 1) * 34
        c = r['curva'] / max(float(r['curva'].max()), 1e-6)
        pts = [(60 + i * (cw - 80) / max(1, len(c) - 1), y + 28 - v * 26) for i, v in enumerate(c)]
        d.text((10, y + 10), f'r{n:02d}', fill=CORES[(n - 1) % len(CORES)])
        d.line(pts, fill=CORES[(n - 1) % len(CORES)], width=2)
    img.save(a.pasta / 'curvas.png')

    # paleta
    pal = base.resize((240, 135)).quantize(colors=12, method=Image.Quantize.MEDIANCUT)
    cores = pal.getpalette()[:36]
    contagem = sorted(pal.getcolors(), reverse=True)
    paleta = [{'hex': '#%02x%02x%02x' % tuple(cores[i * 3:i * 3 + 3]), 'fracao': round(c / (240 * 135), 3)}
              for c, i in contagem]

    # as máscaras exatas (a caixa de uma região difusa engole as vizinhas; o comparador usa a máscara)
    np.savez_compressed(a.pasta / 'mascaras.npz', **{f'r{n:02d}': r['mascara'] for n, r in enumerate(regioes, start=1)})
    energia_global = float(energia.mean())
    C.gravar_json(a.pasta / 'regioes.json', {
        'video': str(a.video), 'duracao': round(info['duracao'], 3), 'fps': round(fps, 3),
        'resolucao_video': [info['largura'], info['altura']], 'largura_ref': a.largura_ref,
        'piso_ruido': round(piso, 3), 'energia_global': round(energia_global, 3), 'regioes': saida})
    C.gravar_json(a.pasta / 'paleta.json', paleta)

    print(f'{len(saida)} regiões · energia global {energia_global:.2f} · piso de ruído {piso:.2f} · '
          f'{info["duracao"]:.2f} s a {fps:.0f} fps')
    for r in saida[:12]:
        per = f' · período {r["periodo_s"]} s' if r['periodo_s'] else ''
        dif = ' (difusa)' if r['difusa'] else ''
        print(f'  {r["id"]}  caixa {r["caixa"]}{dif}  energia {r["energia"]:.1f}  picos {r["picos_s"]}{per}')
    print(f'Abra: {a.pasta / "movimento.png"} e {a.pasta / "quadros" / "folha.jpg"}')


if __name__ == '__main__':
    main()
