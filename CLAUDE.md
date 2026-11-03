# Neo Stitch

Canvas local para explorar interfaces: imagem → vídeo → HTML vivo. **Antes de qualquer trabalho no canvas, leia o
[AGENTS.md](AGENTS.md)** (as regras e os comandos, iguais para todo agente) e, para uma página HTML, o
[docs/AGENTES.md](docs/AGENTES.md). Como operar o canvas (fila, prompts, geração): skill `neo-stitch`
(`.claude/skills/neo-stitch/SKILL.md`). Decisões e escopo: [specs.md](specs.md).

## Estrutura

- `ferramentas/` — Python só com biblioteca padrão, rodado com `uv run`:
  `servidor.py` (API + arquivos + app compilado, porta 8730) · `neo.py` (o lado do Claude: fila, contexto, direções, estados, diário) ·
  `gerar.py` (OpenRouter /images, N em paralelo, várias referências) · `gerar_video.py` (OpenRouter /videos, um vídeo por
  modelo) · `openrouter.py` (cliente HTTP e a chave) · `pagina_videos.py` (página de comparação avulsa) · `ouvir.sh` (o Monitor
  da fila) · `importar_jarvis.py` (import do 20-jarvisOS) · `impl.py` (implementações vídeo → HTML por qualquer agente: reservar a vN,
  reportar etapas, registrar assets e modelos 3D, parar para aprovação com `aguardar`, terminar; spec em `docs/AGENTES.md`) · `base.py` (caminhos, trava, nós,
  códigos, custos, avanços, vistas).
- `app/` — Vite + React + React Flow (`@xyflow/react`). Dev: `npm run dev` (porta 5173, repassa /api e /projects para 8730).
  Produção: `npm run build` → `app/dist`, servido pelo `servidor.py` (que recompila ao iniciar se `app/src` for mais novo).
- `projects/<slug>/` — os dados (um JSON por nó, imagens, vídeos, modelos 3D em models/, thumbs, refs, impl/, brief.md, diario.md, lixeira/). Não versionar.
- `docs/` — o que o README mostra (demo, evolução imagem → vídeo → HTML) e o guia de uso (`docs/USO.md`).
- `fila.jsonl` — fila append-only que o app escreve e o Claude ouve (`tail -F`).

## Regras

- Nunca apague imagens nem nós com linhagem: descarte (estado) ou mova para `lixeira/`.
- Toda escrita em nó passa por `base.travado(slug)` + `gravar_json` (o app e os scripts escrevem ao mesmo tempo).
- O app é tema claro e minimalista: ícones com `title`, sem texto onde um componente se explica.
- A chave `OPENROUTER_API_KEY` vem de `~/.env` (ou `.env` aqui) — nunca imprima nem commite.
