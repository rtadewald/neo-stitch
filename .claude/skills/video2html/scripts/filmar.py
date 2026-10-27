# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright"]
# ///
"""Filma ou fotografa a página com RELÓGIO VIRTUAL: cada quadro vale exatamente 1/fps, por mais que o print demore.

    uv run filmar.py <url> <saida.mp4> [--segundos 6] [--fps 24] [--antes "JS"] [--semente 7]
    uv run filmar.py <url>?estatico <saida.png> --foto

Antes de qualquer script da página, troca requestAnimationFrame, setTimeout/setInterval, performance.now, Date.now e
Math.random (com semente) por versões que só andam quando o filmador manda; animações CSS/WAAPI são pausadas e
posicionadas pelo mesmo tempo. Resultado: GSAP, Canvas, WebGL e CSS saem lisos e iguais de uma rodada para a outra.
Nunca grave a página em tempo real (screencast perde e repete quadros).

Também grava <saida>.log.json com os erros e avisos do console e as requisições que falharam. Erro de JS = página
inválida: corrija antes de comparar qualquer coisa.

Requer Google Chrome instalado (Playwright channel="chrome") e ffmpeg no PATH.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import _comum as C

RELOGIO = r"""
(() => {
  let now = 0;
  const T0 = 1767225600000;  // data fixa: relógio e "hoje" iguais em toda filmagem
  const rafs = new Map(); let rafSeq = 0;
  const timers = new Map(); let timerSeq = 0;
  const born = new WeakMap();
  let s = __SEMENTE__ >>> 0;
  Math.random = () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const run = (fn, args) => { try { if (typeof fn === 'function') fn.apply(window, args); else (0, eval)(String(fn)); }
    catch (e) { console.error('[relogio] ' + ((e && e.stack) || e)); } };
  const addTimer = (fn, ms, args, repeat) => { const id = ++timerSeq; const d = Math.max(repeat ? 1 : 0, Number(ms) || 0);
    timers.set(id, { at: now + d, fn, args, every: repeat ? d : 0 }); return id; };
  const RealDate = Date;
  performance.now = () => now;
  function FakeDate(...a) {
    if (!new.target) return new RealDate(T0 + now).toString();
    return a.length ? new RealDate(...a) : new RealDate(T0 + now);
  }
  FakeDate.prototype = RealDate.prototype;
  FakeDate.now = () => T0 + now; FakeDate.UTC = RealDate.UTC; FakeDate.parse = RealDate.parse;
  window.Date = FakeDate;
  window.requestAnimationFrame = fn => { const id = ++rafSeq; rafs.set(id, fn); return id; };
  window.cancelAnimationFrame = id => { rafs.delete(id); };
  window.setTimeout = (fn, ms, ...args) => addTimer(fn, ms, args, false);
  window.setInterval = (fn, ms, ...args) => addTimer(fn, ms, args, true);
  window.clearTimeout = window.clearInterval = id => { timers.delete(id); };
  function syncAnimations() {
    for (const a of document.getAnimations()) {
      if (!born.has(a)) born.set(a, now);
      const t = now - born.get(a);
      try { a.pause(); const end = a.effect ? a.effect.getComputedTiming().endTime : Infinity;
        if (Number.isFinite(end) && t >= end) a.finish(); else a.currentTime = t; } catch (e) { /* removida */ }
    }
  }
  window.__relogio = {
    now: () => now,
    step(ms) {
      const target = now + ms;
      for (let guard = 0; guard < 5000; guard++) {
        let pick = null, pickId = 0;
        for (const [id, t] of timers) if (t.at <= target && (!pick || t.at < pick.at)) { pick = t; pickId = id; }
        if (!pick) break;
        now = Math.max(now, pick.at);
        if (pick.every) pick.at += pick.every; else timers.delete(pickId);
        run(pick.fn, pick.args);
      }
      now = target;
      const due = [...rafs.values()]; rafs.clear();
      for (const fn of due) run(fn, [now]);
      syncAnimations();
    },
  };
})();
"""


def abrir(p, url: str, largura: int, altura: int, semente: int, escala: float = 1):
    nav = p.chromium.launch(channel='chrome', args=['--use-angle=d3d11', '--enable-gpu-rasterization',
                                                    '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'])
    pag = nav.new_page(viewport={'width': largura, 'height': altura}, device_scale_factor=escala)
    log = {'erros': [], 'avisos': [], 'falhas': [], 'requisicoes': []}
    pag.on('console', lambda m: (log['erros'] if m.type == 'error' else log['avisos']).append(m.text)
           if m.type in ('error', 'warning') else None)
    pag.on('pageerror', lambda e: log['erros'].append(f'pageerror: {e}'))
    pag.on('requestfailed', lambda r: log['falhas'].append(f'{r.url} {r.failure}'))
    pag.on('request', lambda r: log['requisicoes'].append(r.url))
    pag.add_init_script(RELOGIO.replace('__SEMENTE__', str(semente)))
    pag.goto(url, wait_until='load', timeout=60000)
    try:
        pag.evaluate('document.fonts.ready.then(() => true)')
    except Exception:  # noqa: BLE001
        pass
    pag.wait_for_load_state('networkidle', timeout=20000)
    return nav, pag, log


def passo(pag, ms: float) -> None:
    pag.evaluate(f'window.__relogio.step({ms})')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('url')
    ap.add_argument('saida', type=Path)
    ap.add_argument('--foto', action='store_true', help='um PNG depois de 0,5 s de relógio (use com ?estatico)')
    ap.add_argument('--segundos', type=float, default=6)
    ap.add_argument('--fps', type=float, default=24)
    ap.add_argument('--largura', type=int, default=1536)
    ap.add_argument('--altura', type=int, default=864)
    ap.add_argument('--escala', type=float, default=1, help='device scale factor (2 = print nítido para zoom)')
    ap.add_argument('--antes', default='', help='JS rodado depois de carregar e antes de filmar')
    ap.add_argument('--aquecer', type=float, default=0.5, help='segundos de relógio antes do 1º quadro')
    ap.add_argument('--semente', type=int, default=7)
    a = ap.parse_args()

    a.saida.parent.mkdir(parents=True, exist_ok=True)
    dt = 1000 / a.fps
    with sync_playwright() as p:
        nav, pag, log = abrir(p, a.url, a.largura, a.altura, a.semente, a.escala)
        if a.antes:
            try:
                pag.evaluate(f'(() => {{ {a.antes}\n; return null }})()')
            except Exception as e:  # noqa: BLE001
                log['erros'].append(f'--antes: {e}')
        for _ in range(max(1, round(a.aquecer * 1000 / dt))):
            passo(pag, dt)
        if a.foto:
            pag.screenshot(path=str(a.saida))
        else:
            C.exigir('ffmpeg')
            n = round(a.segundos * a.fps)
            enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'image2pipe', '-framerate', f'{a.fps}',
                                    '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p',
                                    '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-movflags', '+faststart',
                                    str(a.saida)], stdin=subprocess.PIPE)
            for i in range(n):
                enc.stdin.write(pag.screenshot(type='jpeg', quality=93))
                passo(pag, dt)
                if i % max(1, round(a.fps)) == 0:
                    print(f'\r  {i / a.fps:5.1f} / {a.segundos:.1f} s', end='', flush=True)
            enc.stdin.close()
            enc.wait()
            print()
        tem_vida = pag.evaluate('!!(window.vida && window.vida.ocioso)')
        nav.close()

    log['requisicoes'] = sorted(set(log['requisicoes']))
    log['vida'] = tem_vida
    C.gravar_json(a.saida.with_suffix(a.saida.suffix + '.log.json'), log)
    print(f'{a.saida} · {len(log["erros"])} erro(s) · {len(log["falhas"])} falha(s) de rede · window.vida.ocioso: '
          f'{"sim" if tem_vida else "NÃO"}')
    for e in log['erros'][:8]:
        print(f'  ERRO {e[:300]}')
    if log['erros']:
        sys.exit(1)


if __name__ == '__main__':
    main()
