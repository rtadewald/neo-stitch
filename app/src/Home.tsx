import { AppWindow, ArrowUp, Flag, Globe, LayoutDashboard, Pin, Plus, Smartphone, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, dinheiro, rotaVista, type ResumoProjeto } from './api'

const TIPOS = [
  { v: 'site', r: 'Site', I: Globe },
  { v: 'webapp', r: 'Webapp', I: AppWindow },
  { v: 'dashboard', r: 'Dashboard', I: LayoutDashboard },
  { v: 'app', r: 'App', I: Smartphone },
] as const

export function Home() {
  const [lista, setLista] = useState<ResumoProjeto[] | null>(null)
  const [novo, setNovo] = useState(false)

  useEffect(() => {
    api.projetos().then(setLista).catch(() => setLista([]))
  }, [])

  // o projeto selecionado (clique) mostra, embaixo, as imagens dele em desenvolvimento; abrir = botão ou duplo clique
  const [sel, setSel] = useState<string | null>(() => { try { return localStorage.getItem('neo:home-sel') } catch { return null } })
  const selecionar = (slug: string | null) => {
    setSel(slug)
    try { if (slug) localStorage.setItem('neo:home-sel', slug); else localStorage.removeItem('neo:home-sel') } catch { /* sem storage */ }
  }
  const atual = lista?.find((p) => p.slug === sel)
  const abrir = (slug: string) => { location.hash = `#/p/${slug}` }
  // com a versão final marcada, o projeto vai para o fim da grade, com a bandeira na capa (o concluído mais recente primeiro)
  const ativos = lista?.filter((p) => !p.final)
  const concluidos = lista?.filter((p) => p.final).sort((a, b) => (b.concluido || '').localeCompare(a.concluido || ''))

  const cartao = (p: ResumoProjeto) => {
    const Tipo = TIPOS.find((t) => t.v === p.tipo)?.I || AppWindow
    const on = p.slug === sel
    return (
      <div key={p.slug} role="button" tabIndex={0} className={`cartao projeto ${on ? 'sel' : ''}`}
        title={`${p.nome}: clique para ver as vistas pinadas · duplo clique abre`}
        onClick={(e) => { e.stopPropagation(); selecionar(p.slug) }} onDoubleClick={() => abrir(p.slug)}
        onKeyDown={(e) => { if (e.key === 'Enter') abrir(p.slug) }}>
        <div className="capa">
          {p.capa ? <img src={p.capa} alt="" draggable={false} /> : <Tipo size={28} strokeWidth={1.3} />}
          {(p.pinados || []).length > 0 && <span className="selo-pin contagem" title={`${p.pinados!.length} vistas pinadas`}><Pin size={12} /> {p.pinados!.length}</span>}
          {p.final && <span className="selo-final capa-final" title={`Versão final: ${p.final}`}><Flag size={12} strokeWidth={2.2} /></span>}
          {on && <button type="button" className="primario abrir" onClick={(e) => { e.stopPropagation(); abrir(p.slug) }} title="Abrir o canvas (↵)">Abrir</button>}
        </div>
        <div className="cartao-info">
          <span className="cartao-nome">{p.nome}</span>
          <span className="prefixo">{p.prefixo}</span>
          <span className="cresce" />
          <span className="mudo" title={`${p.imagens} imagens · ${dinheiro(p.custos.total)}`}>{p.imagens}</span>
        </div>
      </div>
    )
  }

  return (
    <main className="home" onClick={() => selecionar(null)}>
      <header className="home-topo">
        <img src="/favicon.svg" alt="" width={28} height={28} />
        <h1>Neo Stitch</h1>
      </header>
      <h2 className="home-secao">Projetos</h2>
      <section className="grade">
        <button type="button" className="cartao novo" onClick={(e) => { e.stopPropagation(); setNovo(true) }} title="Novo projeto">
          <Plus size={28} strokeWidth={1.5} />
        </button>
        {ativos?.map(cartao)}
        {concluidos?.map(cartao)}
      </section>
      {atual && (
        <div onClick={(e) => e.stopPropagation()}>
          <h2 className="home-secao vistas" title="As vistas pinadas deste projeto">
            <Pin size={15} /> Pinados <span className="mudo">· {atual.nome}</span>
          </h2>
          {(atual.pinados || []).length ? (
            <section className="grade pinados">
              {atual.pinados!.map((f) => (
                <a key={f.id} className="cartao" href={rotaVista(atual.slug, f.id)}>
                  <div className="capa">{f.thumb ? <img src={f.thumb} alt="" /> : <span className="sem-capa">{f.id}</span>}<span className="selo-pin"><Pin size={12} /></span></div>
                  <div className="cartao-info">
                    <span className="cartao-nome">{f.id}</span>
                    <span className="mudo">{f.nome}</span>
                  </div>
                </a>
              ))}
            </section>
          ) : <p className="mudo">Nada pinado ainda: no canvas, abra a partir de um nó e pine a vista.</p>}
        </div>
      )}
      {novo && <NovoProjeto fechar={() => setNovo(false)} />}
    </main>
  )
}

function NovoProjeto({ fechar }: { fechar: () => void }) {
  const [nome, setNome] = useState('')
  const [tipo, setTipo] = useState<string>('webapp')
  const [descricao, setDescricao] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [indo, setIndo] = useState(false)

  const criar = async () => {
    if (!nome.trim()) return
    setIndo(true)
    try {
      const p = await api.criarProjeto({ nome: nome.trim(), tipo, descricao })
      location.hash = `#/p/${p.slug}`
    } catch (e) {
      setErro((e as Error).message)
      setIndo(false)
    }
  }

  return (
    <div className="modal-fundo" onClick={fechar}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={(e) => { e.preventDefault(); criar() }}>
        <button type="button" className="ico fechar" title="Fechar" onClick={fechar}><X size={18} /></button>
        <input className="campo-nome" autoFocus placeholder="Nome do projeto" value={nome} onChange={(e) => setNome(e.target.value)} />
        <div className="tipos" role="radiogroup">
          {TIPOS.map(({ v, r, I }) => (
            <button key={v} type="button" role="radio" aria-checked={tipo === v} className={tipo === v ? 'on' : ''} onClick={() => setTipo(v)}>
              <I size={20} strokeWidth={1.6} />
              <span>{r}</span>
            </button>
          ))}
        </div>
        <textarea rows={6} placeholder="Descreva o projeto: para quem é, o que a tela precisa mostrar, o clima, referências…"
          value={descricao} onChange={(e) => setDescricao(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) criar() }} />
        {erro && <p className="erro-texto">{erro}</p>}
        <div className="modal-acoes">
          <span className="mudo">{descricao.trim() ? 'O Claude propõe direções de estilo ao criar' : ''}</span>
          <button type="submit" className="enviar" disabled={!nome.trim() || indo} title="Criar (⌘↵)"><ArrowUp size={18} /></button>
        </div>
      </form>
    </div>
  )
}
