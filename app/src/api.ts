export type Estado = 'neutra' | 'aprovada' | 'descartada'   // aprovada = o verde (filtro); o favorito é o pinado
export type Status = 'rascunho' | 'enviado' | 'trabalhando' | 'concluido' | 'erro' | 'proposto'
export type Pos = { x: number; y: number }

export type Pin = Pos & { t?: number }  // t: segundo do vídeo (comentário num vídeo)
export type Comentario = { id: string; autor: 'voce' | 'claude'; texto: string; pin: Pin | null; criado: string }
export type Direcao = { nome: string; tese: string; ativa: boolean }
export type Variacao = { nome: string; prompt?: string; tese?: string }


export type No = {
  id: string
  tipo: 'brief' | 'tela' | 'pedido' | 'imagem' | 'referencia' | 'video' | 'modelo' | 'site'
  criado: string
  atualizado?: string
  pos: Pos | null
  recolhido?: boolean
  escondidos?: string[]
  desloc?: Pos | null
  comentarios: Comentario[]
  titulo?: string
  pai?: string
  tela?: string | null
  // brief
  status?: Status
  direcoes?: Direcao[]
  // pedido
  entradas?: string[]
  intencao?: string
  literal?: boolean
  quantidade?: number
  modelo?: string
  asset?: boolean         // imagem gerada durante uma página (placa de fundo, personagem isolado, textura): não é uma geração de tela
  aspecto?: string
  resolucao?: string
  saidas?: string[]
  variacoes?: Variacao[]
  custo?: number
  erro?: string
  legado?: boolean
  midia?: 'imagem' | 'video'
  modelos?: string[]
  duracao?: number
  segundos?: number
  // imagem / referência
  pedido?: string
  giro?: number     // modelo 3D: graus para ficar de frente no visualizador
  nome?: string
  prompt?: string
  estado?: Estado
  arquivo?: string
  thumb?: string
  largura?: number
  altura?: number
  gerando?: boolean
  // site: uma versão de HTML (impl/<imagem>/<versão>/), montada no app a partir dos avanços (não é um arquivo de nó)
  site?: { img: string; versao: string; trabalho?: Trabalho; foto?: number }   // foto: mtime do captura.png (o print)
}

export type Projeto = {
  slug: string
  nome: string
  prefixo: string
  tipo: 'site' | 'app' | 'dashboard' | 'webapp'
  padroes: { modelo: string; aspecto: string; resolucao: string; quantidade: number }
  tetos: { imagens_por_pedido: number; diario_usd: number }
  layout?: 'pilha' | 'grade' | 'grade3' | 'grade4' | 'grade5'
  compacto?: boolean      // o "Distribuir": os galhos sobem para os vãos do canvas
  pinados?: string[]      // as vistas pinadas (a mais recente em cima)
  historico?: string[]    // as últimas vistas abertas (até 10); uma vista está num lugar só
  final?: string          // a versão final (um nó ou um HTML <IMG>/<vN>): vira a capa e o projeto fica concluído
  concluido?: string      // quando a versão final foi marcada
}

export type EstadoProjeto = {
  rev: string
  igual?: boolean
  projeto: Projeto
  nos: No[]
  custos: { total: number; hoje: number }
  brief: string
  diario: string
  modelos: Record<string, { nome: string; preco: number }>
  modelos_video: Record<string, ModeloVideo>
  aspectos: string[]
  ouvinte: boolean
  avancos: Record<string, Avanco>
  vistas: { pinados: string[]; historico: string[] }   // a barra lateral (só o que foi pinado, e o histórico)
}

/** Imagem que avançou (o "fogo"): os vídeos que saíram dela e as tentativas de HTML em impl/<código>/vN/. */
// origens: versão → vídeo de onde saiu · trabalhos: versão → a ficha impl.json do agente que a faz (docs/AGENTES.md)
export type Avanco = { videos: string[]; impl: string[]; origens?: Record<string, string>; trabalhos?: Record<string, Trabalho>; capturas?: Record<string, number> }
export type Trabalho = {
  agente: string; status: 'trabalhando' | 'aguardando' | 'pronto' | 'erro' | 'abandonado'; etapa?: string; progresso?: number
  inicio?: string; atualizado?: string; fim?: string | null; nota?: string; erro?: string | null
  base?: string; pedido?: string  // evolução: a versão de onde saiu (v1 → v1.1) e a alteração pedida
  entradas?: string[]             // as imagens tiradas do vídeo de onde a versão parte (a estática e a viva)
  estado?: Estado                 // a aprovação do usuário (só o app escreve)
  desloc?: Pos | null             // o card arrastado no canvas: deslocamento sobre o lugar automático (só o app escreve)
  custo?: number                  // US$ gastos em APIs nesta versão (imagens, 3D, descrições), declarado pelo agente
  previa?: string                 // enquanto trabalha ou aguarda: uma página para ver (relativa à pasta da versão, ex.: phase1/index.html)
  captura?: string                // um print da página (relativo à pasta da versão): a deixa ser entrada de um pedido de imagens
}
export type Vista = { id: string; thumb: string | null; nome: string }

export type ModeloVideo = { nome: string; duracoes: number[]; resolucoes: string[]; custo_6s: number; preco_s: number; primeiro_ultimo: boolean; tempo_teste_s?: number; nota?: string; ranking?: string; teste?: string }

export type ResumoProjeto = {
  slug: string
  nome: string
  prefixo: string
  tipo: Projeto['tipo']
  capa: string | null
  final?: string | null
  concluido?: string | null
  imagens: number
  custos: { total: number; hoje: number }
  atualizado: string
  pinados: Vista[]
}

async function req<T>(metodo: string, url: string, corpo?: unknown, cabecalhos?: Record<string, string>): Promise<T> {
  const binario = corpo instanceof Blob
  const r = await fetch(url, {
    method: metodo,
    headers: binario ? cabecalhos : corpo !== undefined ? { 'Content-Type': 'application/json', ...cabecalhos } : cabecalhos,
    body: binario ? corpo : corpo !== undefined ? JSON.stringify(corpo) : undefined,
  })
  const dados = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(dados.erro || `HTTP ${r.status}`)
  return dados as T
}

const P = (slug: string) => `/api/projetos/${slug}`

export const api = {
  projetos: () => req<ResumoProjeto[]>('GET', '/api/projetos'),
  mudarImpl: (slug: string, img: string, versao: string, estado: Estado) => req<Trabalho>('PATCH', `${P(slug)}/impl/${img}/${versao}`, { estado }),
  pastaImpl: (slug: string, img: string, versao: string) => req<{ ok: boolean }>('POST', `${P(slug)}/impl/${img}/${versao}/pasta`),
  deslocImpl: (slug: string, img: string, versao: string, desloc: Pos | null) => req<Trabalho>('PATCH', `${P(slug)}/impl/${img}/${versao}`, { desloc }),
  specAgentes: () => req<{ texto: string; caminho: string; raiz: string }>('GET', '/api/spec/agentes'),
  criarProjeto: (d: { nome: string; tipo: string; descricao: string }) => req<ResumoProjeto>('POST', '/api/projetos', d),
  estado: (slug: string, rev?: string) => req<EstadoProjeto>('GET', `${P(slug)}${rev ? `?rev=${rev}` : ''}`),
  mudarProjeto: (slug: string, d: Partial<Omit<Projeto, 'final'>> & { final?: string | null }) => req<Projeto>('PATCH', P(slug), d),
  vista: (slug: string, acao: 'abrir' | 'pinar' | 'despinar', id: string) =>
    req<{ pinados: string[]; historico: string[] }>('POST', `${P(slug)}/vistas`, { acao, id }),
  brief: (slug: string, texto: string) => req('PUT', `${P(slug)}/brief`, { texto }),
  criarNo: (slug: string, d: Partial<No>) => req<No>('POST', `${P(slug)}/nos`, d),
  mudarNo: (slug: string, id: string, d: Partial<No>) => req<No>('PATCH', `${P(slug)}/nos/${id}`, d),
  apagarNo: (slug: string, id: string) => req('DELETE', `${P(slug)}/nos/${id}`),
  restaurarNo: (slug: string, id: string) => req<No>('POST', `${P(slug)}/nos/${id}/restaurar`),
  posicoes: (slug: string, d: Record<string, Pos>) => req('PUT', `${P(slug)}/posicoes`, d),
  enviar: (slug: string, id: string) => req<No>('POST', `${P(slug)}/nos/${id}/enviar`),
  comentar: (slug: string, id: string, texto: string, pin: Pin | null) =>
    req<Comentario>('POST', `${P(slug)}/nos/${id}/comentarios`, { texto, pin }),
  apagarComentario: (slug: string, id: string, cid: string) => req('DELETE', `${P(slug)}/nos/${id}/comentarios/${cid}`),
  subirRef: (slug: string, arquivo: File | Blob, nome: string, pos?: Pos, tela?: string) =>
    req<No>('POST', `${P(slug)}/refs`, arquivo, {
      'Content-Type': arquivo.type || 'image/png',
      'X-Nome': encodeURIComponent(nome),
      ...(pos ? { 'X-Pos': `${Math.round(pos.x)},${Math.round(pos.y)}` } : {}),
      ...(tela ? { 'X-Tela': tela } : {}),
    }),
}

export const arquivoUrl = (slug: string, caminho?: string) => (caminho ? `/projects/${slug}/${caminho}` : '')

/** O canvas recortado a partir de um nó (uma vista: vai para o histórico, pode ser pinada). */
export const rotaVista = (slug: string, id: string) => `#/p/${slug}/f/${id}`

/** O visualizador 3D (public/modelo.html) de um nó "modelo". */
export const urlModelo = (slug: string, no: { arquivo?: string; giro?: number; nome?: string; id: string }) =>
  `/modelo.html?src=${encodeURIComponent(arquivoUrl(slug, no.arquivo))}&giro=${no.giro || 0}&nome=${encodeURIComponent(`${no.id} · ${no.nome || ''}`)}`

export const dinheiro = (v: number) => `$${v.toFixed(2)}`
