import { History, Network, Pin, PinOff } from 'lucide-react'
import { arquivoUrl, rotaVista, type EstadoProjeto, type No } from './api'

/** A miniatura de uma vista: a do nó; um pedido usa a 1ª saída (ou entrada) com imagem; um HTML (IMG/vN), a da imagem. */
export function capaDe(slug: string, cod: string, porId: Map<string, No>): string | null {
  let no = porId.get(cod.split('/')[0])
  if (no?.tipo === 'pedido') no = [...(no.saidas || []), ...(no.entradas || [])].map((c) => porId.get(c)).find((n) => n?.thumb || n?.arquivo) || no
  if (!no) return null
  const arq = no.thumb || (no.tipo === 'imagem' || no.tipo === 'referencia' ? no.arquivo : undefined)
  return arq ? arquivoUrl(slug, arq) : null
}

/**
 * A barra da esquerda: as vistas pinadas em cima e, abaixo, o histórico das últimas abertas (até 10). Uma vista é o canvas
 * recortado a partir de um nó; abrir põe no topo do histórico, pinar sobe para os pinados, despinar volta ao histórico.
 * Pinado é à mão e independe do aprovado (o verde, que só filtra).
 */
export function Trilho({ slug, estado, porId, ativo, voltar, mudarVista }: {
  slug: string; estado: EstadoProjeto; porId: Map<string, No>; ativo?: string; voltar?: boolean
  mudarVista: (acao: 'pinar' | 'despinar', id: string) => void
}) {
  const { pinados, historico } = estado.vistas
  if (!voltar && !pinados.length && !historico.length) return null
  const item = (cod: string, pinado: boolean) => {
    const no = porId.get(cod.split('/')[0])
    const capa = capaDe(slug, cod, porId)
    return (
      <div key={cod} className={`trilho-item ${ativo === cod ? 'on' : ''} ${pinado ? 'pinado' : ''}`}>
        <a href={rotaVista(slug, cod)} title={`${cod}${no?.nome || no?.titulo ? ` · ${no?.nome || no?.titulo}` : ''}`}>
          {capa ? <img src={capa} alt="" /> : <span className="sem-capa">{cod}</span>}
        </a>
        <button type="button" className="trilho-pin" title={pinado ? 'Despinar (volta ao histórico)' : 'Pinar'}
          onClick={() => mudarVista(pinado ? 'despinar' : 'pinar', cod)}>
          {pinado ? <PinOff size={12} /> : <Pin size={12} />}
        </button>
      </div>
    )
  }
  return (
    <nav className="trilho" aria-label="Vistas pinadas e histórico">
      {voltar && (
        <>
          <a href={`#/p/${slug}`} className="trilho-ico" title={`Voltar ao canvas de ${estado.projeto.nome}`}><Network size={17} /></a>
          <span className="trilho-sep" />
        </>
      )}
      {pinados.length > 0 && <span className="trilho-secao" title="Pinados"><Pin size={14} /></span>}
      {pinados.map((c) => item(c, true))}
      {historico.length > 0 && (
        <>
          {pinados.length > 0 && <span className="trilho-sep" />}
          <span className="trilho-secao" title="Histórico: as últimas vistas abertas"><History size={14} /></span>
          {historico.map((c) => item(c, false))}
        </>
      )}
    </nav>
  )
}
