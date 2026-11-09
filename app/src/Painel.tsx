import { X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api } from './api'
import { useCanvas } from './ctx'

/** Gaveta da direita: o brief (editável). */
export function Painel({ fechar }: { fechar: () => void }) {
  const { estado, slug, acao } = useCanvas()
  const [texto, setTexto] = useState(estado.brief)
  const editando = useRef(false)

  useEffect(() => { if (!editando.current) setTexto(estado.brief) }, [estado.brief])

  return (
    <aside className="painel">
      <div className="painel-topo">
        <b>Brief</b>
        <button type="button" className="ico" title="Fechar" onClick={fechar}><X size={18} /></button>
      </div>
      <textarea className="brief-editor" value={texto} spellCheck={false}
        placeholder="Para quem é, o que a tela precisa mostrar, referências, o clima…"
        onFocus={() => { editando.current = true }}
        onChange={(e) => setTexto(e.target.value)}
        onBlur={() => { editando.current = false; if (texto !== estado.brief) acao(() => api.brief(slug, texto)) }} />
    </aside>
  )
}
