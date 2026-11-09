import { Handle, Position, useStore, type Node, type NodeProps } from '@xyflow/react'
import {
  AppWindow, ArrowUp, Bot, Box, Check, ChevronDown, Code2, ExternalLink, Flag, FolderOpen, Globe, LayoutDashboard, Link2, LoaderCircle, MessageCircle,
  ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Clapperboard, Focus, Image as ImageIcon, Layers, Palette, Pin, PinOff, Minus, Play, Plus, Quote, RotateCw, Smartphone, Sparkles, Trash2, TriangleAlert, X, Archive,
} from 'lucide-react'
import { memo, useEffect, useRef, useState, type ReactNode } from 'react'
import { api, arquivoUrl, dinheiro, urlModelo, type ModeloVideo, type No } from './api'
import { useCanvas } from './ctx'
import { ESTADOS, alternarEstado } from './estados'
import { LARG, descendentes, ehPonto, medidaImagem, ocultosSob, razaoDe } from './layout'

export type NoRF = Node<{ no: No }>

const ICONE_TIPO = { site: Globe, app: Smartphone, dashboard: LayoutDashboard, webapp: AppWindow }

function Alcas({ entrada = true, saida = true }: { entrada?: boolean; saida?: boolean }) {
  return (
    <>
      {entrada && <Handle type="target" position={Position.Left} className="alca" />}
      {saida && <Handle type="source" position={Position.Right} className="alca" />}
    </>
  )
}

function Botao({ titulo, onClick, children, className = '', disabled }: {
  titulo: string; onClick: (e: React.MouseEvent) => void; children: ReactNode; className?: string; disabled?: boolean
}) {
  return (
    <button type="button" className={`ico nodrag ${className}`} title={titulo} aria-label={titulo} disabled={disabled}
      onClick={(e) => { e.stopPropagation(); onClick(e) }} onDoubleClick={(e) => e.stopPropagation()}>
      {children}
    </button>
  )
}

/** O botão do galho, à direita do nó: recolhe/expande tudo o que saiu dele (mostra +N quando fechado). */
function Galho({ no }: { no: No }) {
  const { arv, alternar, porId, pontos } = useCanvas()
  const n = descendentes(arv, no.id)
  const ocultos = ocultosSob(arv, no)
  if (!n) return null
  // no modo pontos, quem recolhe é o próprio ponto do pedido: aqui o botão só aparece com o galho todo fechado (para abrir)
  // ou quando algum filho não é um ponto
  const fs = arv.filhos.get(no.id) || []
  if (pontos && !ocultos && fs.every((f) => { const x = porId.get(f); return x && ehPonto(x) })) return null
  return (
    <button type="button" className={`galho nodrag ${ocultos ? 'fechado' : ''}`}
      title={ocultos ? `Mostrar ${ocultos} nós escondidos` : 'Recolher este galho'}
      onClick={(e) => { e.stopPropagation(); alternar(no.id) }} onDoubleClick={(e) => e.stopPropagation()}>
      {ocultos ? <><span>{ocultos}</span><ChevronRight size={14} /></> : <ChevronLeft size={14} />}
    </button>
  )
}

/** Recolher/expandir o galho, para as barras de ação do nó (some quando o nó não tem filhos). */
function BotaoGalho({ no }: { no: No }) {
  const { arv, alternar } = useCanvas()
  const n = descendentes(arv, no.id)
  const ocultos = ocultosSob(arv, no)
  if (!n) return null
  return (
    <Botao titulo={ocultos ? `Mostrar o bloco (${ocultos} nós escondidos)` : `Ocultar o bloco (${n} nós)`} className={ocultos ? 'on' : ''}
      onClick={() => alternar(no.id)}>
      {ocultos ? <ChevronsRight size={14} /> : <ChevronsLeft size={14} />}
    </Botao>
  )
}

/** As vistas no hover de todo cartão: pinar/despinar (a barra lateral) e abrir a partir daqui (o canvas recortado neste nó). */
function BotaoAbrir({ no }: { no: No }) {
  const { raiz, abrirVista, mudarVista, estado } = useCanvas()
  const pinado = estado.vistas.pinados.includes(no.id)
  return (
    <>
      <Botao titulo={pinado ? 'Despinar (volta ao histórico)' : 'Pinar'} className={pinado ? 'on pin' : ''}
        onClick={() => mudarVista(pinado ? 'despinar' : 'pinar', no.id)}>{pinado ? <PinOff size={14} /> : <Pin size={14} />}</Botao>
      {raiz !== no.id && <Botao titulo="Abrir a partir daqui" onClick={() => abrirVista(no.id)}><Focus size={14} /></Botao>}
    </>
  )
}

/** A versão final do projeto: vira a capa e o projeto, concluído, vai para o fim da página inicial (só uma por projeto). */
function BotaoFinal({ id }: { id: string }) {
  const { slug, estado, acao } = useCanvas()
  const on = estado.projeto.final === id
  return (
    <Botao titulo={on ? 'Versão final do projeto · clique para desmarcar (o projeto volta a ficar em andamento)'
      : 'Marcar como a versão final do projeto (vira a capa; o projeto fica concluído)'} className={on ? 'on final' : ''}
      onClick={() => acao(() => api.mudarProjeto(slug, { final: on ? null : id }))}><Flag size={14} /></Botao>
  )
}

/** A miniatura (640 px) basta até certo zoom; passou disso, o cartão carrega o arquivo original por cima (só re-renderiza ao cruzar). */
function useNitida(no: No, w: number) {
  const passou = useStore((s) => s.transform[2] * Math.min(window.devicePixelRatio || 1, 3) * w > 600)
  return passou && !!no.thumb && !!no.arquivo && no.thumb !== no.arquivo
}
function Nitida({ no, w }: { no: No; w: number }) {
  const { slug } = useCanvas()
  return useNitida(no, w) ? <img className="nitida" src={arquivoUrl(slug, no.arquivo)} alt="" draggable={false} /> : null
}

function Codigo({ id }: { id: string }) {
  const { copiar } = useCanvas()
  return (
    <button type="button" className="codigo nodrag" title="Copiar código para citar no chat"
      onClick={(e) => { e.stopPropagation(); copiar(id) }}>
      {id}
    </button>
  )
}

// ---------- Brief ----------

export const BriefNode = memo(function BriefNode({ data, selected }: NodeProps<NoRF>) {
  const { no } = data
  const { estado, mudar, acao, slug, painel, novoPedido, novaTela, enviar } = useCanvas()
  const Icone = ICONE_TIPO[estado.projeto.tipo] || AppWindow
  const texto = estado.brief.replace(/^#.*\n/, '').replace(/^>.*$/gm, '').replace(/\*\*|__|`/g, '').replace(/^\s*[-*]\s+/gm, '· ').replace(/\n{2,}/g, '\n').trim()
  const dirs = no.direcoes || []
  const ativas = dirs.filter((d) => d.ativa)
  const telas = estado.nos.filter((n) => n.tipo === 'tela')
  const ocupado = no.status === 'enviado' || no.status === 'trabalhando'
  const inicio = useRef({ x: 0, y: 0 })  // clique sem arrastar abre o brief; arrastar move o nó

  const gerar = async () => {
    const p = await novoPedido([], telas[0]?.id, {
      variacoes: ativas.map((d) => ({ nome: d.nome, tese: d.tese })),
      intencao: `Exploração divergente: ${ativas.map((d) => d.nome).join(' · ')}`,
      quantidade: ativas.length,
    })
    if (p) await enviar(p.id)
  }

  return (
    <div className={`no brief ${selected ? 'sel' : ''}`} style={{ width: LARG.brief }}>
      <div className="brief-topo">
        <span className="tipo-ico" title={estado.projeto.tipo}><Icone size={16} /></span>
        <h2>{estado.projeto.nome}</h2>
        <Codigo id={no.id} />
      </div>
      <button type="button" className={`brief-texto ${texto ? '' : 'vazio'}`} title="Editar o brief (arraste para mover)"
        onPointerDown={(e) => { inicio.current = { x: e.clientX, y: e.clientY } }}
        onClick={(e) => { if (Math.hypot(e.clientX - inicio.current.x, e.clientY - inicio.current.y) < 4) painel() }}>
        {texto || 'Descreva o projeto…'}
      </button>
      {dirs.length > 0 && (
        <div className="direcoes nodrag">
          {dirs.map((d, i) => (
            <button key={d.nome + i} type="button" className={`chip ${d.ativa ? 'on' : ''}`} title={d.tese}
              onClick={() => mudar(no.id, { direcoes: dirs.map((x, j) => (j === i ? { ...x, ativa: !x.ativa } : x)) })}>
              {d.nome}
            </button>
          ))}
        </div>
      )}
      <div className="brief-acoes">
        {ocupado ? (
          <span className="status-claude"><LoaderCircle size={14} className="gira" /> Claude</span>
        ) : dirs.length ? (
          <>
            <Botao titulo="Propor outras direções" onClick={() => acao(() => api.enviar(slug, no.id))}><RotateCw size={15} /></Botao>
            <button type="button" className="primario nodrag" disabled={!ativas.length} onClick={gerar}
              title={`Gerar uma imagem por direção (${ativas.length})`}>
              <Sparkles size={15} /> {ativas.length}
            </button>
          </>
        ) : (
          <button type="button" className="primario nodrag" disabled={!texto} onClick={() => acao(() => api.enviar(slug, no.id))}
            title="O Claude propõe direções de estilo a partir do brief">
            <Sparkles size={15} /> Direções
          </button>
        )}
      </div>
      <Botao titulo="Nova tela" className="mais-lateral" onClick={novaTela}>
        <Plus size={16} />
      </Botao>
      <Galho no={no} />
      <Alcas entrada={false} />
    </div>
  )
})

// ---------- Tela ----------

export const TelaNode = memo(function TelaNode({ data, selected }: NodeProps<NoRF>) {
  const { no } = data
  const { estado, mudar, novoPedido } = useCanvas()
  const [editando, setEditando] = useState(false)
  const Icone = ICONE_TIPO[estado.projeto.tipo] || AppWindow
  return (
    <div className={`no tela ${selected ? 'sel' : ''}`} style={{ width: LARG.tela }} onDoubleClick={() => setEditando(true)}>
      <Icone size={15} className="tela-ico" />
      {editando ? (
        <input className="nodrag tela-input" autoFocus defaultValue={no.titulo}
          onBlur={(e) => { setEditando(false); if (e.target.value.trim()) mudar(no.id, { titulo: e.target.value.trim() }) }}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === 'Escape') (e.target as HTMLInputElement).blur() }} />
      ) : (
        <span className="tela-nome" title="Duplo clique para renomear">{no.titulo}</span>
      )}
      <span className="tela-abrir"><BotaoAbrir no={no} /></span>
      <Botao titulo="Novo pedido nesta tela" className="mais" onClick={() => novoPedido([], no.id)}><Plus size={15} /></Botao>
      <Galho no={no} />
      <Alcas />
    </div>
  )
})

// ---------- Pedido ----------

function Entradas({ no, editavel }: { no: No; editavel: boolean }) {
  const { porId, slug, mudar, abrir } = useCanvas()
  const ent = (no.entradas || []).map((e) => porId.get(e)).filter(Boolean) as No[]
  if (!ent.length) return null
  return (
    <div className="entradas">
      {ent.map((e) => (
        <div key={e.id} className={`entrada ${e.tipo}`} title={e.nome || e.titulo || e.id}>
          <img src={arquivoUrl(slug, e.thumb || e.arquivo)} alt="" draggable={false} onDoubleClick={() => abrir(e.id)} />
          {editavel && (
            <button type="button" className="tira nodrag" title="Tirar do pedido"
              onClick={() => mudar(no.id, { entradas: (no.entradas || []).filter((x) => x !== e.id) })}>
              <X size={10} />
            </button>
          )}
        </div>
      ))}
    </div>
  )
}

function Seletor({ valor, opcoes, titulo, onChange }: {
  valor: string; opcoes: { v: string; r: string }[]; titulo: string; onChange: (v: string) => void
}) {
  const atual = opcoes.find((o) => o.v === valor)
  return (
    <label className="seletor nodrag" title={titulo}>
      <span>{atual?.r || valor}</span>
      <ChevronDown size={12} />
      <select value={valor} onChange={(e) => onChange(e.target.value)} aria-label={titulo}>
        {opcoes.map((o) => <option key={o.v} value={o.v}>{o.r}</option>)}
      </select>
    </label>
  )
}

/** Pedido: card inteiro — ou, no modo "pontos", o concluído vira um ponto na linha que abre o card no hover/clique. */
export const PedidoNode = memo(function PedidoNode(props: NodeProps<NoRF>) {
  const { pontos } = useCanvas()
  return pontos && ehPonto(props.data.no) ? <PedidoPonto {...props} /> : <PedidoCheio {...props} />
})

function PedidoCheio({ id, data, selected }: NodeProps<NoRF>) {
  const { no } = data
  const { estado, mudar, apagar, enviar, focar, limparFoco } = useCanvas()
  const rascunho = no.status === 'rascunho'
  const [texto, setTexto] = useState(no.intencao || '')
  const ref = useRef<HTMLTextAreaElement>(null)
  const tempo = useRef<number>(0)

  useEffect(() => { if (document.activeElement !== ref.current) setTexto(no.intencao || '') }, [no.intencao])
  useEffect(() => {
    // o React Flow deixa o nó invisível até medi-lo: tenta o foco até pegar
    if (focar !== id) return
    let n = 0
    const t = window.setInterval(() => {
      ref.current?.focus()
      if (document.activeElement === ref.current || ++n > 30) { window.clearInterval(t); limparFoco() }
    }, 40)
    return () => window.clearInterval(t)
  }, [focar, id, limparFoco])
  useEffect(() => {
    const t = ref.current
    if (t) { t.style.height = '0px'; t.style.height = `${Math.min(220, t.scrollHeight)}px` }
  }, [texto])

  const salvar = (v: string) => {
    window.clearTimeout(tempo.current)
    tempo.current = window.setTimeout(() => mudar(no.id, { intencao: v }), 500)
  }
  const disparar = async () => {
    window.clearTimeout(tempo.current)
    if (texto !== no.intencao) await mudar(no.id, { intencao: texto })
    await enviar(no.id)
  }
  const video = no.midia === 'video'
  const podeEnviar = video ? !!(no.modelos || []).length && !!(no.entradas || []).length
    : !!(texto.trim() || (no.entradas || []).length || (no.variacoes || []).length)
  const modelos = Object.entries(estado.modelos).map(([v, m]) => ({ v, r: m.nome }))
  const qtd = no.quantidade || 3
  const variacoes = no.variacoes || []
  // comum aos rascunhos de imagem e de vídeo: o campo da intenção e o fim da barra (literal · apagar · enviar)
  const campo = (placeholder: string) => (
    <textarea ref={ref} className="nodrag nowheel intencao" value={texto} rows={2} placeholder={placeholder}
      onChange={(e) => { setTexto(e.target.value); salvar(e.target.value) }}
      onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && podeEnviar) disparar() }} />
  )
  const fimBarra = (dicaLiteral: string, estimativa?: ReactNode) => (
    <>
      <Botao titulo={no.literal ? 'Literal: vai exatamente o seu texto' : `${dicaLiteral} (clique para literal)`}
        className={`literal ${no.literal ? 'on' : ''}`} onClick={() => mudar(no.id, { literal: !no.literal })}>
        <Quote size={14} />
      </Botao>
      <span className="cresce" />
      {estimativa}
      <Botao titulo="Apagar rascunho (⌘Z desfaz)" className="sutil" onClick={() => apagar(no.id)}><Trash2 size={14} /></Botao>
      <button type="button" className="enviar nodrag" disabled={!podeEnviar} onClick={disparar} title="Enviar ao Claude (⌘↵)">
        <ArrowUp size={16} />
      </button>
    </>
  )

  return (
    <div className={`no pedido st-${no.status} ${video ? 'pedido-video' : ''} ${selected ? 'sel' : ''}`} style={{ width: LARG.pedido }}>
      {video && <span className="selo-midia" title="Pedido de vídeo"><Clapperboard size={12} /> vídeo</span>}
      <Entradas no={no} editavel={rascunho} />
      {rascunho && video ? (
        <>
          {campo('Como a tela ganha vida? (o que se mexe, o que acende…)')}
          <ModelosVideo no={no} />
          <div className="pedido-barra">
            <Seletor titulo="Duração" valor={String(no.duracao || 6)} onChange={(v) => mudar(no.id, { duracao: Number(v) })}
              opcoes={[4, 5, 6, 8, 10].map((d) => ({ v: String(d), r: `${d}s` }))} />
            <Seletor titulo="Resolução" valor={no.resolucao === '1080p' ? '1080p' : '720p'} onChange={(v) => mudar(no.id, { resolucao: v })}
              opcoes={[{ v: '720p', r: '720p' }, { v: '1080p', r: '1080p' }]} />
            {fimBarra('O Claude reescreve como prompt de vídeo, com a interface protegida',
              <span className="estimativa" title="Estimativa (sem áudio)">≈ {dinheiro(custoVideo(no, estado.modelos_video))}</span>)}
          </div>
        </>
      ) : rascunho ? (
        <>
          {variacoes.length > 0 && (
            <div className="direcoes">{variacoes.map((v) => <span key={v.nome} className="chip on" title={v.tese}>{v.nome}</span>)}</div>
          )}
          {campo((no.entradas || []).length ? 'O que mudar?' : 'O que você quer ver?')}
          <div className="pedido-barra">
            <div className="passo nodrag" title="Quantas imagens">
              <button type="button" onClick={() => mudar(no.id, { quantidade: Math.max(1, qtd - 1) })} aria-label="menos"><Minus size={12} /></button>
              <span>{qtd}</span>
              <button type="button" onClick={() => mudar(no.id, { quantidade: Math.min(12, qtd + 1) })} aria-label="mais"><Plus size={12} /></button>
            </div>
            <Seletor titulo="Formato" valor={no.aspecto || '16:9'} onChange={(v) => mudar(no.id, { aspecto: v })}
              opcoes={estado.aspectos.map((a) => ({ v: a, r: a }))} />
            <Seletor titulo="Modelo" valor={no.modelo || ''} onChange={(v) => mudar(no.id, { modelo: v })} opcoes={modelos} />
            {fimBarra('O Claude reescreve como prompt completo')}
          </div>
        </>
      ) : <PedidoLido no={no} />}
      <Codigo id={no.id} />
      <Galho no={no} />
      <Alcas />
    </div>
  )
}

/** O pedido já enviado: a intenção, o status e os prompts usados (no card inteiro e no card que abre do ponto). */
function PedidoLido({ no }: { no: No }) {
  const { enviar } = useCanvas()
  const [verPrompt, setVerPrompt] = useState(false)
  const prompts = (no.variacoes || []).filter((v) => v.prompt)
  return (
    <>
      {no.intencao && <p className="intencao-lida">{no.intencao}</p>}
      {verPrompt && (
        <div className="prompts nodrag nowheel">
          {prompts.length ? prompts.map((v, i) => (
            <div key={i}>{v.nome && <b>{v.nome}</b>}<p>{v.prompt}</p></div>
          )) : <p className="mudo">Sem prompt registrado.</p>}
        </div>
      )}
      <div className="pedido-barra lida">
        <StatusPedido no={no} />
        <span className="cresce" />
        {no.legado && <span className="selo" title="Importado: gerado antes do Neo Stitch"><Archive size={12} /></span>}
        {(prompts.length > 0 || no.status === 'concluido') && (
          <Botao titulo={verPrompt ? 'Esconder prompts' : 'Ver os prompts usados'} className={verPrompt ? 'on' : ''} onClick={() => setVerPrompt(!verPrompt)}>
            <Quote size={14} />
          </Botao>
        )}
        {no.status === 'erro' && (
          <Botao titulo="Tentar de novo" onClick={() => enviar(no.id)}><RotateCw size={14} /></Botao>
        )}
        <BotaoAbrir no={no} />
        <BotaoGalho no={no} />
      </div>
    </>
  )
}

/** O pedido concluído como um ponto na linha entre a imagem de origem e as que saíram dele. É também o botão do galho:
 *  clicar recolhe ou mostra o que saiu dele (fechado, mostra quantos estão escondidos); o mouse em cima abre o card do pedido. */
function PedidoPonto({ data, selected }: NodeProps<NoRF>) {
  const { no } = data
  const { arv, alternar } = useCanvas()
  const [sobre, setSobre] = useState(false)
  const fechar = useRef(0)
  const entra = () => { window.clearTimeout(fechar.current); setSobre(true) }
  const sai = () => { fechar.current = window.setTimeout(() => setSobre(false), 160) }
  const aberto = sobre
  const video = no.midia === 'video'
  const ocultos = ocultosSob(arv, no)
  return (
    <div className={`no pedido-ponto ${video ? 'video' : ''} ${aberto ? 'aberto' : ''} ${ocultos ? 'fechado' : ''} ${selected ? 'sel' : ''}`}
      onMouseEnter={entra} onMouseLeave={sai}>
      <button type="button" className="ponto nodrag" aria-expanded={!ocultos}
        title={`${ocultos ? `Mostrar ${ocultos} nós escondidos` : 'Recolher o que saiu deste pedido'}${no.custo != null ? ` · ${dinheiro(no.custo)}` : ''}`}
        onClick={(e) => { e.stopPropagation(); alternar(no.id) }} onDoubleClick={(e) => e.stopPropagation()}>
        {ocultos ? <span className="ocultos">{ocultos}</span> : video ? <Clapperboard size={11} /> : <Sparkles size={11} />}
      </button>
      {aberto && (
        <div className="pedido-pop" onClick={(e) => e.stopPropagation()} onDoubleClick={(e) => e.stopPropagation()}>
          <div className={`no pedido st-${no.status} ${video ? 'pedido-video' : ''}`} style={{ width: LARG.pedido }}>
            {video && <span className="selo-midia" title="Pedido de vídeo"><Clapperboard size={12} /> vídeo</span>}
            <Entradas no={no} editavel={false} />
            <PedidoLido no={no} />
            <Codigo id={no.id} />
          </div>
        </div>
      )}
      <Alcas />
    </div>
  )
}
/** Estimativa do pedido de vídeo: o custo medido de 6 s de cada modelo, proporcional à duração que ele de fato faz
 *  (a suportada mais próxima: os Hailuo não descem de 5 s) · 1080p ≈ ×1,6. */
function custoVideo(no: No, cat: Record<string, ModeloVideo>) {
  const fator = no.resolucao === '1080p' ? 1.6 : 1
  const pedida = no.duracao || 6
  return (no.modelos || []).reduce((s, id) => {
    const m = cat[id]
    if (!m) return s + 0.1 * pedida
    const dur = m.duracoes?.length ? m.duracoes.reduce((a, b) => (Math.abs(b - pedida) < Math.abs(a - pedida) ? b : a)) : pedida
    return s + (m.custo_6s ? m.custo_6s / 6 : m.preco_s) * dur * fator
  }, 0)
}

/** Os modelos de vídeo do pedido: chips (clique tira) + seletor para adicionar (com o custo de 6 s). */
function ModelosVideo({ no }: { no: No }) {
  const { estado, mudar } = useCanvas()
  const cat = estado.modelos_video || {}
  const marcados = no.modelos || []
  const resto = Object.entries(cat).filter(([id]) => !marcados.includes(id))
  return (
    <div className="modelos-video nodrag">
      {marcados.map((m) => (
        <button key={m} type="button" className="chip on" title={`${m} · ~${dinheiro(cat[m]?.custo_6s || 0)} por 6 s${cat[m]?.ranking ? ` · ${cat[m].ranking}` : ''}${cat[m]?.teste ? ` · teste: ${cat[m].teste}` : ''} — clique para tirar`}
          onClick={() => mudar(no.id, { modelos: marcados.filter((x) => x !== m) })}>
          {cat[m]?.nome || m} <X size={10} />
        </button>
      ))}
      <label className="chip mais-modelo" title="Adicionar um modelo">
        <Plus size={11} /> modelo
        <select value="" onChange={(e) => e.target.value && mudar(no.id, { modelos: [...marcados, e.target.value] })} aria-label="Adicionar modelo">
          <option value="">Adicionar…</option>
          {resto.map(([id, m]) => <option key={id} value={id}>{m.nome} · {dinheiro(m.custo_6s)}/6s{m.nota ? ` · ${m.nota}` : ''}</option>)}
        </select>
      </label>
    </div>
  )
}

function StatusPedido({ no }: { no: No }) {
  if (no.status === 'enviado') return <span className="status fila" title="Na fila do Claude"><span className="pulso" /> fila</span>
  if (no.status === 'trabalhando') return <span className="status" title="O Claude está gerando"><LoaderCircle size={14} className="gira" /></span>
  if (no.status === 'erro') return <span className="status erro" title={no.erro}><TriangleAlert size={14} /> {no.erro?.slice(0, 40)}</span>
  return (
    <span className="status ok" title={`${(no.saidas || []).length} imagens`}>
      <Check size={14} /> {(no.saidas || []).length} {no.custo ? `· ${dinheiro(no.custo)}` : ''}
    </span>
  )
}

// ---------- Imagem e referência ----------

/** O botão descartar da barra de ações de uma imagem, vídeo ou modelo (o pinar vem à parte). */
function BotoesEstado({ no }: { no: No }) {
  const { mudar } = useCanvas()
  const estado = no.estado || 'neutra'
  return (
    <>
      {ESTADOS.map(({ e, t, I }) => (
        <Botao key={e} titulo={t} className={estado === e ? `on ${e}` : ''} onClick={() => mudar(no.id, { estado: alternarEstado(estado, e) })}>
          <I size={14} />
        </Botao>
      ))}
    </>
  )
}

export const ImagemNode = memo(function ImagemNode({ data, selected }: NodeProps<NoRF>) {
  const { no } = data
  const { slug, abrir } = useCanvas()
  const { w, h } = medidaImagem(no)
  const estado = no.estado || 'neutra'
  return (
    <div className={`no imagem ${no.asset ? 'asset' : ''} es-${estado} ${selected ? 'sel' : ''}`} style={{ width: w }} onDoubleClick={() => abrir(no.id)}>
      <div className="moldura">
        <div className="quadro" style={{ height: no.gerando || no.erro ? Math.round(w / razaoDe(no.aspecto)) : h }}>
        {no.gerando ? (
          <div className="brilho" title="Gerando…" />
        ) : no.erro ? (
          <div className="falhou" title={no.erro}><TriangleAlert size={18} /></div>
        ) : (
          <><img src={arquivoUrl(slug, no.thumb || no.arquivo)} alt={no.nome || no.id} draggable={false} /><Nitida no={no} w={w} /></>
        )}
        {!no.gerando && (
          <div className="acoes">
            <BotoesEstado no={no} />
            <BotaoFinal id={no.id} />
            <BotaoGalho no={no} />
            <BotaoAbrir no={no} />
          </div>
        )}
        </div>
        <Legenda no={no} />
      </div>
      <Galho no={no} />
      <Alcas />
    </div>
  )
})

/** A legenda fixa de todo cartão de mídia: o tipo (ícone na cor dele), o código (clique copia), o nome e o custo. */
const TIPO = {
  imagem: [ImageIcon, 'Imagem'], asset: [Layers, 'Asset: gerado durante uma página'], referencia: [Link2, 'Referência'], video: [Clapperboard, 'Vídeo'], modelo: [Box, 'Modelo 3D'], site: [Code2, 'HTML'], ds: [Palette, 'Design System'],
} as const
function Legenda({ no, extra, custo }: { no: No; extra?: ReactNode; custo?: number }) {
  const [I, rotulo] = TIPO[(no.asset ? 'asset' : no.tipo) as keyof typeof TIPO] || TIPO.imagem
  const n = no.comentarios?.length || 0
  const nome = no.tipo === 'site' ? null : no.nome || no.titulo
  const final = useCanvas().estado.projeto.final === no.id
  return (
    <div className="legenda">
      {final && <span className="selo-final" title="Versão final do projeto"><Flag size={11} strokeWidth={2.2} /></span>}
      <span className="legenda-tipo" title={rotulo}><I size={13} strokeWidth={1.8} /></span>
      <Codigo id={no.id} />
      {nome && <span className="nome" title={nome}>{nome}</span>}
      <span className="cresce" />
      {extra}
      <Custo no={custo === undefined ? no : { ...no, custo }} />
      {n > 0 && <span className="bolha" title={`${n} comentário(s)`}><MessageCircle size={11} /> {n}</span>}
    </div>
  )
}

/** O custo do que gerou o cartão (imagem, vídeo, 3D, HTML). Sem registro (importadas, falhas) não mostra nada. */
function Custo({ no }: { no: No }) {
  if (no.custo == null) return null
  return <span className="bolha" title="Custo da geração">{dinheiro(no.custo)}</span>
}

export const RefNode = memo(function RefNode({ data, selected }: NodeProps<NoRF>) {
  const { no } = data
  const { slug, abrir, apagar } = useCanvas()
  const { w, h } = medidaImagem(no)
  return (
    <div className={`no imagem ref ${selected ? 'sel' : ''}`} style={{ width: w }} onDoubleClick={() => abrir(no.id)}>
      <div className="moldura">
        <div className="quadro" style={{ height: h }}>
        <img src={arquivoUrl(slug, no.thumb || no.arquivo)} alt={no.titulo} draggable={false} />
        <Nitida no={no} w={w} />
        <span className="marca refm" title="Referência"><Link2 size={12} /></span>
        <div className="acoes">
          <BotaoGalho no={no} />
          <BotaoAbrir no={no} />
          <Botao titulo="Apagar (⌘Z desfaz)" onClick={() => apagar(no.id)}><Trash2 size={14} /></Botao>
        </div>
        </div>
        <Legenda no={no} />
      </div>
      <Galho no={no} />
      <Alcas />
    </div>
  )
})

/** Vídeo gerado: mostra um quadro; com o mouse em cima, toca sem som. */
export const VideoNode = memo(function VideoNode({ data, selected }: NodeProps<NoRF>) {
  const { no } = data
  const { slug, abrir } = useCanvas()
  const [tocando, setTocando] = useState(false)
  const { w, h } = medidaImagem(no)
  const estado = no.estado || 'neutra'
  return (
    <div className={`no imagem video es-${estado} ${selected ? 'sel' : ''}`} style={{ width: w }} onDoubleClick={() => abrir(no.id)}
      onMouseEnter={() => setTocando(true)} onMouseLeave={() => setTocando(false)}>
      <div className="moldura">
        <div className="quadro" style={{ height: h }}>
        {no.gerando ? (
          <div className="brilho" title="Gerando vídeo…" />
        ) : no.erro ? (
          <div className="falhou" title={no.erro}><TriangleAlert size={18} /></div>
        ) : (
          <>
            <img src={arquivoUrl(slug, no.thumb || '')} alt={no.nome || no.id} draggable={false} />
            {tocando && no.arquivo && <video src={arquivoUrl(slug, no.arquivo)} autoPlay muted loop playsInline />}
          </>
        )}
        <span className="marca play"><Play size={10} fill="currentColor" /></span>
        {!no.gerando && (
          <div className="acoes"><BotoesEstado no={no} /><BotaoFinal id={no.id} /><BotaoAbrir no={no} /></div>
        )}
        </div>
        <Legenda no={no} extra={no.duracao ? <i className="legenda-meta">{no.duracao}s</i> : null} />
      </div>
      <Galho no={no} />
      <Alcas />
    </div>
  )
})

/** Um modelo 3D (imagem → 3D): a capa é um render no ângulo do quadro; dois cliques abrem o visualizador 3D. */
export const ModeloNode = memo(function ModeloNode({ data, selected }: NodeProps<NoRF>) {
  const { no } = data
  const { slug } = useCanvas()
  const { w, h } = medidaImagem(no)
  const estado = no.estado || 'neutra'
  return (
    <div className={`no imagem modelo es-${estado} ${selected ? 'sel' : ''}`} style={{ width: w }}
      onDoubleClick={() => window.open(urlModelo(slug, no), '_blank', 'noreferrer')} title="Dois cliques abrem o modelo em 3D">
      <div className="moldura">
        <div className="quadro" style={{ height: h }}>
        <img src={arquivoUrl(slug, no.thumb || '')} alt={no.nome || no.id} draggable={false} />
        <span className="marca play"><Box size={11} /></span>
        <div className="acoes"><BotoesEstado no={no} /><BotaoFinal id={no.id} /><BotaoAbrir no={no} /></div>
        </div>
        <Legenda no={no} />
      </div>
      <Galho no={no} />
      <Alcas />
    </div>
  )
})

const PARADO_MS = 15 * 60 * 1000  // sem atualizar o impl.json por mais que isso, "trabalhando" vira "parado?" (docs/AGENTES.md)

/** O relógio de quem mostra tempo relativo: re-renderiza a cada 30 s. */
function useAgora() {
  const [agora, setAgora] = useState(() => Date.now())
  useEffect(() => { const t = setInterval(() => setAgora(Date.now()), 30000); return () => clearInterval(t) }, [])
  return agora
}
const haQuanto = (iso: string | undefined, agora: number) => {
  if (!iso) return ''
  const min = Math.max(0, Math.round((agora - Date.parse(iso)) / 60000))
  return min < 1 ? 'agora' : min < 60 ? `há ${min} min` : `há ${Math.round(min / 60)} h`
}

/**
 * Uma versão de HTML (impl/<imagem>/<versão>/). Pronta: a página roda dentro do quadro (sem capturar o mouse, para o canvas
 * navegar) e dois cliques abrem interativa em outra aba. Em andamento: o agente (impl.json), a etapa e o progresso.
 */
export const SiteNode = memo(function SiteNode({ data, selected }: NodeProps<NoRF>) {
  const { no } = data
  const { slug, acao } = useCanvas()
  const agora = useAgora()
  const { img, versao, trabalho: t, foto } = no.site!
  const { w, h } = medidaImagem(no)
  const pasta = `/projects/${slug}/impl/${img}/${versao}/`
  const url = pasta + 'index.html'
  const pronto = !t || t.status === 'pronto'
  // em andamento com prévia (ex.: a página da fase 1): ela roda no quadro e o andamento fica por cima.
  // aguardando: o agente parou esperando a sua aprovação dessa prévia (impl.py aguardar)
  const aguardando = t?.status === 'aguardando'
  const previa = !pronto && (t?.status === 'trabalhando' || aguardando) && t?.previa ? pasta + t.previa : null
  const abrir = pronto ? url : previa
  // pronta, o quadro mostra o print (captura.png) e só roda a página viva com o mouse em cima ou selecionada: dezenas de
  // páginas com WebGL rodando juntas travam o canvas. Sem print ainda (o servidor tira ao fundo), mostra a imagem de origem
  const [mouse, setMouse] = useState(false)
  const espera = useRef(0)
  const viva = !pronto || mouse || selected
  const poster = foto ? `${pasta}${t?.captura || 'captura.png'}?v=${foto}` : `${pasta}reference.png`
  const parado = t?.status === 'trabalhando' && !!t.atualizado && agora - Date.parse(t.atualizado) > PARADO_MS
  const estado = no.estado || 'neutra'
  const titulo = t ? `${t.agente} · ${t.status}${t.base ? ` · evolução da ${t.base}: ${t.pedido || ''}` : ''}${t.etapa && !pronto ? ` · ${t.etapa}` : ''}${t.nota ? ` · ${t.nota}` : ''}` : 'HTML vivo'
  return (
    <div className={`no imagem site es-${estado} ${selected ? 'sel' : ''} ${pronto ? '' : `obra st-${t!.status}`} ${parado ? 'parado' : ''}`}
      style={{ width: w }} title={titulo} onDoubleClick={() => abrir && window.open(abrir, '_blank', 'noreferrer')}>
      <div className="moldura">
        <div className="quadro" style={{ height: h }}
          onMouseEnter={() => { espera.current = window.setTimeout(() => setMouse(true), 250) }}
          onMouseLeave={() => { window.clearTimeout(espera.current); setMouse(false) }}>
        {pronto && <img className="foto-pagina" src={poster} alt="" draggable={false} />}
        {viva && (pronto || previa) && <iframe src={abrir!} title={no.id} loading="lazy" tabIndex={-1} inert />}
        {abrir && (
          <button type="button" className="abrir-centro nodrag" title={pronto ? 'Abrir a página em outra aba (interativa)' : 'Abrir a prévia em outra aba'}
            onClick={(e) => { e.stopPropagation(); window.open(abrir, '_blank', 'noreferrer') }}>
            <ExternalLink size={16} /> Abrir
          </button>
        )}
        {!pronto && (
          <div className={`obra-painel ${previa ? 'sobre' : ''}`}>
            <span className="agente-chip grande"><Bot size={14} strokeWidth={1.8} /> {t!.agente}</span>
            {t!.pedido && <p className="obra-pedido">“{t!.pedido}”</p>}
            <p className="obra-etapa">
              {t!.status === 'trabalhando' && !parado && <LoaderCircle size={13} className="gira" />}
              {t!.status === 'erro' ? (t!.erro || 'erro') : t!.status === 'abandonado' ? (t!.nota || 'abandonado') : t!.etapa || 'trabalhando'}
            </p>
            {aguardando && <span className="aguardando-chip" title="O agente parou: aprove (ou peça ajustes) no chat com ele">aguardando você</span>}
            {t!.status === 'trabalhando' && <div className="obra-barra"><i style={{ width: `${Math.round((t!.progresso || 0) * 100)}%` }} /></div>}
            <span className="obra-tempo">{parado ? `parado? última notícia ${haQuanto(t!.atualizado, agora)}` : t!.status === 'trabalhando' ? `${Math.round((t!.progresso || 0) * 100)}% · ${haQuanto(t!.atualizado, agora)}` : aguardando ? `aguardando ${haQuanto(t!.atualizado, agora)}` : t!.status}</span>
          </div>
        )}
        {/* o canto esquerdo, longe da barra de ações: abrir a página em outra aba e a pasta */}
        <div className="canto-esq">
          {abrir && <Botao titulo={pronto ? 'Abrir a página em outra aba (interativa)' : 'Abrir a prévia em outra aba'} className="abrir-pagina"
            onClick={() => window.open(abrir, '_blank', 'noreferrer')}><ExternalLink size={14} /></Botao>}
          <Botao titulo="Abrir a pasta no Finder" className="abrir-pagina"
            onClick={() => acao(() => api.pastaImpl(slug, img, versao))}><FolderOpen size={14} /></Botao>
        </div>
        <div className="acoes">
          {t && pronto && ESTADOS.map(({ e, t: rotulo, I }) => (
            // descartar a versão
            <Botao key={e} titulo={rotulo} className={estado === e ? `on ${e}` : ''}
              onClick={() => acao(() => api.mudarImpl(slug, img, versao, alternarEstado(estado, e)))}><I size={14} /></Botao>
          ))}
          <BotaoFinal id={no.id} />
          <BotaoAbrir no={no} />
        </div>
        </div>
        <Legenda no={no} extra={t && <span className="agente-chip" title={`Feito por ${t.agente}`}><Bot size={11} strokeWidth={1.8} /> {t.agente}</span>} custo={t?.custo} />
      </div>
      <Alcas />
    </div>
  )
})

/** Design system: um catálogo (ds/<código>/design-system.html) destacado como a referência. O quadro mostra o print; dois cliques abrem o catálogo. */
export const DsNode = memo(function DsNode({ data, selected }: NodeProps<NoRF>) {
  const { no } = data
  const { slug } = useCanvas()
  const { w, h } = medidaImagem(no)
  const estado = no.estado || 'neutra'
  const abrir = () => { if (no.pagina) window.open(arquivoUrl(slug, no.pagina), '_blank', 'noreferrer') }
  return (
    <div className={`no imagem ds es-${estado} ${selected ? 'sel' : ''}`} style={{ width: w }} onDoubleClick={abrir}>
      <div className="moldura">
        <div className="quadro" style={{ height: h }}>
          <img src={arquivoUrl(slug, no.thumb || no.arquivo)} alt={no.nome || no.id} draggable={false} />
          <Nitida no={no} w={w} />
          <button type="button" className="abrir-centro nodrag" title="Abrir o design system em outra aba"
            onClick={(e) => { e.stopPropagation(); abrir() }}>
            <ExternalLink size={16} /> Abrir
          </button>
          <div className="acoes">
            <BotoesEstado no={no} />
            <BotaoAbrir no={no} />
          </div>
        </div>
        <Legenda no={no} />
      </div>
      <Alcas />
    </div>
  )
})

export const nodeTypes = { brief: BriefNode, tela: TelaNode, pedido: PedidoNode, imagem: ImagemNode, referencia: RefNode, video: VideoNode, modelo: ModeloNode, site: SiteNode, ds: DsNode }

