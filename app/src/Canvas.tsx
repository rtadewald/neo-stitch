import {
  Background, BackgroundVariant, ControlButton, Controls, MiniMap, ReactFlow, ReactFlowProvider, SelectionMode, applyNodeChanges, useReactFlow,
  type Connection, type Edge, type NodeChange,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  ArrowUp, BadgeCheck, BookOpen, Bot, CircleDot, Clapperboard, Pin, PinOff, Check, ChevronLeft, ChevronRight, ClipboardPaste, Copy, Eye, EyeOff, FileText, GitBranchPlus, ImagePlus,
  Focus, LayoutGrid, AlignVerticalDistributeCenter, Maximize, Maximize2, Monitor, Trash2, UnfoldHorizontal, X,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, arquivoUrl, dinheiro, rotaVista, type Estado, type No } from './api'
import { CanvasCtx, type Ctx } from './ctx'
import { arestas, arvore, caminhoAprovadas, descendentes, ehPonto, galhoCompleto, layoutArvore, medida, nosDeSite, ocultosSob, recorte, type ModoLayout } from './layout'
import { Menu, type ItemMenu } from './Menu'
import { nodeTypes, type NoRF } from './nodes'
import { Painel } from './Painel'
import { SpecAgentes } from './Spec'
import { Trilho } from './Trilho'
import { useHistorico } from './useHistorico'
import { useProjeto } from './useProjeto'
import { Viewer } from './Viewer'

/** O canvas do projeto. Com `raiz` (uma vista, #/p/<slug>/f/<código>), é o mesmo canvas recortado: o nó e tudo o que saiu dele. */
export function Canvas({ slug, raiz }: { slug: string; raiz?: string }) {
  return (
    <ReactFlowProvider>
      <CanvasInterno slug={slug} raiz={raiz} />
    </ReactFlowProvider>
  )
}

function CanvasInterno({ slug, raiz }: { slug: string; raiz?: string }) {
  const { estado, erro, setErro, carregar, mudar: mudarCru, posicoes: posicoesCru, acao } = useProjeto(slug)
  const rf = useReactFlow()
  const [nodes, setNodes] = useState<NoRF[]>([])
  const [selecao, setSelecao] = useState<string[]>([])
  const [visto, setVisto] = useState<string | null>(null)
  const [aba, setAba] = useState<'brief' | 'diario' | null>(null)
  const [esconder, setEsconder] = useState(() => localStorage.getItem('neo:esconder') === '1')
  const [pontos, setPontos] = useState(() => localStorage.getItem('neo:pontos') !== '0')  // padrão: ligado
  const [focar, setFocar] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)
  const [selecionando, setSelecionando] = useState(false)
  const [confirmar, setConfirmar] = useState<string[] | null>(null)
  const [spec, setSpec] = useState(false)
  const [organizar, setOrganizar] = useState(false)
  const enquadrarDepois = useRef(false)
  const [caixa, setCaixa] = useState<{ x: number; y: number; w: number; h: number } | null>(null)
  const caixaAtiva = useRef(false)  // uma caixa de seleção em andamento não é interrompida se o ⌘ for solto no meio
  const [menu, setMenu] = useState<{ x: number; y: number; flow: { x: number; y: number }; no?: No } | null>(null)
  const mouse = useRef<{ x: number; y: number } | null>(null)
  const ancora = useRef<{ id: string; pos: { x: number; y: number } } | null>(null)
  const arquivo = useRef<HTMLInputElement>(null)
  const ondeSubir = useRef<{ x: number; y: number } | undefined>(undefined)
  const arrastando = useRef(new Set<string>())
  const [medidas, setMedidas] = useState(() => new Map<string, { w: number; h: number }>())

  // acima de 100% de zoom, os controles dos cartões (ações, rodapé, marcas) ficam do tamanho da tela: --inv = 1/zoom
  const raizCanvas = useRef<HTMLDivElement>(null)
  const contraZoom = useCallback((z: number) => { raizCanvas.current?.style.setProperty('--inv', String(1 / Math.max(1, z))) }, [])
  const limparSelecao = useCallback(() => setNodes((ns) => ns.map((n) => (n.selected ? { ...n, selected: false } : n))), [])
  // todos os nós do projeto + as versões de HTML (montadas dos avanços); `nos` é o que esta vista mostra
  const todos = useMemo(() => (estado ? [...estado.nos, ...nosDeSite(estado)] : []), [estado])
  const porId = useMemo(() => new Map(todos.map((n) => [n.id, n])), [todos])
  const porIdRef = useRef(porId)
  porIdRef.current = porId
  const lerPorId = useCallback(() => porIdRef.current, [])
  const historico = useHistorico({ slug, porId: lerPorId, mudar: mudarCru, posicoes: posicoesCru, acao })
  const { posicoes, apagar: apagarDeVez, emLote, passo } = historico
  // o HTML não é um arquivo de nó: por aqui só o deslocamento do card (arrastar, ⌘Z), que vai para o impl.json; o estado
  // dele vai pelos botões do card
  const mudarHist = historico.mudar
  const mudar = useCallback((id: string, c: Partial<No>) =>
    (lerPorId().get(id)?.tipo === 'site' && !('desloc' in c) ? Promise.resolve() : mudarHist(id, c)),
    [lerPorId, mudarHist])
  const arvTodos = useMemo(() => arvore(todos), [todos])
  const recortado = !!raiz && porId.has(raiz)
  const [filtrouRaiz, setFiltrouRaiz] = useState(false)
  // abrir uma vista a põe no topo do histórico (se não estiver pinada)
  const registrada = useRef(false)
  useEffect(() => {
    if (!recortado || registrada.current) return
    registrada.current = true
    api.vista(slug, 'abrir', raiz!).then(() => carregar(true)).catch(() => {})
  }, [recortado, slug, raiz, carregar])
  const mudarVista = useCallback((a: 'pinar' | 'despinar', id: string) => { acao(() => api.vista(slug, a, id)) }, [acao, slug])
  const abrirVista = useCallback((id: string) => { location.hash = rotaVista(slug, id) }, [slug])
  const nos = useMemo(() => {
    if (!recortado) return todos
    const dentro = recorte(arvTodos, raiz!, todos)
    // a raiz sempre abre (a vista existe para mostrar o que saiu dela) e é a raiz da árvore, mesmo se tiver posição própria
    // ao abrir, a raiz mostra tudo; depois de filtrar ou recolher aqui dentro (⌘A, níveis, galho), passa a valer o que foi gravado nela
    return todos.filter((n) => dentro.has(n.id)).map((n) => (n.id !== raiz ? n
      : filtrouRaiz ? { ...n, pos: null, desloc: null } : { ...n, recolhido: false, escondidos: [], pos: null, desloc: null }))
  }, [todos, arvTodos, recortado, raiz, filtrouRaiz])
  const arv = useMemo(() => (recortado ? arvore(nos) : arvTodos), [recortado, nos, arvTodos])
  const videosRecorte = useMemo(() => (recortado ? nos.filter((n) => n.tipo === 'video' && n.arquivo) : []), [recortado, nos])
  const [modoLocal, setModoLocal] = useState<ModoLayout | null>(null)
  const modo: ModoLayout = modoLocal || estado?.projeto.layout || 'pilha'
  const trocarModo = useCallback(async (v: ModoLayout) => {
    setModoLocal(v)
    await acao(() => api.mudarProjeto(slug, { layout: v }))
    setModoLocal(null)
  }, [acao, slug])
  const [compactoLocal, setCompactoLocal] = useState<boolean | null>(null)
  const compacto = compactoLocal ?? !!estado?.projeto.compacto

  // apagar sempre pergunta antes; leva o galho inteiro (o ⌘Z traz de volta)
  const apagar = useCallback(async (ids: string | string[]) => {
    const lista = (Array.isArray(ids) ? ids : [ids]).filter((id) => porId.get(id) && porId.get(id)!.tipo !== 'brief' && porId.get(id)!.tipo !== 'site')
    const set = new Set(lista)
    const raizes = lista.filter((id) => {
      for (let p = arv.pai.get(id); p; p = arv.pai.get(p)) if (set.has(p)) return false
      return true
    })
    if (raizes.length) setConfirmar(raizes)
  }, [porId, arv])
  const confirmarApagar = useCallback(async () => {
    const raizes = confirmar || []
    setConfirmar(null)
    limparSelecao()
    await emLote(async () => { for (const id of raizes) await apagarDeVez(id) })
  }, [confirmar, emLote, apagarDeVez, limparSelecao])


  // a árvore se arranja sozinha (galhos recolhidos somem); só referências soltas guardam posição
  const posicoesArvore = useMemo(
    () => layoutArvore(nos, arv, medidas, (n) => esconder && (n.tipo === 'imagem' || n.tipo === 'site') && n.estado === 'descartada', modo, pontos, compacto),
    [nos, arv, medidas, esconder, modo, pontos, compacto],
  )
  // o ajuste manual (arrastar) é um deslocamento sobre a posição automática, herdado por todo o galho
  const posicoesFinais = useMemo(() => {
    const out: Record<string, { x: number; y: number }> = {}
    const soma = new Map<string, { x: number; y: number }>()  // deslocamento acumulado do nó + ancestrais (memo)
    const acumulado = (id: string): { x: number; y: number } => {
      const c = soma.get(id)
      if (c) return c
      const p = arv.pai.get(id)
      const base = p ? acumulado(p) : { x: 0, y: 0 }
      const d = porId.get(id)?.desloc
      const v = d ? { x: base.x + d.x, y: base.y + d.y } : base
      soma.set(id, v)
      return v
    }
    for (const [id, p] of Object.entries(posicoesArvore)) {
      if (arv.soltos.has(id)) { out[id] = p; continue }
      const d = acumulado(id)
      out[id] = { x: p.x + d.x, y: p.y + d.y }
    }
    return out
  }, [posicoesArvore, arv, porId])
  const visiveis = useMemo(() => nos.filter((n) => posicoesArvore[n.id]), [nos, posicoesArvore])
  const galhoVisivel = useCallback((id: string) => {
    const out: string[] = []
    // o galho inclui as referências soltas usadas pelos pedidos dele (andam junto ao arrastar)
    const ir = (x: string) => {
      for (const r of arv.anexos.get(x) || []) if (posicoesArvore[r] && !out.includes(r)) out.push(r)
      for (const f of arv.filhos.get(x) || []) if (posicoesArvore[f]) { out.push(f); ir(f) }
    }
    ir(id)
    return out
  }, [arv, posicoesArvore])
  const refs = useRef({ galhoVisivel, posicoesFinais })
  refs.current = { galhoVisivel, posicoesFinais }

  useEffect(() => {
    setNodes((anteriores) => {
      const antes = new Map(anteriores.map((n) => [n.id, n]))
      return visiveis.map((no) => {
        const a = antes.get(no.id)
        const pos = arrastando.current.has(no.id) && a ? a.position : posicoesFinais[no.id]
        return { id: no.id, type: no.tipo, position: pos, data: { no }, selected: a?.selected ?? false,
          // a versão de HTML antiga (sem impl.json) não tem onde guardar a posição
          draggable: no.tipo !== 'site' || !!no.site?.trabalho }
      })
    })
  }, [visiveis, posicoesFinais])

  // pedido criado pelo botão direito: nasce no ponto clicado (um deslocamento sobre o lugar automático dele)
  useEffect(() => {
    const a = ancora.current
    if (!a || !posicoesFinais[a.id]) return
    ancora.current = null
    const f = posicoesFinais[a.id]
    const d = porId.get(a.id)?.desloc || { x: 0, y: 0 }
    mudarCru(a.id, { desloc: { x: Math.round(d.x + a.pos.x - f.x), y: Math.round(d.y + a.pos.y - f.y) } })
  }, [posicoesFinais, porId, mudarCru])

  // um pedido recém-criado vem para o centro (e só então o campo dele ganha o foco)
  useEffect(() => {
    if (!focar) return
    const n = nodes.find((x) => x.id === focar)
    if (!n) return
    const { x, y, zoom } = rf.getViewport()
    const w = n.measured?.width || 320
    const h = n.measured?.height || 170
    const sx = n.position.x * zoom + x
    const sy = n.position.y * zoom + y
    const dentro = sx > 40 && sy > 70 && sx + w * zoom < window.innerWidth - 40 && sy + h * zoom < window.innerHeight - 40
    if (!dentro) rf.setCenter(n.position.x + w / 2, n.position.y + h / 2, { zoom: Math.max(zoom, 0.8), duration: 350 })
  }, [focar, nodes, rf])

  const edges: Edge[] = useMemo(() => {
    const ids = new Set(visiveis.map((n) => n.id))
    return arestas(visiveis, arv)
      .filter((a) => ids.has(a.de) && ids.has(a.para))
      .map((a) => {
        const alvo = porId.get(a.para)
        const vivo = alvo?.tipo === 'pedido' && (alvo.status === 'trabalhando' || alvo.status === 'enviado') ||
          (alvo?.tipo === 'imagem' || alvo?.tipo === 'video') && alvo.gerando || alvo?.site?.trabalho?.status === 'trabalhando'
        // o que leva a um HTML é verde-azulado; de uma versão para a evolução dela, tracejado
        const site = alvo?.tipo === 'site' ? ` deriva${porId.get(a.de)?.tipo === 'site' ? ' evolucao' : ''}` : ''
        return { id: `${a.de}>${a.para}`, source: a.de, target: a.para, animated: !!vivo, className: `aresta ${a.tipo}${site}` }
      })
  }, [visiveis, porId, arv])

  const onNodesChange = useCallback((changes: NodeChange<NoRF>[]) => {
    setNodes((ns) => {
      const out = applyNodeChanges(changes.filter((c) => c.type !== 'remove'), ns)
      // arrastar um nó leva o galho junto (os filhos andam o mesmo tanto)
      const movs = changes.filter((c) => c.type === 'position' && c.dragging && c.position)
      if (!movs.length) return out
      const antes = new Map(ns.map((n) => [n.id, n.position]))
      const arrastados = new Set(movs.map((c) => (c.type === 'position' ? c.id : '')))
      const delta = new Map<string, { x: number; y: number }>()
      for (const c of movs) {
        if (c.type !== 'position' || !c.position) continue
        const p0 = antes.get(c.id)
        if (!p0) continue
        const d = { x: c.position.x - p0.x, y: c.position.y - p0.y }
        for (const f of refs.current.galhoVisivel(c.id)) if (!arrastados.has(f) && !delta.has(f)) {
          delta.set(f, d)
          arrastando.current.add(f)
        }
      }
      return delta.size ? out.map((n) => {
        const d = delta.get(n.id)
        return d ? { ...n, position: { x: n.position.x + d.x, y: n.position.y + d.y } } : n
      }) : out
    })
    for (const c of changes) if (c.type === 'position' && c.dragging) arrastando.current.add(c.id)
    // o tamanho real de cada nó alimenta o arranjo da árvore (textos longos, imagens retrato…)
    const dims = changes.filter((c) => c.type === 'dimensions' && c.dimensions)
    if (dims.length) {
      setMedidas((m) => {
        let mudou = false
        const novo = new Map(m)
        for (const c of dims) {
          if (c.type !== 'dimensions' || !c.dimensions) continue
          const a = m.get(c.id)
          const d = { w: Math.round(c.dimensions.width), h: Math.round(c.dimensions.height) }
          if (!a || Math.abs(a.w - d.w) > 2 || Math.abs(a.h - d.h) > 2) { novo.set(c.id, d); mudou = true }
        }
        return mudou ? novo : m
      })
    }
  }, [])

  const onNodeDragStop = useCallback(
    (_: unknown, __: unknown, movidos: NoRF[]) => {
      emLote(() => {
      const mapa: Record<string, { x: number; y: number }> = {}
      const ids = new Set(movidos.map((n) => n.id))
      for (const n of movidos) {
        if (arv.soltos.has(n.id)) { mapa[n.id] = { x: Math.round(n.position.x), y: Math.round(n.position.y) }; continue }
        // um nó cujo ancestral também foi arrastado só acompanha (o deslocamento já vem do ancestral)
        let anc = arv.pai.get(n.id)
        while (anc && !ids.has(anc)) anc = arv.pai.get(anc)
        if (anc) continue
        const antes = posicoesFinais[n.id]
        const d = porId.get(n.id)?.desloc || { x: 0, y: 0 }
        const dx = Math.round(n.position.x - antes.x)
        const dy = Math.round(n.position.y - antes.y)
        if (dx || dy) mudar(n.id, { desloc: { x: d.x + dx, y: d.y + dy } })
      }
      // referências usadas por pedidos do galho andaram junto: grava onde ficaram
      for (const n of movidos) for (const r of galhoVisivel(n.id)) if (arv.soltos.has(r) && !mapa[r]) {
        const p = rf.getNode(r)?.position
        if (p) mapa[r] = { x: Math.round(p.x), y: Math.round(p.y) }
      }
      if (Object.keys(mapa).length) posicoes(mapa)
      })
      // solta o "arrastando" depois que a posição nova já voltou do estado
      window.setTimeout(() => arrastando.current.clear(), 600)
    },
    [posicoes, arv, posicoesFinais, porId, mudar, emLote, galhoVisivel, rf],
  )

  const onConnect = useCallback(
    (c: Connection) => {
      const de = porId.get(c.source)
      const para = porId.get(c.target)
      if (!de || !para) return
      if (para.tipo === 'pedido' && para.status === 'rascunho' && (de.tipo === 'imagem' || de.tipo === 'referencia')) {
        if (!(para.entradas || []).includes(de.id)) mudar(para.id, { entradas: [...(para.entradas || []), de.id] })
      }
    },
    [porId, mudar],
  )

  const conexaoValida = useCallback(
    (c: Connection | Edge) => {
      const de = porId.get(c.source)
      const para = porId.get(c.target)
      return !!de && !!para && para.tipo === 'pedido' && para.status === 'rascunho' && (de.tipo === 'imagem' || de.tipo === 'referencia')
    },
    [porId],
  )

  const aoSelecionar = useCallback(({ nodes: s }: { nodes: NoRF[] }) => {
    const ids = s.map((n) => n.id)
    setSelecao((a) => (a.length === ids.length && a.every((x, i) => x === ids[i]) ? a : ids))
  }, [])

  const telaPadrao = useCallback(() => todos.find((n) => n.tipo === 'tela')?.id, [todos])

  const novoPedido = useCallback(
    async (entradas: string[], tela?: string, extra?: Partial<No>) => {
      const p = await acao(() => api.criarNo(slug, { tipo: 'pedido', entradas, tela: tela || telaPadrao(), ...extra }))
      if (p) {
        historico.criado(p.id)
        setFocar(p.id)
        limparSelecao()
      }
      return p
    },
    [acao, slug, telaPadrao, historico, limparSelecao],
  )

  const pedidoVideo = useCallback((img: string) => novoPedido([img], undefined, { midia: 'video' }), [novoPedido])
  const novaTela = useCallback(
    () => acao(() => api.criarNo(slug, { tipo: 'tela', titulo: `Tela ${todos.filter((n) => n.tipo === 'tela').length + 1}` })),
    [acao, slug, todos],
  )
  const enviar = useCallback(async (id: string) => { await acao(() => api.enviar(slug, id)) }, [acao, slug])

  const copiar = useCallback((t: string) => {
    navigator.clipboard?.writeText(t)
    setAviso(`${t} copiado`)
  }, [])
  useEffect(() => {
    if (!aviso) return
    const t = setTimeout(() => setAviso(null), 1600)
    return () => clearTimeout(t)
  }, [aviso])

  // colar (⌘V) ou soltar imagens no canvas → referências
  const subir = useCallback(
    async (arquivos: File[], onde?: { x: number; y: number }) => {
      const imgs = arquivos.filter((f) => f.type.startsWith('image/'))
      if (!imgs.length) return
      // onde o mouse está (⌘V cola embaixo do cursor); fora do canvas, no centro da tela
      const tela = mouse.current || { x: window.innerWidth / 2, y: window.innerHeight / 2 }
      const centro = onde || rf.screenToFlowPosition(tela)
      for (const [i, f] of imgs.entries())
        await acao(() => api.subirRef(slug, f, f.name || 'colada', { x: centro.x + i * 30, y: centro.y + i * 30 }, telaPadrao()))
    },
    [acao, rf, slug, telaPadrao],
  )
  useEffect(() => {
    const colar = (e: ClipboardEvent) => {
      if (e.target instanceof Element && e.target.closest('textarea, input')) return
      const arquivos = [...(e.clipboardData?.files || [])]
      if (arquivos.length) { e.preventDefault(); subir(arquivos) }
    }
    window.addEventListener('paste', colar)
    return () => window.removeEventListener('paste', colar)
  }, [subir])

  const selecionados = useMemo(() => selecao.map((id) => porId.get(id)).filter(Boolean) as No[], [selecao, porId])
  const imgsSel = selecionados.filter((n) => n.tipo === 'imagem' || n.tipo === 'referencia')
  const soImagens = selecionados.filter((n) => n.tipo === 'imagem' && !n.gerando)

  const marcar = useCallback(
    (lista: No[], e: Estado) => {
      const todos = lista.every((n) => n.estado === e)
      emLote(() => lista.forEach((n) => mudar(n.id, { estado: todos ? 'neutra' : e })))
    },
    [mudar, emLote],
  )

  // ⌘1/⌘2/⌘3 (ou 1/2/3): cada nível é uma geração de imagens, e o pedido anda junto com as imagens que gera —
  // 1 = as primeiras imagens (os pedidos que saem delas ficam recolhidos) · 2 = + os pedidos delas e as imagens desses · 3 = …
  // nível: imagem = imagens no caminho até a raiz (contando ela); pedido = imagens acima + 1; brief/tela/referência = 0.
  const recolherNivel = useCallback((n: number) => {
    setFiltrouRaiz(true)
    const imgsAcima = new Map<string, number>()
    const contar = (id: string): number => {
      if (imgsAcima.has(id)) return imgsAcima.get(id)!
      const p = arv.pai.get(id)
      const c = (porId.get(id)?.tipo === 'imagem' ? 1 : 0) + (p ? contar(p) : 0)
      imgsAcima.set(id, c)
      return c
    }
    const nivel = (no: No) => no.tipo === 'pedido' ? contar(no.id) + 1 : no.tipo === 'imagem' ? contar(no.id) : 0
    emLote(() => {
      for (const no of nos) {
        if (arv.soltos.has(no.id) || !(arv.filhos.get(no.id) || []).length) continue
        const l = nivel(no)
        const aberto = !no.recolhido && !(no.escondidos || []).length
        const fecha = no.tipo === 'imagem' && l === n  // a imagem do nível fica; o que saiu dela é o próximo nível
        const abre = no.tipo === 'pedido' ? l <= n : l < n
        if (fecha && (!no.recolhido || (no.escondidos || []).length)) mudar(no.id, { recolhido: true, escondidos: [] })
        else if (abre && !fecha && !aberto) mudar(no.id, { recolhido: false, escondidos: [] })
      }
    })
    enquadrarDepois.current = true
    setAviso(`Nível ${n} · ⌘Z desfaz`)
  }, [nos, arv, porId, emLote, mudar])

  // ⌘A: recolhe tudo o que não leva a uma imagem aprovada (uma ação comum: dá para expandir de volta, e o ⌘Z desfaz)
  const irParaAprovados = useCallback(() => {
    setFiltrouRaiz(true)
    const pinados = new Set(estado?.vistas.pinados || [])      // o filtro mostra os aprovados e os pinados
    const caminho = caminhoAprovadas(nos, arv, pinados)
    if (!nos.some((n) => (n.tipo === 'imagem' && n.estado === 'aprovada') || pinados.has(n.id))) { setAviso('Nada aprovado nem pinado ainda'); return }
    emLote(() => {
      for (const n of nos) {
        const filhos = arv.filhos.get(n.id) || []
        if (!filhos.length || !caminho.has(n.id)) continue
        const escondidos = filhos.filter((f) => !caminho.has(f))
        const iguais = !n.recolhido && JSON.stringify(n.escondidos || []) === JSON.stringify(escondidos)
        if (!iguais) mudar(n.id, { recolhido: false, escondidos })
      }
    })
    enquadrarDepois.current = true
    setAviso('Só o caminho até os aprovados e os pinados · ⌘Z desfaz')
  }, [nos, arv, estado?.vistas.pinados, emLote, mudar])

  // ⌘Z desfaz, ⌘⇧Z (ou ⌘Y) refaz — fora dos campos de texto, que têm o próprio desfazer
  useEffect(() => {
    const tecla = async (e: KeyboardEvent) => {
      if (!(e.metaKey || e.ctrlKey)) return
      if (e.target instanceof Element && e.target.closest('textarea, input, select')) return
      const k = e.key.toLowerCase()
      // ⌘+ / ⌘− dão zoom no canvas (em vez do zoom da página do navegador)
      if (k === '=' || k === '+') { e.preventDefault(); rf.zoomIn({ duration: 160 }); return }
      if (k === '-' || k === '_') { e.preventDefault(); rf.zoomOut({ duration: 160 }); return }
      if (k === 'a') { e.preventDefault(); irParaAprovados(); return }  // ⌘A: só aprovados (em vez de selecionar a página)
      if (k === '1' || k === '2' || k === '3') { e.preventDefault(); recolherNivel(Number(k)); return }
      const refaz = (k === 'z' && e.shiftKey) || k === 'y'
      if (k !== 'z' && k !== 'y') return
      e.preventDefault()
      const ok = await (refaz ? historico.refazer() : historico.desfazer())
      setAviso(ok ? (refaz ? 'Refeito' : 'Desfeito') : refaz ? 'Nada para refazer' : 'Nada para desfazer')
    }
    window.addEventListener('keydown', tecla)
    return () => window.removeEventListener('keydown', tecla)
  }, [historico, irParaAprovados, recolherNivel, rf])

  // ⌘ segurado: liga a camada de seleção (⌘ + arrastar = caixa; ⌘ + clique = põe/tira o nó da seleção)
  useEffect(() => {
    const desce = (e: KeyboardEvent) => { if (e.key === 'Meta' || e.key === 'Control') setSelecionando(true) }
    const sobe = (e: KeyboardEvent) => { if (e.key === 'Meta' || e.key === 'Control') setSelecionando(false) }
    const sai = () => setSelecionando(false)
    // o macOS às vezes engole o keyup do ⌘ (⌘Tab, atalhos): o mouse sem ⌘ desliga a camada
    const confere = (e: PointerEvent) => { if (!e.metaKey && !e.ctrlKey && !caixaAtiva.current) setSelecionando(false) }
    window.addEventListener('keydown', desce)
    window.addEventListener('keyup', sobe)
    window.addEventListener('blur', sai)
    window.addEventListener('pointermove', confere)
    return () => {
      window.removeEventListener('keydown', desce); window.removeEventListener('keyup', sobe)
      window.removeEventListener('blur', sai); window.removeEventListener('pointermove', confere)
    }
  }, [])


  // atalhos: A aprova (o verde), D descarta, N novo pedido (com a seleção), Esc limpa
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if (e.target instanceof Element && e.target.closest('textarea, input, select')) return
      if (e.metaKey || e.ctrlKey || visto) return
      const k = e.key.toLowerCase()
      if ((k === '1' || k === '2' || k === '3') && !e.shiftKey && !e.altKey) { recolherNivel(Number(k)); return }
      if (k === 'a' && soImagens.length) marcar(soImagens, 'aprovada')
      else if (k === 'd' && soImagens.length) marcar(soImagens, 'descartada')
      else if (k === 'n' && imgsSel.length) { e.preventDefault(); novoPedido(imgsSel.map((n) => n.id)) }
      else if (k === 'v' && soImagens.length === 1) { e.preventDefault(); pedidoVideo(soImagens[0].id) }
      else if ((k === 'backspace' || k === 'delete') && selecao.length) { e.preventDefault(); apagar(selecao) }
      else if (k === 'escape') limparSelecao()
      else return
    }
    window.addEventListener('keydown', tecla)
    return () => window.removeEventListener('keydown', tecla)
  }, [soImagens, imgsSel, marcar, novoPedido, pedidoVideo, visto, selecao, apagar, recolherNivel, limparSelecao])

  // enquadrar pelas posições calculadas (o fitView do React Flow só enxerga nós já desenhados/medidos)
  const enquadrar = useCallback((ids?: string[], o: { min?: number; max?: number; dur?: number; folga?: number } = {}) => {
    const lista = (ids || Object.keys(posicoesFinais)).filter((id) => posicoesFinais[id] && porId.get(id))
    if (!lista.length) return
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity
    for (const id of lista) {
      const p = posicoesFinais[id]
      const n = porId.get(id)!
      const m = pontos && ehPonto(n) ? medida(n, true) : medidas.get(id) || medida(n)
      x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y); x1 = Math.max(x1, p.x + m.w); y1 = Math.max(y1, p.y + m.h)
    }
    const W = window.innerWidth
    const H = window.innerHeight
    const f = o.folga ?? 0.1
    const zoom = Math.min(o.max ?? 1.2, Math.max(o.min ?? 0.05, Math.min((W * (1 - 2 * f)) / (x1 - x0), (H * (1 - 2 * f)) / (y1 - y0))))
    rf.setViewport({ x: W / 2 - ((x0 + x1) / 2) * zoom, y: H / 2 - ((y0 + y1) / 2) * zoom, zoom }, { duration: o.dur ?? 450 })
  }, [posicoesFinais, porId, medidas, rf, pontos])
  const enquadrado = useRef(false)
  useEffect(() => {
    if (enquadrado.current || !nodes.length) return
    enquadrado.current = true
    requestAnimationFrame(() => enquadrar(undefined, { min: 0.3, max: 1, dur: 0, folga: 0.08 }))
  }, [nodes.length, enquadrar])

  // depois do ⌘A, enquadra o que ficou visível (quando as posições novas já chegaram)
  // (o pedido fica de pé até o enquadramento acontecer: re-renders no meio só adiam o timer)
  useEffect(() => {
    if (!enquadrarDepois.current) return
    const t = window.setTimeout(() => { enquadrarDepois.current = false; enquadrar(undefined, { min: 0.2, max: 1, folga: 0.06 }) }, 250)
    return () => window.clearTimeout(t)
  }, [posicoesFinais, enquadrar])

  // botão do meio num nó: enquadra a "família" dele (o nó + o que saiu dele; um pedido no meio leva as imagens junto).
  // Num nó sem filhos, sobe para o pai (imagem/referência) e enquadra pai + irmãos.
  const enquadrarFamilia = useCallback((id: string) => {
    const vis = (x: string) => !!posicoesArvore[x]
    const filhosVis = (x: string) => (arv.filhos.get(x) || []).filter(vis)
    let foco = id
    if (!filhosVis(id).length) {
      let p = arv.pai.get(id)
      while (p && porId.get(p)?.tipo === 'pedido') p = arv.pai.get(p)
      if (p) foco = p
    }
    const ids = new Set([foco])
    if (porId.get(foco)?.tipo === 'pedido') { const p = arv.pai.get(foco); if (p && vis(p)) ids.add(p) }
    for (const f of filhosVis(foco)) {
      ids.add(f)
      if (porId.get(f)?.tipo === 'pedido') filhosVis(f).forEach((g) => ids.add(g))
    }
    for (const r of arv.anexos.get(foco) || []) if (vis(r)) ids.add(r)
    enquadrar([...ids], { max: 1.2 })
  }, [arv, porId, posicoesArvore, enquadrar])
  const meio = useRef<{ x: number; y: number } | null>(null)
  const ultimoMeio = useRef(0)

  const recolhidos = useMemo(() => nos.filter((n) => n.recolhido || (n.escondidos || []).length), [nos])
  const deslocados = useMemo(() => nos.filter((n) => n.desloc && (n.desloc.x || n.desloc.y)), [nos])
  // Otimizar espaço: liga o layout compacto (os galhos sobem para os vãos) e desfaz os ajustes manuais desta vista — na 1ª vez,
  // de todo o projeto, porque todas as posições automáticas mudam. ⌘Z desfaz tudo junto.
  const distribuir = useCallback(async () => {
    const alvo = (compacto ? nos : todos).filter((n) => n.desloc && (n.desloc.x || n.desloc.y))
    await emLote(async () => {
      if (!compacto) {
        const ligar = async (v: boolean) => {
          setCompactoLocal(v)
          await acao(() => api.mudarProjeto(slug, { compacto: v }))
          setCompactoLocal(null)
        }
        passo({ desfazer: () => ligar(false), refazer: () => ligar(true) })
        await ligar(true)
      }
      for (const n of alvo) await mudar(n.id, { desloc: null })
    })
    enquadrarDepois.current = true
  }, [compacto, nos, todos, emLote, passo, acao, slug, mudar])
  const expandirTudo = useCallback(
    () => emLote(() => recolhidos.forEach((n) => mudar(n.id, { recolhido: false, escondidos: [] }))), [emLote, recolhidos, mudar])
  // a pílula/botão do galho: se algo está escondido, mostra tudo; senão, recolhe o galho inteiro
  const alternar = useCallback((id: string) => {
    // a raiz da vista: vale o que ela mostra agora (a cópia de `nos`), não o que está gravado nela
    const n = id === raiz ? nos.find((x) => x.id === id) : porId.get(id)
    if (!n) return
    if (id === raiz) setFiltrouRaiz(true)
    if (ocultosSob(arv, n)) mudar(id, { recolhido: false, escondidos: [] })
    else mudar(id, { recolhido: true })
  }, [porId, nos, raiz, arv, mudar])

  // ---------- botão direito ----------
  const telaMaisProxima = (p: { x: number; y: number }) => {
    let melhor: string | undefined
    let dist = Infinity
    for (const n of nos) {
      const q = posicoesFinais[n.id]
      if (n.tipo !== 'tela' || !q) continue
      const d = Math.hypot(q.x - p.x, q.y - p.y)
      if (d < dist) { dist = d; melhor = n.id }
    }
    return melhor || telaPadrao()
  }
  const colarDoClipboard = async (onde: { x: number; y: number }) => {
    try {
      const itens = await navigator.clipboard.read()
      const arquivos: File[] = []
      for (const it of itens) {
        const tipo = it.types.find((t) => t.startsWith('image/'))
        if (tipo) arquivos.push(new File([await it.getType(tipo)], 'colada', { type: tipo }))
      }
      if (arquivos.length) subir(arquivos, onde)
      else setErro('Não há imagem no clipboard.')
    } catch {
      setErro('Sem acesso ao clipboard: use ⌘V com o mouse sobre o canvas.')
    }
  }
  const itensMenu = (m: NonNullable<typeof menu>): ItemMenu[] => {
    const no = m.no
    if (!no) return [
      { rotulo: 'Novo pedido aqui', icone: <GitBranchPlus size={15} />, acao: async () => {
        const p = await novoPedido([], telaMaisProxima(m.flow))
        if (p) ancora.current = { id: p.id, pos: m.flow }
      } },
      { rotulo: 'Colar imagem', icone: <ClipboardPaste size={15} />, atalho: '⌘V', acao: () => colarDoClipboard(m.flow) },
      { rotulo: 'Referência do computador…', icone: <ImagePlus size={15} />, acao: () => { ondeSubir.current = m.flow; arquivo.current?.click() } },
      'sep',
      { rotulo: 'Nova tela', icone: <Monitor size={15} />, acao: novaTela },
    ]
    const galho: ItemMenu[] = descendentes(arv, no.id) ? [{
      rotulo: ocultosSob(arv, no) ? 'Mostrar o que está escondido' : 'Recolher galho',
      icone: ocultosSob(arv, no) ? <ChevronRight size={15} /> : <ChevronLeft size={15} />, acao: () => alternar(no.id),
    }] : []
    const codigo: ItemMenu = { rotulo: `Copiar código ${no.id}`, icone: <Copy size={15} />, acao: () => copiar(no.id) }
    // vistas: abrir o canvas a partir deste nó; pinar (a barra lateral; independe do aprovado)
    const abrirDaqui: ItemMenu[] = raiz === no.id ? [] : [{ rotulo: 'Abrir a partir daqui', icone: <Focus size={15} />, acao: () => abrirVista(no.id) }]
    const pinado = estado!.vistas.pinados.includes(no.id)
    const pinItem: ItemMenu = { rotulo: pinado ? 'Despinar' : 'Pinar', icone: pinado ? <PinOff size={15} /> : <Pin size={15} />,
      acao: () => mudarVista(pinado ? 'despinar' : 'pinar', no.id) }
    const apagarItem = (ids: string[]): ItemMenu => ({ rotulo: ids.length > 1 ? `Apagar as ${ids.length}…` : 'Apagar…', icone: <Trash2 size={15} />,
      atalho: '⌫', perigo: true, acao: () => apagar(ids) })
    if (no.tipo === 'imagem' || no.tipo === 'referencia') {
      // clicou numa imagem que faz parte de uma seleção maior: as ações valem para a seleção
      const grupo = selecao.includes(no.id) && imgsSel.length > 1 ? imgsSel : [no]
      const imgs = grupo.filter((n) => n.tipo === 'imagem' && !n.gerando)
      const marcas: ItemMenu[] = imgs.length ? [
        'sep',
        { rotulo: 'Aprovar', icone: <Check size={15} />, atalho: 'A', acao: () => marcar(imgs, 'aprovada') },
        { rotulo: 'Descartar', icone: <EyeOff size={15} />, atalho: 'D', acao: () => marcar(imgs, 'descartada') },
      ] : []
      return [
        { rotulo: grupo.length > 1 ? `Novo pedido com as ${grupo.length}` : 'Novo pedido a partir desta', icone: <GitBranchPlus size={15} />,
          atalho: 'N', acao: () => novoPedido(grupo.map((n) => n.id)) },
        ...(no.tipo === 'imagem' && no.arquivo ? [{ rotulo: 'Pedido de vídeo (dar vida)', icone: <Clapperboard size={15} />, atalho: 'V',
          acao: () => pedidoVideo(no.id) }] : []),
        ...(no.arquivo ? [{ rotulo: 'Abrir', icone: <Maximize2 size={15} />, acao: () => setVisto(no.id) }] : []),
        ...abrirDaqui, pinItem,
        ...marcas, 'sep', ...galho, codigo,
        'sep', apagarItem(grupo.map((n) => n.id)),
      ]
    }
    if (no.tipo === 'pedido') return [
      ...(no.status === 'rascunho' ? [{ rotulo: 'Enviar ao Claude', icone: <ArrowUp size={15} />, atalho: '⌘↵', acao: () => enviar(no.id) }] : []),
      ...abrirDaqui, pinItem, 'sep', ...galho, codigo, 'sep', apagarItem([no.id]),
    ]
    if (no.tipo === 'tela') return [
      { rotulo: 'Novo pedido nesta tela', icone: <GitBranchPlus size={15} />, acao: () => novoPedido([], no.id) },
      ...abrirDaqui, pinItem, 'sep', ...galho, codigo, 'sep', apagarItem([no.id]),
    ]
    // uma página com print (captura) pode ser a origem de um pedido de imagens, como uma imagem
    const daPagina: ItemMenu[] = no.tipo === 'site' && no.arquivo
      ? [{ rotulo: 'Novo pedido a partir desta', icone: <GitBranchPlus size={15} />, atalho: 'N', acao: () => novoPedido([no.id]) }] : []
    if (no.tipo === 'video' || no.tipo === 'modelo' || no.tipo === 'site') return [...daPagina, ...abrirDaqui, pinItem, 'sep', ...galho, codigo]
    return [
      { rotulo: 'Editar brief', icone: <FileText size={15} />, acao: () => setAba('brief') },
      { rotulo: 'Nova tela', icone: <Monitor size={15} />, acao: novaTela },
      ...galho, codigo,
    ]
  }
  const abrirMenu = (e: React.MouseEvent | MouseEvent, no?: No) => {
    e.preventDefault()
    setMenu({ x: e.clientX, y: e.clientY, flow: rf.screenToFlowPosition({ x: e.clientX, y: e.clientY }), no })
  }

  const ctx: Ctx | null = useMemo(
    () => estado && {
      slug, estado, porId, arv, alternar, mudar, apagar: (id: string) => apagar(id), acao, abrir: setVisto, painel: setAba, novoPedido, pedidoVideo,
      novaTela, enviar, copiar, focar, limparFoco: () => setFocar(null), pontos, raiz, abrirVista, mudarVista,
    },
    [slug, estado, porId, arv, alternar, mudar, apagar, acao, novoPedido, pedidoVideo, novaTela, enviar, copiar, focar, pontos, raiz, abrirVista, mudarVista],
  )

  if (!estado || !ctx) {
    return <div className="carregando">{erro ? <p className="erro-tela">{erro}</p> : <span className="pulso grande" />}</div>
  }

  return (
    <CanvasCtx.Provider value={ctx}>
      <div className="canvas" ref={raizCanvas} onDragOver={(e) => e.preventDefault()}
        onPointerDownCapture={(e) => { if (e.button === 1) meio.current = { x: e.clientX, y: e.clientY } }}
        onAuxClick={(e) => {
          // clique do meio (sem arrastar) em cima de um nó
          if (e.button !== 1 || !meio.current || Math.hypot(e.clientX - meio.current.x, e.clientY - meio.current.y) > 5) return
          const id = (e.target as Element).closest('.react-flow__node')?.getAttribute('data-id')
          if (id) { e.preventDefault(); enquadrarFamilia(id); return }
          // dois cliques do meio no vazio: afasta para mostrar tudo
          if ((e.target as Element).closest('.topo, .painel, .menu, .barra-selecao, .react-flow__controls, .react-flow__minimap')) return
          const agora = Date.now()
          if (agora - ultimoMeio.current < 450) { e.preventDefault(); enquadrar(undefined, { folga: 0.05 }); ultimoMeio.current = 0 }
          else ultimoMeio.current = agora
        }}
        onDoubleClick={(e) => {
          // duplo clique no vazio: afasta para mostrar tudo
          // (vale no fundo, nas linhas de conexão, em qualquer lugar que não seja um nó ou um painel)
          if (!(e.target as Element).closest('.react-flow__node, .topo, .painel, .menu, .barra-selecao, .react-flow__controls, .react-flow__minimap, .modal-fundo, .viewer'))
            enquadrar(undefined, { folga: 0.05 })
        }}
        onMouseMove={(e) => { mouse.current = { x: e.clientX, y: e.clientY } }} onMouseLeave={() => { mouse.current = null }}
        onDrop={(e) => { e.preventDefault(); subir([...e.dataTransfer.files], rf.screenToFlowPosition({ x: e.clientX, y: e.clientY })) }}>
        {nodes.length > 0 && <ReactFlow
          nodes={nodes} edges={edges} nodeTypes={nodeTypes}
          onNodesChange={onNodesChange} onNodeDragStop={onNodeDragStop}
          onConnect={onConnect} isValidConnection={conexaoValida}
          onSelectionChange={aoSelecionar}
          onPaneContextMenu={(e) => abrirMenu(e)}
          onNodeContextMenu={(e, n) => abrirMenu(e, n.data.no)}
          onSelectionContextMenu={(e, ns) => abrirMenu(e, ns[0]?.data.no)}
          deleteKeyCode={null} selectionKeyCode={null} multiSelectionKeyCode={['Meta', 'Control']}
          minZoom={0.05} maxZoom={2.5} proOptions={{ hideAttribution: true }}
          // dois dedos no trackpad (ou a roda) = navegar · pinça = zoom · ⌘+ / ⌘− = zoom · arrastar no vazio = navegar ·
          // ⌘ + arrastar (em qualquer lugar) = caixa de seleção · ⌘ + clique = seleção
          onlyRenderVisibleElements zoomOnScroll={false} panOnScroll zoomOnPinch
          panOnDrag={[0, 1]} panActivationKeyCode={null} selectionOnDrag={false} selectionMode={SelectionMode.Partial}
          defaultEdgeOptions={{ type: 'default' }} connectionRadius={36}
          zoomOnDoubleClick={false}
          onMove={(_, vp) => contraZoom(vp.zoom)} onInit={(i) => contraZoom(i.getZoom())}
        >
          <Background variant={BackgroundVariant.Dots} gap={22} size={1.3} color="var(--ponto)" />
          <Controls showInteractive={false} showFitView={false} position="bottom-left">
            <ControlButton title="Mostrar tudo (duplo clique no vazio)" onClick={() => enquadrar(undefined, { folga: 0.05 })}><Maximize size={12} /></ControlButton>
          </Controls>
          <MiniMap position="bottom-right" pannable zoomable nodeColor={corMinimapa} nodeStrokeWidth={0} maskColor="var(--mascara)" />
        </ReactFlow>}

        <Trilho slug={slug} estado={estado} porId={porId} ativo={raiz} voltar={recortado} mudarVista={mudarVista} />
        <header className="topo">
          <a href="#/" className="marca-app" title="Projetos">
            <img src="/favicon.svg" alt="" width={22} height={22} />
          </a>
          {recortado ? (
            <a href={`#/p/${slug}`} className="projeto-nome link" title="Voltar ao canvas inteiro">{estado.projeto.nome}</a>
          ) : <span className="projeto-nome">{estado.projeto.nome}</span>}
          <span className="prefixo">{estado.projeto.prefixo}</span>
          {recortado && <Recorte raiz={porId.get(raiz!)!} pinado={estado.vistas.pinados.includes(raiz!)} copiar={copiar} mudarVista={mudarVista} />}
          <span className="cresce" />
          <span className={`ouvinte ${estado.ouvinte ? 'on' : ''}`}
            title={estado.ouvinte ? 'Claude está ouvindo a fila' : 'Claude não está ouvindo — peça no chat: "ouça o Neo Stitch"'}>
            <span className="ponto" /> Claude
          </span>
          <span className="custo" title={`Hoje ${dinheiro(estado.custos.hoje)} · teto diário ${dinheiro(estado.projeto.tetos.diario_usd)}`}>
            {dinheiro(estado.custos.total)}
          </span>
          <button type="button" className={`ico ${esconder ? 'on' : ''}`} title={esconder ? 'Mostrar descartadas' : 'Esconder descartadas'}
            onClick={() => { setEsconder(!esconder); localStorage.setItem('neo:esconder', esconder ? '0' : '1') }}>
            {esconder ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
          <button type="button" className={`ico ${pontos ? 'on' : ''}`}
            title={pontos ? 'Pedidos concluídos como pontos na linha (passe o mouse para ver) — clique para mostrar os cards' : 'Mostrar os pedidos concluídos como pontos na linha'}
            onClick={() => { setPontos(!pontos); localStorage.setItem('neo:pontos', pontos ? '0' : '1') }}>
            <CircleDot size={16} />
          </button>
          <button type="button" className="ico aprovados" title="Só aprovados e pinados: recolhe o resto (⌘A · ⌘Z desfaz)" onClick={irParaAprovados}>
            <BadgeCheck size={16} />
          </button>
          <div className="organizar">
            <button type="button" className={`ico ${organizar ? 'on' : ''}`} title="Organizar o canvas" onClick={() => setOrganizar(!organizar)}>
              <LayoutGrid size={16} />
            </button>
            {organizar && (
              <div className="pop-organizar" onPointerLeave={() => setOrganizar(false)}>
                <div className="modos">
                  {([['pilha', 'Empilhado'], ['grade', 'Árvore em grade'], ['grade3', 'Grade 3×3'], ['grade4', 'Grade 4×4'], ['grade5', 'Grade 5×5']] as const).map(([v, r]) => (
                    <button key={v} type="button" className={`modo ${modo === v ? 'on' : ''}`} onClick={() => trocarModo(v)}>
                      <PreviaModo modo={v} />
                      <span>{r}</span>
                    </button>
                  ))}
                </div>
                <span className="menu-sep" />
                <button type="button" className="acao-pop" onClick={() => { distribuir(); setOrganizar(false) }}>
                  <AlignVerticalDistributeCenter size={15} /> Otimizar espaço <span className="mudo">{compacto && deslocados.length ? `fecha os vãos · ${deslocados.length} ajustes` : 'fecha os vãos'}</span>
                </button>
                <button type="button" className="acao-pop" onClick={() => { irParaAprovados(); setOrganizar(false) }}>
                  <Check size={15} /> Só aprovados <kbd>⌘A</kbd>
                </button>
                <button type="button" className="acao-pop" disabled={!deslocados.length}
                  onClick={() => emLote(() => deslocados.forEach((n) => mudar(n.id, { desloc: null })))}>
                  <LayoutGrid size={15} /> Realinhar <span className="mudo">{deslocados.length ? `${deslocados.length} ajustes manuais` : 'nada fora do lugar'}</span>
                </button>
                <span className="menu-sep" />
                <div className="niveis">
                  {[1, 2, 3].map((n) => (
                    <button key={n} type="button" className="modo" title={`Recolher a partir do nível ${n} (⌘${n})`}
                      onClick={() => { recolherNivel(n); setOrganizar(false) }}>
                      <PreviaNivel n={n} />
                      <span>Nível {n} <kbd>⌘{n}</kbd></span>
                    </button>
                  ))}
                </div>
                <button type="button" className="acao-pop" disabled={!recolhidos.length}
                  onClick={expandirTudo}>
                  <UnfoldHorizontal size={15} /> Expandir tudo <span className="mudo">{recolhidos.length ? `${recolhidos.length} galhos fechados` : 'tudo aberto'}</span>
                </button>
              </div>
            )}
          </div>
          {videosRecorte.length > 0 && (
            <button type="button" className={`ico ${spec ? 'on' : ''}`} title="Delegar o vídeo → HTML para outros agentes (a spec)" onClick={() => setSpec(true)}>
              <Bot size={16} />
            </button>
          )}
          <button type="button" className={`ico ${aba ? 'on' : ''}`} title="Brief e diário" onClick={() => setAba(aba ? null : 'diario')}>
            <BookOpen size={16} />
          </button>
        </header>
        {spec && videosRecorte.length > 0 && (
          <SpecAgentes videos={videosRecorte.map((n) => ({ id: n.id, nome: n.nome || n.modelo || '' }))}
            fechar={() => setSpec(false)} copiar={(t, msg) => { navigator.clipboard?.writeText(t); setAviso(msg || `${t} copiado`) }} />
        )}

        {imgsSel.length > 0 && (
          <div className="barra-selecao">
            <span className="contagem">{imgsSel.length}</span>
            <button type="button" className="primario" title="Novo pedido com a seleção (N)" onClick={() => novoPedido(imgsSel.map((n) => n.id))}>
              <GitBranchPlus size={15} /> Pedido
            </button>
            {soImagens.length === 1 && (
              <button type="button" className="ico" title="Pedido de vídeo a partir desta imagem (V)" onClick={() => pedidoVideo(soImagens[0].id)}>
                <Clapperboard size={16} />
              </button>
            )}
            {soImagens.length > 0 && (
              <>
                <span className="sep" />
                <button type="button" className="ico" title="Aprovar (A)" onClick={() => marcar(soImagens, 'aprovada')}><Check size={16} /></button>
                <button type="button" className="ico" title="Descartar (D)" onClick={() => marcar(soImagens, 'descartada')}><EyeOff size={16} /></button>
              </>
            )}
            <span className="sep" />
            <button type="button" className="ico" title="Limpar seleção (Esc)" onClick={() => limparSelecao()}>
              <X size={16} />
            </button>
          </div>
        )}

        {!recortado && nos.length <= 2 && !nos.some((n) => n.tipo === 'pedido') && (
          <div className="dica">Cole ou arraste referências · <kbd>+</kbd> na tela para pedir imagens</div>
        )}

        {erro && (
          <div className="toast erro" onClick={() => setErro(null)}>{erro}</div>
        )}
        {aviso && <div className="toast">{aviso}</div>}

        {visto && porId.get(visto) && <Viewer id={visto} fechar={() => setVisto(null)} navegar={setVisto} />}
        {aba && <Painel aba={aba} setAba={setAba} />}
        {(selecionando || caixa) && !visto && !menu && (
          // ⌘ pressionado: arrastar desenha a caixa de seleção (mesmo começando em cima de um nó); clicar põe/tira o nó;
          // ⌘ + scroll dá zoom em volta do cursor (a capa fica por cima do canvas, então o scroll passa por ela)
          <div className="capa-selecao" onWheel={(e) => {
            const area = document.querySelector('.react-flow')?.getBoundingClientRect()
            if (!area) return
            const { x, y, zoom } = rf.getViewport()
            const z = Math.min(2.5, Math.max(0.05, zoom * Math.pow(2, -e.deltaY * 0.0025)))
            const cx = e.clientX - area.left, cy = e.clientY - area.top
            rf.setViewport({ x: cx - ((cx - x) * z) / zoom, y: cy - ((cy - y) * z) / zoom, zoom: z })
          }} onPointerDown={(e) => {
            const alvo = e.currentTarget
            alvo.setPointerCapture(e.pointerId)
            caixaAtiva.current = true
            const somar = e.shiftKey  // ⇧ junto soma à seleção atual
            const r0 = alvo.getBoundingClientRect()
            const inicio = { x: e.clientX, y: e.clientY }
            setCaixa({ x: inicio.x - r0.left, y: inicio.y - r0.top, w: 0, h: 0 })
            const mover = (ev: PointerEvent) => {
              const x = Math.min(inicio.x, ev.clientX)
              const y = Math.min(inicio.y, ev.clientY)
              setCaixa({ x: x - r0.left, y: y - r0.top, w: Math.abs(ev.clientX - inicio.x), h: Math.abs(ev.clientY - inicio.y) })
            }
            const soltar = (ev: PointerEvent) => {
              alvo.removeEventListener('pointermove', mover)
              alvo.removeEventListener('pointerup', soltar)
              caixaAtiva.current = false
              setCaixa(null)
              if (Math.hypot(ev.clientX - inicio.x, ev.clientY - inicio.y) < 4) {
                // ⌘ + clique: o nó embaixo do cursor entra ou sai da seleção
                const no = document.elementsFromPoint(ev.clientX, ev.clientY)
                  .map((el) => el.closest('.react-flow__node')).find(Boolean)?.getAttribute('data-id')
                if (no) setNodes((ns) => ns.map((n) => (n.id === no ? { ...n, selected: !n.selected } : n)))
                return
              }
              const a = rf.screenToFlowPosition({ x: Math.min(inicio.x, ev.clientX), y: Math.min(inicio.y, ev.clientY) })
              const b = rf.screenToFlowPosition({ x: Math.max(inicio.x, ev.clientX), y: Math.max(inicio.y, ev.clientY) })
              const dentro = new Set(rf.getIntersectingNodes({ x: a.x, y: a.y, width: b.x - a.x, height: b.y - a.y }, true).map((n) => n.id))
              setNodes((ns) => ns.map((n) => ({ ...n, selected: dentro.has(n.id) || (somar && !!n.selected) })))
            }
            alvo.addEventListener('pointermove', mover)
            alvo.addEventListener('pointerup', soltar)
          }}>
            {caixa && <div className="caixa-selecao" style={{ left: caixa.x, top: caixa.y, width: caixa.w, height: caixa.h }} />}
          </div>
        )}
        {confirmar && (() => {
          const extra = [...new Set(confirmar.flatMap((id) => galhoCompleto(arv, id)))].filter((id) => !confirmar.includes(id))
          const imgs = [...confirmar, ...extra].map((id) => porId.get(id)).filter((n) => n && (n.thumb || n.arquivo)).slice(0, 8) as No[]
          return (
            <div className="modal-fundo" onClick={() => setConfirmar(null)}>
              <div className="modal confirmar" role="alertdialog" onClick={(e) => e.stopPropagation()}
                onKeyDown={(e) => { if (e.key === 'Escape') setConfirmar(null) }}>
                <h3>{confirmar.length > 1 ? `Apagar ${confirmar.length} nós?` : `Apagar ${confirmar[0]}?`}</h3>
                <p className="mudo">{extra.length ? `Leva junto ${extra.length} ${extra.length === 1 ? 'nó que saiu' : 'nós que saíram'} daqui.` : 'Nada saiu daqui.'} ⌘Z desfaz.</p>
                {imgs.length > 0 && (
                  <div className="confirmar-imgs">
                    {imgs.map((n) => <img key={n.id} src={arquivoUrl(slug, n.thumb || n.arquivo)} alt="" />)}
                  </div>
                )}
                <div className="modal-acoes">
                  <span />
                  <div className="botoes">
                    <button type="button" className="secundario" onClick={() => setConfirmar(null)}>Cancelar</button>
                    <button type="button" className="perigo" autoFocus onClick={confirmarApagar}>Apagar</button>
                  </div>
                </div>
              </div>
            </div>
          )
        })()}
        {menu && <Menu x={menu.x} y={menu.y} itens={itensMenu(menu)} fechar={() => setMenu(null)} />}
        <input ref={arquivo} type="file" accept="image/*" multiple hidden
          onChange={(e) => { subir([...(e.target.files || [])], ondeSubir.current); e.target.value = '' }} />
      </div>
    </CanvasCtx.Provider>
  )
}

function corMinimapa(n: { data: unknown }) {
  const no = (n.data as { no: No }).no
  if (no.tipo === 'imagem') return no.estado === 'aprovada' ? '#13a35a' : no.estado === 'descartada' ? '#e3e5e9' : '#b9bec7'
  if (no.tipo === 'video') return no.estado === 'aprovada' ? '#13a35a' : '#7a6cf0'
  if (no.tipo === 'site') return no.estado === 'aprovada' ? '#13a35a' : '#0d9488'
  if (no.tipo === 'pedido') return '#3d5afe'
  if (no.tipo === 'referencia') return '#d0d4da'
  return '#111318'
}

/** O caminho no topo quando o canvas está recortado num nó (uma vista): pinar/despinar, o código e o nome. */
function Recorte({ raiz, pinado, copiar, mudarVista }: { raiz: No; pinado: boolean; copiar: (t: string) => void; mudarVista: (a: 'pinar' | 'despinar', id: string) => void }) {
  return (
    <>
      <span className="topo-sep">/</span>
      <button type="button" className={`ico topo-pin ${pinado ? 'on' : ''}`} title={pinado ? 'Despinar esta vista (volta ao histórico)' : 'Pinar esta vista'}
        onClick={() => mudarVista(pinado ? 'despinar' : 'pinar', raiz.id)}>
        {pinado ? <PinOff size={15} /> : <Pin size={15} />}
      </button>
      <button type="button" className="codigo" title="Copiar código para citar no chat" onClick={() => copiar(raiz.id)}>{raiz.id}</button>
      {raiz.nome && <span className="topo-img-nome">{raiz.nome}</span>}
    </>
  )
}

/** Miniatura do modo de organização (o desenho explica melhor que o texto). */
function PreviaModo({ modo }: { modo: ModoLayout }) {
  const r = (x: number, y: number, w = 14, h = 9) => <rect x={x} y={y} width={w} height={h} rx={2} />
  return (
    <svg viewBox="0 0 96 60" className="previa" aria-hidden>
      <g className="linhas">
        {modo === 'pilha'
          ? [6, 18, 30, 42].map((y) => <path key={y} d={`M26 30 C34 30 34 ${y + 4} 42 ${y + 4}`} />)
          : [8, 26, 44].map((y) => <path key={y} d={`M26 30 C34 30 34 ${y + 4} 42 ${y + 4}`} />)}
      </g>
      <rect className="pai" x={6} y={25} width={20} height={10} rx={2} />
      {modo === 'pilha'
        ? [6, 18, 30, 42].map((y) => <g key={y}>{r(42, y)}</g>)
        : modo === 'grade'
          ? [[42, 8], [42, 26], [42, 44], [62, 8], [62, 26]].map(([x, y]) => <g key={`${x}${y}`}>{r(x, y)}</g>)
          // N×N: blocos (galho = nó + filhos) em colunas de N
          : (() => {
              const n = modo === 'grade5' ? 5 : modo === 'grade4' ? 4 : 3
              const passo = 50 / n
              const blocos = []
              for (let c = 0; c < 2; c++) for (let i = 0; i < (c ? n - 1 : n); i++) blocos.push([38 + c * 30, 5 + i * passo])
              return blocos.map(([x, y]) => <g key={`${x}-${y}`}>{r(x, y, 8, passo - 3)}{r(x + 10, y, 8, (passo - 4) / 2)}{r(x + 10, y + (passo - 2) / 2, 8, (passo - 4) / 2)}</g>)
            })()}
    </svg>
  )
}

/** Miniatura do nível: quantas gerações ficam abertas. */
function PreviaNivel({ n }: { n: number }) {
  return (
    <svg viewBox="0 0 40 16" className="previa-nivel" aria-hidden>
      {[0, 1, 2, 3].map((i) => <rect key={i} x={i * 10} y={4} width={7} height={8} rx={1.5} className={i <= n ? 'on' : ''} />)}
    </svg>
  )
}
