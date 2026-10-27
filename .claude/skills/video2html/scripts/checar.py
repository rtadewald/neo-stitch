# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright"]
# ///
"""Confere o contrato da página antes de qualquer comparação. Página que reprova aqui não vale ser filmada.

    uv run checar.py <url do index.html> [--pasta <vN>]

Estático (lê os arquivos da --pasta):
  - index.html e assets/ existem; nada de <video>, <iframe> nem GIF como camada viva
  - scripts e folhas só da própria pasta ou de CDN com versão fixa (jsdelivr, unpkg, cdnjs) e Google Fonts
Em execução (Chrome com o relógio do filmar.py):
  - zero erro de console e zero requisição falhada
  - window.vida.ocioso existe (a linha do tempo ociosa) e window.vida.interagiu é função
  - ?estatico marca <html data-estatico> e fica parado: dois instantes diferentes dão o mesmo print
  - o modo normal mexe: 0,5 s e 2,0 s dão prints diferentes
  - mesma semente, mesmo instante → mesmo print (determinismo; WebGL pode variar ±1 nível, vira aviso)
  - nenhum texto cortado (overflow escondido engolindo letras)
Sai com 1 se algo obrigatório falhar.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

import _comum as C
from filmar import abrir, passo

CDN_OK = ('cdn.jsdelivr.net', 'unpkg.com', 'cdnjs.cloudflare.com', 'fonts.googleapis.com', 'fonts.gstatic.com')

TEXTO_CORTADO = r"""
(() => {
  const out = [];
  for (const el of document.querySelectorAll('body *')) {
    if (!el.childNodes.length || ![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const esconde = /(hidden|clip)/.test(cs.overflow + cs.overflowX + cs.overflowY) || cs.textOverflow === 'ellipsis';
    if (esconde && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 2))
      out.push(el.textContent.trim().slice(0, 60));
  }
  return out.slice(0, 20);
})()
"""


def com_param(url: str, param: str) -> str:
    return url + ('&' if '?' in url else '?') + param


def hash_print(pag) -> str:
    return hashlib.sha1(pag.screenshot(type='png')).hexdigest()[:12]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('url')
    ap.add_argument('--pasta', type=Path, help='a pasta vN (para as checagens estáticas)')
    a = ap.parse_args()
    falhas, avisos, ok = [], [], []

    if a.pasta:
        idx = a.pasta / 'index.html'
        if not idx.is_file():
            falhas.append('falta index.html')
        else:
            html = idx.read_text(encoding='utf-8', errors='ignore')
            todo = html + ''.join(p.read_text(encoding='utf-8', errors='ignore')
                                  for p in (a.pasta / 'assets').rglob('*') if p.suffix in ('.js', '.css', '.mjs'))
            if re.search(r'<(video|iframe)\b', todo, re.I):
                falhas.append('<video>/<iframe> na página: tudo que se mexe é código')
            if re.search(r'\.gif["\')]', todo, re.I):
                avisos.append('GIF referenciado: só vale para algo que não é parte da vida')
            for src in re.findall(r'(?:src|href)=["\']([^"\']+)["\']', html) + re.findall(r'from\s+["\']([^"\']+)["\']', todo):
                u = urlparse(src)
                if u.scheme in ('http', 'https'):
                    if u.hostname not in CDN_OK:
                        falhas.append(f'recurso de fora da lista: {src}')
                    elif u.hostname in CDN_OK[:3] and not re.search(r'@\d', src):
                        avisos.append(f'CDN sem versão fixa: {src}')
            ok.append('arquivos e origens conferidos')

    with sync_playwright() as p:
        nav, pag, log = abrir(p, a.url, 1536, 864, 7)
        passo(pag, 500)
        contrato = pag.evaluate('({ocioso: !!(window.vida && window.vida.ocioso),'
                                ' interagiu: typeof (window.vida && window.vida.interagiu) === "function"})')
        h05 = hash_print(pag)
        for _ in range(36):
            passo(pag, 1000 / 24)
        h20 = hash_print(pag)
        cortados = pag.evaluate(TEXTO_CORTADO)
        nav.close()
        erros_normal = list(log['erros']) + list(log['falhas'])

        nav, pag, log2 = abrir(p, com_param(a.url, 'estatico'), 1536, 864, 7)
        passo(pag, 500)
        marcado = pag.evaluate('document.documentElement.hasAttribute("data-estatico")')
        e1 = hash_print(pag)
        for _ in range(36):
            passo(pag, 1000 / 24)
        e2 = hash_print(pag)
        nav.close()

        nav, pag, _ = abrir(p, a.url, 1536, 864, 7)
        passo(pag, 500)
        h05b = hash_print(pag)
        nav.close()

    if erros_normal or log2['erros']:
        for e in (erros_normal + log2['erros'])[:6]:
            falhas.append(f'console/rede: {e[:200]}')
    else:
        ok.append('zero erro de console e de rede')
    (ok if contrato['ocioso'] else falhas).append('window.vida.ocioso ' + ('existe' if contrato['ocioso'] else 'NÃO existe'))
    (ok if contrato['interagiu'] else avisos).append('window.vida.interagiu ' + ('existe' if contrato['interagiu'] else 'não existe'))
    (ok if marcado else falhas).append('?estatico ' + ('marca data-estatico' if marcado else 'NÃO marca <html data-estatico>'))
    (ok if e1 == e2 else falhas).append('?estatico ' + ('fica parado' if e1 == e2 else 'MEXE (precisa congelar no estado da imagem)'))
    (ok if h05 != h20 else falhas).append('modo normal ' + ('mexe' if h05 != h20 else 'NÃO MEXE entre 0,5 s e 2,0 s'))
    (ok if h05 == h05b else avisos).append('determinismo ' + ('ok' if h05 == h05b else 'variou (Math.random sem semente? WebGL ±1?)'))
    if cortados:
        falhas.append(f'texto cortado: {cortados[:5]}')
    else:
        ok.append('nenhum texto cortado')

    for t in ok:
        print(f'  ok     {t}')
    for t in avisos:
        print(f'  aviso  {t}')
    for t in falhas:
        print(f'  FALHA  {t}')
    print('PASSOU' if not falhas else f'NÃO PASSOU ({len(falhas)} falha(s))')
    sys.exit(1 if falhas else 0)


if __name__ == '__main__':
    main()
