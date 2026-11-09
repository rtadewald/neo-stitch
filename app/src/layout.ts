import type { EstadoProjeto, No, Pos } from './api'

export const LARG = { brief: 360, tela: 220, pedido: 300 }
export const LEGENDA = 49   // a legenda fixa embaixo dos cartões de mídia (32 × zoom 1.5 + a borda)
const GAP_X = 90
const GAP_Y = 28

/** Largura e altura de um nó de imagem/referência no canvas (paisagem 720, retrato 480): a imagem já nasce grande, para
 *  ser vista sem zoom (o zoom estica também a legenda e os textos). */
export function medidaImagem(no: No): { w: number; h: number } {
  let razao = no.largura && no.altura ? no.largura / no.altura : razaoDe(no.aspecto)
  if (!isFinite(razao) || razao <= 0) razao = 16 / 9
  const w = razao >= 1 ? 720 : 480
  return { w, h: Math.round(w / razao) }
}

export function razaoDe(aspecto?: string): number {
  const [a, b] = (aspecto || '16:9').split(':').map(Number)
  return a && b ? a / b : 16 / 9
}

/** No modo "pontos", o pedido concluído vira um ponto na linha (rascunho, fila e erro continuam como card). */
export const ehPonto = (no: No) => no.tipo === 'pedido' && no.status === 'concluido'
export const PONTO = 26

export function medida(no: No, pontos = false): { w: number; h: number } {
  if (pontos && ehPonto(no)) return { w: PONTO, h: PONTO }
  if (no.tipo === 'imagem' || no.tipo === 'referencia' || no.tipo === 'video' || no.tipo === 'modelo' || no.tipo === 'site' || no.tipo === 'ds') {
    const m = medidaImagem(no)
    return { w: m.w, h: m.h + LEGENDA }
  }
  if (no.tipo === 'brief') return { w: LARG.brief, h: 200 }
  if (no.tipo === 'tela') return { w: LARG.tela, h: 48 }
  return { w: LARG.pedido, h: no.status === 'rascunho' ? 150 : 96 }
}

export type Arvore = {
  pai: Map<string, string>          // filho → pai na árvore
  filhos: Map<string, string[]>     // pai → filhos (em ordem de criação)
  soltos: Set<string>               // referências fora da árvore (posição livre)
  anexos: Map<string, string[]>     // pedido → referências soltas que ele usa (somem/andam com o galho do pedido)
  donoDe: Map<string, string>       // referência solta → o 1º pedido que a usa
  total: Map<string, number>        // quantos descendentes cada nó tem (calculado uma vez por árvore)
}

/**
 * A árvore de ideias: brief → telas → pedidos → imagens → pedidos → imagens…
 * O pai de um pedido é a imagem de onde ele saiu (a 1ª entrada que é imagem ou vídeo); sem imagem, a referência (que então
 * pende da tela) se ela não tiver posição própria; senão, a tela. As outras entradas viram arestas tracejadas.
 */
export function arvore(nos: No[]): Arvore {
  const porId = new Map(nos.map((n) => [n.id, n]))
  const pai = new Map<string, string>()
  const ordem = [...nos].sort((a, b) => a.id.localeCompare(b.id))
  const ligar = (filho: string, p?: string | null) => {
    if (p && porId.has(p) && !pai.has(filho)) pai.set(filho, p)
  }
  const brief = nos.find((n) => n.tipo === 'brief')
  for (const n of ordem) {
    if (n.tipo === 'tela') ligar(n.id, n.pai || brief?.id)
    if (n.tipo === 'pedido') {
      const ent = (n.entradas || []).map((e) => porId.get(e)).filter(Boolean) as No[]
      // a imagem (ou o vídeo: um pedido pode partir de um quadro dele; ou a página, pelo print) de onde o pedido saiu
      const img = ent.find((e) => e.tipo === 'imagem' || e.tipo === 'video' || e.tipo === 'site')
      const ref = ent.find((e) => e.tipo === 'referencia')
      // referência com posição própria (colada/arrastada pelo usuário) fica onde está: não vira galho da árvore
      if (img) ligar(n.id, img.id)
      else if (ref && !ref.pos) {
        ligar(ref.id, n.tela || ref.tela)
        ligar(n.id, ref.id)
      } else ligar(n.id, n.tela)
    }
    if (n.tipo === 'imagem' || n.tipo === 'video' || n.tipo === 'modelo' || n.tipo === 'site' || n.tipo === 'ds') ligar(n.id, n.pedido)
  }
  const filhos = new Map<string, string[]>()
  for (const n of ordem) {
    const p = pai.get(n.id)
    if (!p) continue
    const fs = filhos.get(p)
    if (fs) fs.push(n.id)
    else filhos.set(p, [n.id])
  }
  // referência solta: sem pai e sem filhos (uma referência com pedidos pendurados é nó da árvore, ex.: a raiz de um recorte)
  const soltos = new Set(nos.filter((n) => n.tipo === 'referencia' && !pai.has(n.id) && !filhos.has(n.id)).map((n) => n.id))
  const anexos = new Map<string, string[]>()
  const donoDe = new Map<string, string>()
  for (const n of ordem) {
    if (n.tipo !== 'pedido') continue
    for (const e of n.entradas || []) if (soltos.has(e) && !donoDe.has(e)) {
      donoDe.set(e, n.id)
      const as = anexos.get(n.id)
      if (as) as.push(e)
      else anexos.set(n.id, [e])
    }
  }
  const total = new Map<string, number>()
  const contar = (id: string): number => {
    const c = total.get(id)
    if (c !== undefined) return c
    const n = (filhos.get(id) || []).reduce((s, f) => s + 1 + contar(f), 0)
    total.set(id, n)
    return n
  }
  for (const id of filhos.keys()) contar(id)
  return { pai, filhos, soltos, anexos, donoDe, total }
}

/**
 * As versões de HTML (impl/<imagem>/<versão>/) como nós da árvore. Cada uma pende de onde saiu: a versão-base (evolução
 * v1 → v1.1), a 1ª imagem ou modelo tirado do vídeo, o vídeo, ou a própria imagem (img-to-html). As outras origens viram
 * arestas tracejadas (`entradas`). O código é <imagem>/<versão>.
 */
export function nosDeSite(estado: EstadoProjeto): No[] {
  const ids = new Set(estado.nos.map((n) => n.id))
  const out: No[] = []
  for (const [img, av] of Object.entries(estado.avancos || {})) {
    if (!ids.has(img)) continue
    const trab = av.trabalhos || {}
    for (const v of av.impl) {
      const t = trab[v]
      const base = t?.base && av.impl.includes(t.base) ? `${img}/${t.base}` : null
      const video = av.origens?.[v] && ids.has(av.origens[v]) ? av.origens[v] : null
      const origens = [...(t?.entradas || []).filter((e) => ids.has(e)), ...(video ? [video] : [])]
      out.push({
        id: `${img}/${v}`, tipo: 'site', criado: t?.inicio || '', pos: null, desloc: t?.desloc ?? null, comentarios: [],
        pedido: base || origens[0] || img, entradas: base ? origens : origens.slice(1),
        nome: t?.agente, estado: t?.estado || 'neutra', site: { img, versao: v, trabalho: t, foto: av.capturas?.[v] },
        ...(t?.captura || av.capturas?.[v] ? { arquivo: `impl/${img}/${v}/${t?.captura || 'captura.png'}` } : {}),
      })
    }
  }
  return out
}

/**
 * A árvore filtrada (o "Filtrar" do topo): só os nós que passam, cada um pendurado no ancestral visível mais perto (sem os
 * pedidos, a imagem liga direto na imagem de onde saiu). `podar`: nós que só ficam se algo abaixo deles ficar (o pedido cujas
 * imagens saíram do filtro). O que está recolhido ou escondido na árvore inteira continua fora.
 */
export function filtrarArvore(nos: No[], a: Arvore, passa: (n: No) => boolean, podar: (n: No) => boolean): { nos: No[]; arv: Arvore } {
  const porId = new Map(nos.map((n) => [n.id, n]))
  const aberto = new Map<string, boolean>()
  const estaAberto = (id: string): boolean => {
    const c = aberto.get(id)
    if (c !== undefined) return c
    const p = a.pai.get(id)
    const pn = p ? porId.get(p) : undefined
    const v = !pn || (!pn.recolhido && !(pn.escondidos || []).includes(id) && estaAberto(p!))
    aberto.set(id, v)
    return v
  }
  const memo = new Map<string, boolean>()
  const abaixo = new Map<string, boolean>()
  const temAbaixo = (id: string): boolean => {
    const c = abaixo.get(id)
    if (c !== undefined) return c
    const v = (a.filhos.get(id) || []).some((f) => fica(f) || temAbaixo(f))
    abaixo.set(id, v)
    return v
  }
  const fica = (id: string): boolean => {
    const c = memo.get(id)
    if (c !== undefined) return c
    const n = porId.get(id)!
    const v = estaAberto(id) && passa(n) && (!podar(n) || temAbaixo(id))
    memo.set(id, v)
    return v
  }
  const dentro = nos.filter((n) => fica(n.id))
  const ids = new Set(dentro.map((n) => n.id))
  const pai = new Map<string, string>()
  for (const n of dentro) {
    let p = a.pai.get(n.id)
    while (p && !ids.has(p)) p = a.pai.get(p)
    if (p) pai.set(n.id, p)
  }
  const filhos = new Map<string, string[]>()
  for (const n of [...dentro].sort((x, y) => x.id.localeCompare(y.id))) {
    const p = pai.get(n.id)
    if (!p) continue
    const fs = filhos.get(p)
    if (fs) fs.push(n.id)
    else filhos.set(p, [n.id])
  }
  const soltos = new Set([...a.soltos].filter((id) => ids.has(id)))
  const anexos = new Map<string, string[]>()
  const donoDe = new Map<string, string>()
  for (const [ped, rs] of a.anexos) {
    if (!ids.has(ped)) continue
    const ok = rs.filter((r) => ids.has(r))
    if (ok.length) anexos.set(ped, ok)
    for (const r of ok) donoDe.set(r, ped)
  }
  const total = new Map<string, number>()
  const contar = (id: string): number => {
    const c = total.get(id)
    if (c !== undefined) return c
    const v = (filhos.get(id) || []).reduce((s, f) => s + 1 + contar(f), 0)
    total.set(id, v)
    return v
  }
  for (const id of filhos.keys()) contar(id)
  return { nos: dentro, arv: { pai, filhos, soltos, anexos, donoDe, total } }
}

/** O recorte a partir de um nó (uma vista): ele, tudo o que saiu dele (com as referências soltas desses pedidos) e os pedidos
 * que o usam como outra entrada (ex.: a 2ª imagem de um pedido), com o que saiu deles. */
export function recorte(a: Arvore, raiz: string, nos: No[]): Set<string> {
  const out = new Set([raiz, ...galhoCompleto(a, raiz)])
  for (const n of nos) {
    if (n.tipo !== 'pedido' || out.has(n.id) || !(n.entradas || []).includes(raiz)) continue
    out.add(n.id)
    for (const x of galhoCompleto(a, n.id)) out.add(x)
  }
  return out
}

/** Tudo o que sai junto quando um nó é apagado: os descendentes + referências soltas usadas pelos pedidos do galho. */
export function galhoCompleto(a: Arvore, id: string): string[] {
  const out: string[] = []
  const ir = (x: string) => {
    for (const r of a.anexos.get(x) || []) if (!out.includes(r)) out.push(r)
    for (const f of a.filhos.get(x) || []) { out.push(f); ir(f) }
  }
  ir(id)
  return out
}

/** O caminho até os nós em `extras` (os pinados): eles + todos os ancestrais (+ referências soltas
 * usadas pelos pedidos do caminho). */
export function caminhoAprovadas(nos: No[], a: Arvore, extras: Set<string> = new Set()): Set<string> {
  const out = new Set<string>()
  for (const n of nos) {
    if (!extras.has(n.id)) continue
    for (let cur: string | undefined = n.id; cur && !out.has(cur); cur = a.pai.get(cur)) out.add(cur)
  }
  for (const id of [...out]) for (const r of a.anexos.get(id) || []) out.add(r)
  return out
}

/** Quantos nós estão escondidos sob este (recolhido = todo o galho; escondidos = esses filhos e o que saiu deles). */
export function ocultosSob(a: Arvore, no: No): number {
  if (no.recolhido) return descendentes(a, no.id)
  return (no.escondidos || []).filter((f) => (a.filhos.get(no.id) || []).includes(f)).reduce((s, f) => s + 1 + descendentes(a, f), 0)
}

/** Quantos descendentes um nó tem (o selo "+N" quando recolhido). */
export function descendentes(a: Arvore, id: string): number {
  return a.total.get(id) || 0
}

// grade: por nível (cada nível numa coluna só) · gradeN: os filhos em colunas de N
export type ModoLayout = 'grade' | 'grade3' | 'grade4' | 'grade5' | 'grade6' | 'grade8'
const GAP_COL = 36
const GAP_PAI_X = 320   // grade: entre colunas quando a de trás tem galho
const GAP_PAI_Y = 140   // entre irmãos empilhados quando um deles tem galho

/**
 * Os nós visíveis e suas posições: árvore da esquerda para a direita, irmãos empilhados, pai centrado nos filhos.
 * Galhos recolhidos somem; `oculto` esconde folhas (ex.: descartadas sem filhos). Referências soltas ficam onde estão.
 * `compacto` (o "Distribuir"): os galhos sobem para os vãos em vez de cada um ocupar uma faixa da altura inteira.
 */
export function layoutArvore(nos: No[], a: Arvore, medidas: Map<string, { w: number; h: number }>, oculto: (n: No) => boolean,
  modo: ModoLayout = 'grade', pontos = false, compacto = false) {
  const porId = new Map(nos.map((n) => [n.id, n]))
  // o ponto tem tamanho fixo (a medida guardada pode ser a do card, de antes de virar ponto)
  const m = (id: string) => {
    const n = porId.get(id)!
    return pontos && ehPonto(n) ? medida(n, true) : medidas.get(id) || medida(n)
  }
  // recolhido: o galho inteiro fecha · escondidos: só esses filhos somem (o "só aprovados" usa isso)
  const visiveisDe = (id: string) => {
    const no = porId.get(id)
    if (no?.recolhido) return []
    const fora = new Set(no?.escondidos || [])
    return (a.filhos.get(id) || []).filter((f) => !fora.has(f) && (!oculto(porId.get(f)!) || (a.filhos.get(f) || []).length))
  }

  // modos grade N×N (3, 4, 5, 6, 8): em TODO nível os filhos — com ou sem galho — vão em colunas de N; cada um ocupa o bloco do
  // próprio galho (largura e altura da subárvore), e as colunas ficam lado a lado. Entre blocos que têm galho o espaço é
  // maior (GAP_PAI_X/Y): um pai não encosta nos filhos do vizinho e não parece filho dele
  const larguras = new Map<string, number>()
  const porCol = Number(modo.slice(5))   // grade N×N: N filhos por coluna (0 no modo por nível)
  const emGradeN = porCol > 0
  const colunas = (id: string) => {
    const fs = visiveisDe(id)
    const cols: string[][] = []
    for (let i = 0; i < fs.length; i += porCol) cols.push(fs.slice(i, i + porCol))
    return cols
  }
  const temGalho = (id: string) => visiveisDe(id).length > 0
  // o espaço entre dois irmãos de uma coluna, e o que vem depois de uma coluna
  const gapY = (a: string, b: string) => (temGalho(a) || temGalho(b) ? GAP_PAI_Y : GAP_Y)
  const gapCol = (c: string[]) => (c.some(temGalho) ? GAP_PAI_X : GAP_COL * 2)
  const altColuna = (c: string[]) => c.reduce((s, f, i) => s + alturas.get(f)! + (i ? gapY(c[i - 1], f) : 0), 0)
  const medir3 = (id: string): { w: number; h: number } => {
    const cols = colunas(id)
    let cw = 0
    let ch = 0
    cols.forEach((c, k) => {
      const tams = c.map((f) => medir3(f))
      cw += Math.max(...tams.map((t) => t.w)) + (k < cols.length - 1 ? gapCol(c) : 0)
      ch = Math.max(ch, altColuna(c))
    })
    const w = m(id).w + (cols.length ? GAP_X + cw : 0)
    const h = Math.max(m(id).h, ch)
    larguras.set(id, w)
    alturas.set(id, h)
    return { w, h }
  }
  const colocar3 = (id: string, x: number, topo: number) => {
    const cols = colunas(id)
    const { w, h } = m(id)
    const H = alturas.get(id)!
    let cx = x + w + GAP_X
    const centros: number[] = []
    for (const c of cols) {
      let y = topo + (H - altColuna(c)) / 2
      c.forEach((f, i) => {
        if (i) y += gapY(c[i - 1], f)
        colocar3(f, cx, y)
        centros.push(pos[f].y + m(f).h / 2)
        y += alturas.get(f)!
      })
      cx += Math.max(...c.map((f) => larguras.get(f)!)) + gapCol(c)
    }
    const centro = centros.length ? (Math.min(...centros) + Math.max(...centros)) / 2 : topo + H / 2
    pos[id] = { x: Math.round(x), y: Math.round(centro - h / 2) }
  }

  const alturas = new Map<string, number>()
  const altura = (id: string): number => {
    if (emGradeN) return medir3(id).h
    const fs = visiveisDe(id)
    fs.forEach(altura)
    const h = Math.max(m(id).h, altColuna(fs))
    alturas.set(id, h)
    return h
  }
  const pos: Record<string, Pos> = {}
  const colocar = (id: string, x: number, topo: number) => {
    if (emGradeN) return colocar3(id, x, topo)
    const fs = visiveisDe(id)
    const { w, h } = m(id)
    const H = alturas.get(id)!
    let y = topo + (H - altColuna(fs)) / 2
    const centros: number[] = []
    fs.forEach((f, i) => {
      if (i) y += gapY(fs[i - 1], f)
      colocar(f, x + w + GAP_X, y)
      centros.push(pos[f].y + m(f).h / 2)
      y += alturas.get(f)!
    })
    const centro = centros.length ? (Math.min(...centros) + Math.max(...centros)) / 2 : topo + H / 2
    pos[id] = { x: Math.round(x), y: Math.round(centro - h / 2) }
  }
  // raízes: o brief (e, por segurança, qualquer nó órfão que não seja referência solta)
  const raizes = nos
    .filter((n) => !a.pai.has(n.id) && !a.soltos.has(n.id))
    .sort((x, y) => (x.tipo === 'brief' ? -1 : y.tipo === 'brief' ? 1 : x.id.localeCompare(y.id)))
  let topo = 0
  for (const r of raizes) {
    altura(r.id)
    colocar(r.id, 0, topo)
    topo += alturas.get(r.id)! + 80
  }

  // por nível: todo o mesmo nível na mesma coluna, em toda a árvore. O nível é a geração, sem contar os pedidos (5 referências
  // numa coluna, as 15 imagens delas na seguinte); os pedidos ficam numa coluna própria, entre as duas
  if (!emGradeN) {
    const col = new Map<string, number>()
    const ir = (id: string, g: number) => {
      const ped = porId.get(id)?.tipo === 'pedido'
      col.set(id, ped ? 2 * g + 1 : 2 * g)
      for (const f of visiveisDe(id)) ir(f, porId.get(f)?.tipo === 'pedido' && !ped ? g : g + 1)
    }
    for (const r of raizes) ir(r.id, 0)
    const larg = new Map<number, number>()
    for (const [id, c] of col) larg.set(c, Math.max(larg.get(c) || 0, m(id).w))
    const xDe = new Map<number, number>()
    let x = 0
    for (const c of [...larg.keys()].sort((p, q) => p - q)) { xDe.set(c, x); x += larg.get(c)! + GAP_X }
    for (const [id, c] of col) pos[id] = { x: xDe.get(c)!, y: pos[id].y }
  }

  // compacto: cada galho sobe até encostar no que já está acima dele, onde as colunas se cruzam (um galho baixinho não
  // fica mais preso embaixo do galho comprido do irmão); depois o pai se recentraliza nos filhos
  type Caixa = { x: number; y: number; w: number; h: number }
  const galho = (id: string): string[] => [id, ...visiveisDe(id).flatMap(galho)]
  const caixa = (id: string): Caixa => ({ ...pos[id], ...m(id) })
  // as pilhas de cada nó (filhos empilhados na mesma coluna), cada uma com os grupos que sobem juntos
  const pilhasDe = (id: string): string[][][] => {
    if (emGradeN) return colunas(id).map((c) => c.map((f) => [f]))
    return [visiveisDe(id).map((f) => [f])]
  }
  const empilhar = (pilha: string[][], gap0: number) => {
    const acima: Caixa[] = []
    let antes: string[] = []
    for (const g of pilha) {
      // blocos com galho guardam o espaço maior (um pai não encosta nos filhos do vizinho)
      const gap = g.some(temGalho) || antes.some(temGalho) ? Math.max(gap0, GAP_PAI_Y) : gap0
      antes = g
      const ids = g.flatMap(galho)
      const cx = ids.map(caixa)
      let dy = Infinity
      for (const a of cx) for (const b of acima)
        if (a.x < b.x + b.w && b.x < a.x + a.w) dy = Math.min(dy, a.y - (b.y + b.h) - gap)
      // encosta no de cima (desce também, se um neto que subiu dentro do grupo invadiu o de cima)
      if (dy !== Infinity && dy) for (const id of ids) pos[id] = { x: pos[id].x, y: pos[id].y - Math.round(dy) }
      acima.push(...ids.map(caixa))
    }
  }
  const meioDe = (ids: string[]) => {
    const cs = ids.map((f) => pos[f].y + m(f).h / 2)
    return (Math.min(...cs) + Math.max(...cs)) / 2
  }
  const compactar = (id: string) => {
    const pilhas = pilhasDe(id)
    for (const f of visiveisDe(id)) compactar(f)
    for (const p of pilhas) empilhar(p, GAP_Y)
    // grade N×N: as colunas encolheram por baixo; realinha o meio de cada uma com o da 1ª
    if (pilhas.length > 1) {
      const ref = meioDe(pilhas[0].flat())
      for (const p of pilhas.slice(1)) {
        const d = Math.round(ref - meioDe(p.flat()))
        for (const id of p.flat().flatMap(galho)) pos[id] = { x: pos[id].x, y: pos[id].y + d }
      }
    }
    const fs = visiveisDe(id)
    if (fs.length) pos[id] = { x: pos[id].x, y: Math.round(meioDe(fs) - m(id).h / 2) }
  }
  if (compacto) {
    for (const r of raizes) compactar(r.id)
    empilhar(raizes.map((r) => [r.id]), 80)
  }
  // várias raízes (ex.: um filtro que tirou o que as ligava): em linhas, como uma grade, em vez de uma coluna comprida
  if (compacto && raizes.length > 1) {
    const blocos = raizes.map((r) => {
      const ids = galho(r.id)
      const cx = ids.map(caixa)
      const x0 = Math.min(...cx.map((c) => c.x)), y0 = Math.min(...cx.map((c) => c.y))
      return { ids, x0, y0, w: Math.max(...cx.map((c) => c.x + c.w)) - x0, h: Math.max(...cx.map((c) => c.y + c.h)) - y0 }
    })
    const largura = Math.max(...blocos.map((b) => b.w), Math.sqrt(blocos.reduce((s, b) => s + (b.w + 80) * (b.h + 80), 0) * 16 / 9))
    let x = 0, y = 0, alturaLinha = 0
    for (const b of blocos) {
      if (x > 0 && x + b.w > largura) { x = 0; y += alturaLinha + 80; alturaLinha = 0 }
      for (const id of b.ids) pos[id] = { x: Math.round(pos[id].x - b.x0 + x), y: Math.round(pos[id].y - b.y0 + y) }
      x += b.w + GAP_COL * 2
      alturaLinha = Math.max(alturaLinha, b.h)
    }
  }
  let ys = 0
  for (const id of a.soltos) {
    const n = porId.get(id)!
    // usada num pedido: faz parte daquele fluxo — some quando o galho do pedido está recolhido
    const dono = a.donoDe.get(id)
    if (dono && !pos[dono]) continue
    if (n.pos) pos[id] = n.pos
    else { pos[id] = { x: -360, y: ys }; ys += m(id).h + GAP_Y }
  }
  return pos
}

/** As arestas: a árvore (sólidas) + as entradas extras de cada pedido e de cada HTML (tracejadas). */
export function arestas(nos: No[], a: Arvore): { de: string; para: string; tipo: 'linha' | 'entrada' }[] {
  const ids = new Set(nos.map((n) => n.id))
  const out: { de: string; para: string; tipo: 'linha' | 'entrada' }[] = []
  for (const [filho, p] of a.pai) if (ids.has(filho) && ids.has(p)) out.push({ de: p, para: filho, tipo: 'linha' })
  for (const n of nos) {
    if (n.tipo !== 'pedido' && n.tipo !== 'site') continue
    for (const e of n.entradas || []) if (ids.has(e) && a.pai.get(n.id) !== e) out.push({ de: e, para: n.id, tipo: 'entrada' })
  }
  return out
}
