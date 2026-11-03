import { Check, EyeOff } from 'lucide-react'
import type { Estado } from './api'

/** As marcas de uma imagem, vídeo, modelo ou HTML (botões e atalhos A/D). Aprovada é o verde: serve para filtrar (⌘A). */
export const ESTADOS: { e: Estado; t: string; I: typeof Check }[] = [
  { e: 'aprovada', t: 'Aprovar (A)', I: Check },
  { e: 'descartada', t: 'Descartar (D)', I: EyeOff },
]

/** A/D → o estado (ou undefined para outras teclas). */
export const estadoDaTecla = (tecla: string): Estado | undefined =>
  ({ a: 'aprovada', d: 'descartada' } as const)[tecla.toLowerCase() as 'a' | 'd']

/** Clicar no estado que já está marcado volta para neutra. */
export const alternarEstado = (atual: Estado | undefined, e: Estado): Estado => (atual === e ? 'neutra' : e)
