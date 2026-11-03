import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type EstadoProjeto, type No, type Pos } from './api'

/**
 * O estado do projeto, sincronizado com o disco: busca a cada 2 s (o servidor responde "igual" quando nada mudou),
 * e cada mudança local é aplicada na hora (otimista) e confirmada pela próxima leitura.
 */
export function useProjeto(slug: string) {
  const [estado, setEstado] = useState<EstadoProjeto | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const rev = useRef<string | undefined>(undefined)
  const locais = useRef(new Map<string, { campos: Partial<No>; ate: number }>())

  const carregar = useCallback(
    async (forcar = false) => {
      try {
        const r = await api.estado(slug, forcar ? undefined : rev.current)
        if (r.igual) return
        rev.current = r.rev
        const agora = Date.now()
        for (const [id, l] of locais.current) if (l.ate < agora) locais.current.delete(id)
        r.nos = r.nos.map((n) => {
          const l = locais.current.get(n.id)
          return l ? { ...n, ...l.campos } : n
        })
        for (const [id, l] of locais.current) if (id.includes('/') && 'desloc' in l.campos) r.avancos = comDesloc(r.avancos, id, l.campos.desloc ?? null)
        setEstado(r)
        setErro(null)
      } catch (e) {
        setErro((e as Error).message)
      }
    },
    [slug],
  )

  useEffect(() => {
    rev.current = undefined
    setEstado(null)
    carregar(true)
    const t = setInterval(() => document.visibilityState === 'visible' && carregar(), 2000)
    return () => clearInterval(t)
  }, [carregar])

  /** Muda um nó localmente agora e no servidor em seguida. */
  const mudar = useCallback(
    async (id: string, campos: Partial<No>) => {
      locais.current.set(id, { campos: { ...(locais.current.get(id)?.campos || {}), ...campos }, ate: Date.now() + 4000 })
      // uma versão de HTML (<IMG>/<vN>) não é um arquivo de nó: só o desloc dela vale, e vai para o impl.json
      const [img, versao] = id.split('/')
      if (versao) {
        if (!('desloc' in campos)) return
        const d = campos.desloc ?? null
        setEstado((e) => (e ? { ...e, avancos: comDesloc(e.avancos, id, d) } : e))
        try {
          await api.deslocImpl(slug, img, versao, d)
        } catch (e) {
          locais.current.delete(id)
          setErro((e as Error).message)
        }
        carregar(true)
        return
      }
      setEstado((e) => (e ? { ...e, nos: e.nos.map((n) => (n.id === id ? { ...n, ...campos } : n)) } : e))
      try {
        await api.mudarNo(slug, id, campos)
      } catch (e) {
        locais.current.delete(id)
        setErro((e as Error).message)
      }
      carregar(true)
    },
    [slug, carregar],
  )

  const posicoes = useCallback(
    async (mapa: Record<string, { x: number; y: number }>) => {
      if (!Object.keys(mapa).length) return
      for (const [id, pos] of Object.entries(mapa))
        locais.current.set(id, { campos: { ...(locais.current.get(id)?.campos || {}), pos }, ate: Date.now() + 4000 })
      setEstado((e) => (e ? { ...e, nos: e.nos.map((n) => (mapa[n.id] ? { ...n, pos: mapa[n.id] } : n)) } : e))
      await api.posicoes(slug, mapa).catch((e) => setErro(e.message))
    },
    [slug],
  )

  /** Roda uma ação no servidor, mostra o erro se houver e recarrega. */
  const acao = useCallback(
    async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
      try {
        const r = await fn()
        await carregar(true)
        return r
      } catch (e) {
        setErro((e as Error).message)
      }
    },
    [carregar],
  )

  return { estado, erro, setErro, carregar, mudar, posicoes, acao }
}

/** Os avanços com o desloc de uma versão de HTML (<IMG>/<vN>) trocado. */
function comDesloc(avancos: EstadoProjeto['avancos'], id: string, desloc: Pos | null): EstadoProjeto['avancos'] {
  const [img, versao] = id.split('/')
  const av = avancos?.[img]
  const t = av?.trabalhos?.[versao]
  if (!av || !t) return avancos
  return { ...avancos, [img]: { ...av, trabalhos: { ...av.trabalhos, [versao]: { ...t, desloc } } } }
}
