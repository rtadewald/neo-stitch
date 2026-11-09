import { ExternalLink, KeyRound, X } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { api, type Chave } from './api'

const ORIGEM: Record<string, string> = {
  ambiente: 'definida na variável de ambiente, que tem prioridade',
  '.env': 'salva no .env deste repositório',
  '~/.env': 'definida em ~/.env',
}

/** As chaves de API. O servidor nunca devolve o valor salvo: aqui só se vê se a chave existe e de onde vem. */
export function Config({ fechar }: { fechar: () => void }) {
  const [chaves, setChaves] = useState<Chave[]>([])
  const [valores, setValores] = useState<Record<string, string>>({})
  const [erro, setErro] = useState<string | null>(null)
  const carregar = useCallback(() => api.config().then((r) => setChaves(r.chaves)).catch((e) => setErro(e.message)), [])
  useEffect(() => { carregar() }, [carregar])
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => { if (e.key === 'Escape') fechar() }
    window.addEventListener('keydown', tecla)
    return () => window.removeEventListener('keydown', tecla)
  }, [fechar])
  const gravar = async (nome: string, valor: string) => {
    setErro(null)
    try {
      await api.mudarChave(nome, valor)
      setValores((v) => ({ ...v, [nome]: '' }))
      await carregar()
    } catch (e) { setErro((e as Error).message) }
  }

  return (
    <div className="modal-fundo" onClick={fechar}>
      <div className="modal config" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="ico fechar" title="Fechar (Esc)" onClick={fechar}><X size={18} /></button>
        <header><KeyRound size={18} /><h2>Chaves de API</h2></header>
        {chaves.map((c) => (
          <form key={c.nome} className="chave" onSubmit={(e) => { e.preventDefault(); if (valores[c.nome]?.trim()) gravar(c.nome, valores[c.nome]) }}>
            <div className="chave-topo">
              <b>{c.rotulo}</b>
              <a href={c.link} target="_blank" rel="noreferrer" title="Pegar uma chave"><ExternalLink size={13} /></a>
              <span className={`chave-estado ${c.origem ? 'ok' : ''}`}>{c.origem ? 'definida' : 'não definida'}</span>
            </div>
            <p className="mudo">{c.para}{c.origem ? ` · ${ORIGEM[c.origem]}` : ''}</p>
            <div className="chave-linha">
              <input type="password" autoComplete="off" spellCheck={false} placeholder={c.origem ? 'Nova chave (substitui a atual)' : c.nome} aria-label={c.rotulo}
                value={valores[c.nome] || ''} onChange={(e) => setValores((v) => ({ ...v, [c.nome]: e.target.value }))} />
              <button type="submit" className="primario" disabled={!valores[c.nome]?.trim()}>Salvar</button>
              {c.origem === '.env' && <button type="button" className="secundario" onClick={() => gravar(c.nome, '')}>Remover</button>}
            </div>
          </form>
        ))}
        {erro && <p className="chave-erro">{erro}</p>}
        <p className="mudo chave-nota">As chaves ficam no arquivo <code>.env</code> deste repositório, fora do git. O app nunca mostra o valor salvo.</p>
      </div>
    </div>
  )
}
