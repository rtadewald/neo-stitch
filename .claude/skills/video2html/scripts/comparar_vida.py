# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "pillow"]
# ///
"""Fase de vida: o vídeo da página contra o vídeo de referência, região por região. Pega "zero animação" na hora.

    uv run comparar_vida.py <video-ref.mp4> <html.mp4> <pasta> --regioes analise/regioes.json [--vida vida.json]

Para cada região do ler_video.py, mede a ENERGIA (a mesma conta: desvio temporal da luminância menos o piso de ruído)
nos dois vídeos e divide: razão = energia da página / (energia do vídeo × alvo).
  PARADO     razão < 0,25   o vídeo mexe ali e a página não
  FRACO      razão < 0,60   mexe, mas tão pouco que não se lê
  OK         0,60 a 1,80
  EXAGERADO  razão > 1,80   mexe muito mais que o vídeo
  ÁSPERO     mexe certo, mas o contraste fino do quadro ficou > 1,35x o do vídeo (ruído, "vermes")
  LISO       mexe certo, mas o contraste fino ficou < 0,7x o do vídeo (borrão, fantasma de duas fases)
A textura (|lum - lum desfocada| na média do tempo) existe porque energia sozinha aprova borrão e ruído: os dois mexem.
Só vale em regiões com alvo 1,0 (o elemento contido de propósito difere do vídeo por definição).
O alvo de cada região vem do vida.json (padrão 1,0). Um elemento contido de propósito ("pulsa de leve") declara
alvo menor; um artefato do vídeo (rótulo que muda, anel neon recusado) declara "artefato": true e sai da conta.
Um elemento estatístico (campo de partículas, faíscas, chuva) declara "agregar": true: as caixinhas dele em volta de
uma gota só medem sorte (a gota da página nunca passa no mesmo lugar), então ele é julgado pela energia da área toda.

Saídas em <pasta>: movimento.json (o relatório), movimento.txt, pares.jpg (vídeo | página a cada 0,5 s), lado-a-lado.mp4.
Passa (saída 0) quando nenhuma região conta como PARADO ou FRACO e a energia global fica entre 0,6 e 1,8 do alvo.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

import _comum as C


def parado(quadros: np.ndarray) -> float:
    """Fração dos quadros em que a tela quase não muda em relação ao anterior."""
    lum = C.luminancia(quadros)
    passo = np.abs(np.diff(lum, axis=0)).mean(axis=(1, 2))
    return float((passo < 0.12).mean()) if len(passo) else 1.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('ref', type=Path)
    ap.add_argument('html', type=Path)
    ap.add_argument('pasta', type=Path)
    ap.add_argument('--regioes', type=Path, required=True, help='regioes.json do ler_video.py')
    ap.add_argument('--vida', type=Path, help='vida.json com alvos e artefatos por elemento')
    a = ap.parse_args()

    meta = C.ler_json(a.regioes)
    vida = C.ler_json(a.vida, {'elementos': []})
    alvo_de, nome_de, artefato, agregado = {}, {}, set(), {}
    for el in vida.get('elementos', []):
        for rid in el.get('regioes', []):
            nome_de[rid] = el.get('nome', rid)
            if el.get('artefato'):
                artefato.add(rid)
            else:
                alvo_de[rid] = float(el.get('alvo', 1.0))
                if el.get('agregar'):
                    agregado[rid] = el.get('nome', rid)

    info_ref = C.info_video(a.ref)
    dur = info_ref['duracao']
    qr = C.ler_quadros(a.ref, fps=24)
    qh = C.ler_quadros(a.html, fps=24, ate=dur)
    er, _ = C.energia_por_pixel(qr)
    eh, _ = C.energia_por_pixel(qh)
    # textura: o contraste fino DENTRO do quadro (|lum - lum desfocada|), na média do tempo. Energia sozinha aceita
    # borrão (que mexe) e ruído (que mexe muito); a textura pega os dois: a página tem que ter o grão do vídeo
    def textura(q):
        lum = C.luminancia(q)
        return np.mean([np.abs(f - ndimage.gaussian_filter(f, 1.5)) for f in lum], axis=0)
    tr, th = textura(qr), textura(qh)

    arq_mascaras = a.regioes.with_name('mascaras.npz')
    mascaras = dict(np.load(arq_mascaras)) if arq_mascaras.is_file() else {}
    linhas, relatorio, ruins = [], [], []
    soma_ref = soma_html = soma_alvo = 0.0
    for r in meta['regioes']:
        rid = r['id']
        x, y, w, h = r['caixa_analise']
        m = mascaras.get(rid)
        if m is None:  # regioes.json antigo, sem máscara: usa a caixa
            m = np.zeros(er.shape, bool)
            m[y:y + h, x:x + w] = True
        e_ref = float(er[m].mean())
        e_html = float(eh[m].mean())
        tx = float(th[m].mean()) / max(float(tr[m].mean()), 1e-6)
        w, h = int(m.sum()), 1
        if rid in artefato:
            estado, razao, alvo = 'ARTEFATO', None, 0.0
        else:
            alvo = alvo_de.get(rid, 1.0)
            razao = e_html / max(e_ref * alvo, 1e-6)
            estado = 'PARADO' if razao < 0.25 else 'FRACO' if razao < 0.6 else 'EXAGERADO' if razao > 1.8 else 'OK'
            # textura só vale onde o alvo é o vídeo (elemento contido de propósito difere por definição)
            if estado == 'OK' and alvo >= 1.0 and rid not in agregado:
                if tx > 1.35:
                    estado = 'ÁSPERO'   # ruído/vermes: mexe, mas não é a fumaça do vídeo
                elif tx < 0.7:
                    estado = 'LISO'     # borrão/fantasma: mexe, mas perdeu a nitidez
            peso = w * h
            soma_ref += e_ref * peso
            soma_alvo += e_ref * alvo * peso
            soma_html += e_html * peso
        if rid in agregado and estado not in ('ARTEFATO',):
            estado = estado.lower()  # julgado pelo elemento inteiro, abaixo
        elif estado in ('PARADO', 'FRACO', 'ÁSPERO', 'LISO'):
            ruins.append(rid)
        relatorio.append({'id': rid, 'elemento': nome_de.get(rid, ''), 'caixa': r['caixa'], 'energia_ref': round(e_ref, 2),
                          'energia_html': round(e_html, 2), 'alvo': alvo, 'razao': None if razao is None else round(razao, 2),
                          'textura': round(tx, 2), 'estado': estado})
        rz = '   -  ' if razao is None else f'{razao:5.2f}x'
        linhas.append(f'{rid}  {estado:9s} {rz}  ref {e_ref:5.1f}  página {e_html:5.1f}  alvo {alvo:.2f}  '
                      f'textura {tx:4.2f}x  {nome_de.get(rid, "")}')

    # elementos estatísticos (campo de partículas, chuva, faíscas): o lugar exato de cada gota é sorte; vale a energia
    # somada da área toda do elemento, não a de cada caixinha
    for nome in sorted(set(agregado.values())):
        ids = [rid for rid, n in agregado.items() if n == nome]
        uniao = np.zeros(er.shape, bool)
        for rid in ids:
            m = mascaras.get(rid)
            if m is None:
                x, y, w, h = next(r['caixa_analise'] for r in meta['regioes'] if r['id'] == rid)
                m = np.zeros(er.shape, bool)
                m[y:y + h, x:x + w] = True
            uniao |= m
        alvo = alvo_de[ids[0]]
        e_ref, e_html = float(er[uniao].mean()), float(eh[uniao].mean())
        razao = e_html / max(e_ref * alvo, 1e-6)
        estado = 'PARADO' if razao < 0.25 else 'FRACO' if razao < 0.6 else 'EXAGERADO' if razao > 1.8 else 'OK'
        if estado in ('PARADO', 'FRACO'):
            ruins.append(nome)
        relatorio.append({'id': '+'.join(ids), 'elemento': nome, 'agregado': True, 'energia_ref': round(e_ref, 2),
                          'energia_html': round(e_html, 2), 'alvo': alvo, 'razao': round(razao, 2), 'estado': estado})
        linhas.append(f'[{nome}] agregado ({len(ids)} regiões)  {estado:9s} {razao:5.2f}x  ref {e_ref:5.1f}  '
                      f'página {e_html:5.1f}  alvo {alvo:.2f}')

    global_razao = soma_html / max(soma_alvo, 1e-6)
    p_ref, p_html = parado(qr), parado(qh)
    passou = not ruins and 0.6 <= global_razao <= 1.8
    cab = (f'energia nas regiões vivas: página/alvo = {global_razao:.2f}x · tempo parado: vídeo {p_ref:.0%}, '
           f'página {p_html:.0%} · {"PASSOU" if passou else "NÃO PASSOU"}')

    # pares a cada 0,5 s
    a.pasta.mkdir(parents=True, exist_ok=True)
    tempos = np.arange(0, dur, 0.5)
    cel_w, cel_h = 480, 270
    folha = Image.new('RGB', (cel_w * 2 + 30, (cel_h + 22) * len(tempos)), 'white')
    d = ImageDraw.Draw(folha)
    for k, t in enumerate(tempos):
        i = min(int(t * 24), len(qr) - 1)
        j = min(int(t * 24), len(qh) - 1)
        y = k * (cel_h + 22)
        d.text((6, y + 4), f'{t:.1f} s   vídeo | página', fill='black')
        folha.paste(Image.fromarray(qr[i]), (0, y + 20))
        folha.paste(Image.fromarray(qh[j]), (cel_w + 30, y + 20))
    folha.save(a.pasta / 'pares.jpg', quality=85)
    C.ffmpeg('-i', str(a.ref), '-i', str(a.html), '-filter_complex',
             f'[0:v]scale=768:432,setsar=1,fps=24[a];[1:v]scale=768:432,setsar=1,fps=24[b];[a][b]hstack=inputs=2',
             '-t', f'{dur:.3f}', '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p', str(a.pasta / 'lado-a-lado.mp4'))

    C.gravar_json(a.pasta / 'movimento.json', {'passou': passou, 'energia_global_razao': round(global_razao, 2),
                                          'parado_ref': round(p_ref, 3), 'parado_html': round(p_html, 3),
                                          'regioes': relatorio})
    (a.pasta / 'movimento.txt').write_text(cab + '\n\n' + '\n'.join(linhas) + '\n', encoding='utf-8')
    print(cab)
    for linha in linhas:
        print('  ' + linha)
    if ruins:
        print(f'  sem vida suficiente: {", ".join(ruins)} · abra {a.pasta / "pares.jpg"} e {a.pasta / "lado-a-lado.mp4"}')
    sys.exit(0 if passou else 1)


if __name__ == '__main__':
    main()
