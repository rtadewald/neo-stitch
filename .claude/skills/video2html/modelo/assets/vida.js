/* O contrato da página viva (o checar.py confere tudo isto):

   window.vida = { ocioso, interagiu, mov, estatico }
     ocioso     a linha do tempo GSAP do estado ocioso, repeat: -1, montada a partir do vida.md
     interagiu  pausa o ocioso e o retoma sozinho depois de RETOMAR_S
     mov        as funções de movimento (uma por elemento vivo); o ocioso e a interação chamam as MESMAS
     estatico   true em ?estatico: tudo congelado no estado exato da reference.png

   Regras: o tempo vem do relógio (gsap.ticker / requestAnimationFrame / performance.now). Nada de Math.random
   sem passar por `aleatorio` (semente fixa). Em ?estatico ninguém lê o relógio: cada módulo desenha t = 0. */

const params = new URLSearchParams(location.search);
const ESTATICO = params.has('estatico');
if (ESTATICO) document.documentElement.setAttribute('data-estatico', '');

const W = 1536, H = 864;           // = reference.png
const RETOMAR_S = 6;

/* palco: escala para caber, sem distorcer */
function ajustar() {
  const k = Math.min(innerWidth / W, innerHeight / H);
  document.documentElement.style.setProperty('--k', String(k));
}
addEventListener('resize', ajustar);
ajustar();

/* aleatório com semente (mulberry32): o mesmo a cada carga */
export function aleatorio(semente = 7) {
  let s = semente >>> 0;
  return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

/* relógio único para módulos procedurais (canvas, WebGL): desenhar(t) é função pura de t */
const modulos = [];
export function registrar(desenhar) { modulos.push(desenhar); desenhar(0); }
gsap.ticker.add(() => {
  const t = ESTATICO ? 0 : gsap.ticker.time;
  for (const d of modulos) d(t);
});

/* funções de movimento: uma por elemento do vida.md, devolvem um tween/timeline para entrar no ocioso */
const mov = {
  // exemplo: um brilho que "enche" a linha, segura e decai (luz que passa num caminho fraco em repouso)
  feixe(id, { dur = 0.9, segura = 1.2 } = {}) {
    const el = document.getElementById(id);
    if (!el) return gsap.timeline();
    const L = el.getTotalLength ? el.getTotalLength() : 100;
    gsap.killTweensOf(el);
    return gsap.timeline()
      .set(el, { strokeDasharray: L, strokeDashoffset: L, opacity: 1 })
      .to(el, { strokeDashoffset: 0, duration: dur, ease: 'power2.out' })
      .to(el, { opacity: 0.25, duration: 0.8, ease: 'power1.in' }, `+=${segura}`);
  },
};

/* a linha do tempo ociosa: os tempos saem do vida.md (que saiu do ler_video.py), nunca de chute */
const ocioso = gsap.timeline({ repeat: -1, paused: ESTATICO });
// ocioso.add(mov.feixe('linha-comercial'), 1.1)
//       .add(mov.feixe('linha-prospeccao'), 2.2)
//       .add(() => {}, 9);   // duração do loop; o tempo 0 reinicia o estado (o que ligou no meio, desliga)

let retomada = null;
function interagiu() {
  if (ESTATICO) return;
  ocioso.pause();
  clearTimeout(retomada);
  retomada = setTimeout(() => ocioso.play(), RETOMAR_S * 1000);
}

window.vida = { ocioso, interagiu, mov, estatico: ESTATICO };
