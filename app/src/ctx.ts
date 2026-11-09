import { createContext, useContext } from 'react'
import type { EstadoProjeto, No } from './api'
import type { Arvore } from './layout'

export type Ctx = {
  slug: string
  estado: EstadoProjeto
  porId: Map<string, No>
  arv: Arvore
  alternar: (id: string) => void
  mudar: (id: string, campos: Partial<No>) => Promise<void>
  apagar: (id: string) => Promise<void>
  acao: <T>(fn: () => Promise<T>) => Promise<T | undefined>
  abrir: (id: string) => void
  painel: () => void   // abre o brief
  novoPedido: (entradas: string[], tela?: string, extra?: Partial<No>) => Promise<No | undefined>
  pedidoVideo: (imagem: string) => Promise<No | undefined>
  novaTela: () => Promise<unknown>
  enviar: (id: string) => Promise<void>
  copiar: (texto: string) => void
  focar: string | null
  pontos: boolean  // pedidos concluídos como pontos na linha
  limparFoco: () => void
  raiz?: string                  // a vista aberta (o nó a partir do qual o canvas está recortado)
  abrirVista: (id: string) => void
  mudarVista: (acao: 'pinar' | 'despinar', id: string) => void
}

export const CanvasCtx = createContext<Ctx | null>(null)

export function useCanvas(): Ctx {
  const c = useContext(CanvasCtx)
  if (!c) throw new Error('fora do canvas')
  return c
}
