import { Bot, Copy, X } from 'lucide-react'
import { Fragment, useEffect, useState, type ReactNode } from 'react'
import { api } from './api'

/** Markdown mínimo da spec: títulos, parágrafos, listas, tabelas, blocos de código, `código`, **negrito** e [links](url). */
function inline(texto: string): ReactNode[] {
  const partes = texto.split(/(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g)
  return partes.map((p, i) => {
    if (p.startsWith('`') && p.endsWith('`')) return <code key={i}>{p.slice(1, -1)}</code>
    if (p.startsWith('**') && p.endsWith('**')) return <b key={i}>{p.slice(2, -2)}</b>
    const l = p.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
    if (l) return <a key={i} href={l[2]} target="_blank" rel="noreferrer">{l[1]}</a>
    return <Fragment key={i}>{p}</Fragment>
  })
}

function Markdown({ texto }: { texto: string }) {
  const blocos: ReactNode[] = []
  const linhas = texto.split('\n')
  for (let i = 0; i < linhas.length; i++) {
    const l = linhas[i]
    if (l.startsWith('```')) {
      const corpo: string[] = []
      for (i++; i < linhas.length && !linhas[i].startsWith('```'); i++) corpo.push(linhas[i])
      blocos.push(<pre key={i}><code>{corpo.join('\n')}</code></pre>)
    } else if (l.startsWith('|')) {
      const linhasT: string[][] = []
      for (; i < linhas.length && linhas[i].startsWith('|'); i++) {
        if (!/^\|[\s|:-]+\|$/.test(linhas[i])) linhasT.push(linhas[i].slice(1, -1).split(' | ').map((c) => c.trim()))
      }
      i--
      const [cab, ...corpo] = linhasT
      blocos.push(
        <table key={i}><thead><tr>{cab.map((c, k) => <th key={k}>{inline(c)}</th>)}</tr></thead>
          <tbody>{corpo.map((r, j) => <tr key={j}>{r.map((c, k) => <td key={k}>{inline(c)}</td>)}</tr>)}</tbody></table>)
    } else if (/^#{1,3} /.test(l)) {
      const n = l.indexOf(' ')
      const H = (['h1', 'h2', 'h3'] as const)[n - 1]
      blocos.push(<H key={i}>{inline(l.slice(n + 1))}</H>)
    } else if (/^(\s*[-*] |\d+\. )/.test(l)) {
      const ordenada = /^\d+\. /.test(l)
      const itens: string[] = []
      for (; i < linhas.length && /^(\s*[-*] |\d+\. |\s{2,}\S)/.test(linhas[i]); i++) {
        if (/^\s{2,}\S/.test(linhas[i]) && !/^\s*[-*] /.test(linhas[i])) itens[itens.length - 1] += ' ' + linhas[i].trim()
        else itens.push(linhas[i].replace(/^(\s*[-*] |\d+\. )/, ''))
      }
      i--
      const L = ordenada ? 'ol' : 'ul'
      blocos.push(<L key={i}>{itens.map((t, k) => <li key={k}>{inline(t)}</li>)}</L>)
    } else if (l.trim()) {
      const par = [l]
      for (; i + 1 < linhas.length && linhas[i + 1].trim() && !/^(#|```|\||\s*[-*] |\d+\. )/.test(linhas[i + 1]); i++) par.push(linhas[i + 1])
      blocos.push(<p key={i}>{inline(par.join(' '))}</p>)
    }
  }
  return <div className="markdown">{blocos}</div>
}

/** A spec para delegar vídeo → HTML a outros agentes, com a instrução pronta para cada vídeo da imagem. */
export function SpecAgentes({ videos, fechar, copiar }: { videos: { id: string; nome: string }[]; fechar: () => void; copiar: (t: string, aviso?: string) => void }) {
  const [spec, setSpec] = useState<{ texto: string; caminho: string; raiz: string } | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  useEffect(() => { api.specAgentes().then(setSpec).catch((e) => setErro((e as Error).message)) }, [])
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => { if (e.key === 'Escape') fechar() }
    window.addEventListener('keydown', tecla)
    return () => window.removeEventListener('keydown', tecla)
  }, [fechar])
  const instrucao = (v: string) =>
    `No repositório do Neo Stitch (${spec?.raiz}), leia o AGENTS.md e o docs/AGENTES.md e implemente o vídeo ${v} como HTML vivo. Seu nome de agente: "<nome curto, ex.: Codex 5.6>".`

  return (
    <div className="modal-fundo" onClick={fechar}>
      <div className="modal spec-agentes" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="ico fechar" title="Fechar (Esc)" onClick={fechar}><X size={18} /></button>
        <header>
          <Bot size={18} />
          <h2>Delegar para outros agentes</h2>
          {spec && <button type="button" className="codigo" title="Copiar o caminho da spec" onClick={() => copiar(spec.caminho, 'caminho copiado')}>docs/AGENTES.md</button>}
        </header>
        {videos.length > 0 && (
          <div className="spec-videos">
            <span className="mudo">Instrução pronta para colar no agente:</span>
            {videos.map((v) => (
              <button key={v.id} type="button" className="spec-chip" title={`Copiar a instrução para ${v.id} (${v.nome})`}
                onClick={() => copiar(instrucao(v.id), `instrução para ${v.id} copiada`)}><Copy size={12} /> {v.id} <i>{v.nome}</i></button>
            ))}
          </div>
        )}
        {erro && <p className="erro-texto">{erro}</p>}
        {spec ? <Markdown texto={spec.texto} /> : !erro && <span className="pulso" />}
      </div>
    </div>
  )
}
