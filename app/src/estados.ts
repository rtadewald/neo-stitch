import { EyeOff } from 'lucide-react'
import type { Estado } from './api'

/** A marca de uma imagem, vídeo, modelo ou HTML: só descartar (D). O que importa fica pinado (as vistas); não há mais
 *  "aprovar" — o estado `aprovada` dos nós antigos conta como sem marca. */
export const ESTADOS: { e: Estado; t: string; I: typeof EyeOff }[] = [
  { e: 'descartada', t: 'Descartar (D)', I: EyeOff },
]

/** D → descartada (ou undefined para outras teclas). */
export const estadoDaTecla = (tecla: string): Estado | undefined => (tecla.toLowerCase() === 'd' ? 'descartada' : undefined)

/** Clicar no estado que já está marcado volta para neutra. */
export const alternarEstado = (atual: Estado | undefined, e: Estado): Estado => (atual === e ? 'neutra' : e)
