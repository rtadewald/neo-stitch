import { useCallback, useMemo, useRef } from 'react'
import { api, type No, type Pos } from './api'

type Passo = { desfazer: () => Promise<unknown>; refazer: () => Promise<unknown> }

// o valor "vazio" de cada campo, para desfazer uma mudança num nó que ainda não tinha o campo
const VAZIO: Partial<Record<keyof No, unknown>> = { estado: 'neutra', recolhido: false, escondidos: [], desloc: null, entradas: [], direcoes: [], literal: false }
// texto digitado tem o desfazer do próprio campo (⌘Z dentro do textarea)
const FORA = new Set<keyof No>(['intencao'])

/**
 * ⌘Z / ⌘⇧Z do canvas. Cada mudança feita por aqui guarda o "antes" e o "depois"; `emLote` junta várias mudanças
 * (arrastar uma seleção, marcar várias imagens, expandir tudo) num passo só.
 */
export function useHistorico(opts: {
  slug: string
  porId: () => Map<string, No>
  mudar: (id: string, campos: Partial<No>) => Promise<void>
  posicoes: (mapa: Record<string, Pos>) => Promise<void>
  acao: <T>(fn: () => Promise<T>) => Promise<T | undefined>
}) {
  const { slug, porId, mudar, posicoes, acao } = opts
  const pilhas = useRef<{ desfazer: Passo[]; refazer: Passo[] }>({ desfazer: [], refazer: [] })
  const lote = useRef<Passo[] | null>(null)

  const registrar = useCallback((p: Passo) => {
    if (lote.current) { lote.current.push(p); return }
    pilhas.current.desfazer.push(p)
    if (pilhas.current.desfazer.length > 100) pilhas.current.desfazer.shift()
    pilhas.current.refazer = []
  }, [])

  const emLote = useCallback(async (fn: () => unknown) => {
    const anterior = lote.current
    lote.current = []
    try {
      await fn()
    } finally {
      const passos = lote.current || []
      lote.current = anterior
      if (passos.length) registrar({
        desfazer: async () => { for (const p of [...passos].reverse()) await p.desfazer() },
        refazer: async () => { for (const p of passos) await p.refazer() },
      })
    }
  }, [registrar])

  const mudarH = useCallback((id: string, campos: Partial<No>) => {
    const no = porId().get(id)
    const chaves = (Object.keys(campos) as (keyof No)[]).filter((k) => !FORA.has(k))
    if (no && chaves.length) {
      const antes = Object.fromEntries(chaves.map((k) => [k, no[k] ?? VAZIO[k] ?? null])) as Partial<No>
      const depois = Object.fromEntries(chaves.map((k) => [k, campos[k]])) as Partial<No>
      registrar({ desfazer: () => mudar(id, antes), refazer: () => mudar(id, depois) })
    }
    return mudar(id, campos)
  }, [porId, mudar, registrar])

  const posicoesH = useCallback((mapa: Record<string, Pos>) => {
    const antes: Record<string, Pos> = {}
    for (const id of Object.keys(mapa)) {
      const p = porId().get(id)?.pos
      if (p) antes[id] = p
    }
    if (Object.keys(antes).length) registrar({ desfazer: () => posicoes(antes), refazer: () => posicoes(mapa) })
    return posicoes(mapa)
  }, [porId, posicoes, registrar])

  /** Apagar (rascunho, referência) vai para a lixeira do projeto; desfazer traz de volta. */
  const apagarH = useCallback(async (id: string) => {
    const r = await acao(() => api.apagarNo(slug, id))
    if (r) registrar({
      desfazer: () => acao(() => api.restaurarNo(slug, id)),
      refazer: () => acao(() => api.apagarNo(slug, id)),
    })
  }, [slug, acao, registrar])

  /** Um nó recém-criado: desfazer o apaga (vai para a lixeira), refazer o restaura. */
  const criado = useCallback((id: string) => {
    registrar({
      desfazer: () => acao(() => api.apagarNo(slug, id)),
      refazer: () => acao(() => api.restaurarNo(slug, id)),
    })
  }, [slug, acao, registrar])

  const desfazer = useCallback(async () => {
    const p = pilhas.current.desfazer.pop()
    if (!p) return false
    await p.desfazer()
    pilhas.current.refazer.push(p)
    return true
  }, [])

  const refazer = useCallback(async () => {
    const p = pilhas.current.refazer.pop()
    if (!p) return false
    await p.refazer()
    pilhas.current.desfazer.push(p)
    return true
  }, [])

  return useMemo(
    () => ({ mudar: mudarH, posicoes: posicoesH, apagar: apagarH, criado, passo: registrar, emLote, desfazer, refazer }),
    [mudarH, posicoesH, apagarH, criado, registrar, emLote, desfazer, refazer],
  )
}
