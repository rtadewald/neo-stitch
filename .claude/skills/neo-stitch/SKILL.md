---
name: neo-stitch
description: Opera o canvas do Neo Stitch — ouve a fila do app, propõe direções de estilo, escreve os prompts e gera as imagens dos pedidos, responde comentários e mantém o diário. Use quando o usuário falar do Neo Stitch, do canvas, citar um código de nó (ex. JAR-042), pedir variações de uma imagem, ou disser "ouça o canvas" / "roda os pedidos".
---

# Neo Stitch

O app (canvas em `app/`, servidor em `ferramentas/servidor.py`) é a mesa de exploração visual; **você é quem gera**.
O app só grava pedidos no disco e põe uma linha na `fila.jsonl`; você ouve a fila, escreve os prompts e roda o gerador.
Especificação: `specs.md`. Contrato dos nós: [modelo.md](modelo.md).

## 1. Ligar (início de toda sessão de canvas)

1. Servidores. Se não estiverem no ar:
   - pelo painel do app: `preview_start` com `api` (porta 8730) e `app` (Vite, porta 5173), definidos em `.claude/launch.json`;
   - ou manualmente: `uv run ferramentas/servidor.py`, que também serve o app compilado (`app/dist`) em http://localhost:8730/.
2. Ouvir a fila com o **Monitor** (o ponto verde "Claude" no topo do app só acende com ele ligado):
   `Monitor(command: "<raiz>/ferramentas/ouvir.sh", timeout_ms: 1800000, description: "Fila do Neo Stitch")`.
   Ele expira em 30 min: re-arme a cada aviso de expiração enquanto o usuário estiver trabalhando no canvas.
3. Rode `uv run ferramentas/neo.py pendentes`, porque algo pode ter sido enviado com você fora.

## 2. Cada evento da fila

Cada evento é uma linha `{"projeto", "id", "acao"}`. Antes de qualquer coisa, rode `uv run ferramentas/neo.py ver <id>` para ler todo o contexto: entradas com arquivo, o prompt que gerou cada uma, os comentários com pin e o brief. Se precisar ver as imagens de entrada, abra-as com Read.

### acao = "direcoes" (nó Brief)
1. `neo.py pegar <id>`.
2. Leia o brief e proponha **4 a 6 direções de estilo bem diferentes entre si**. Elas precisam variar paleta, tipografia, materiais e composição, não só cor. Cada direção tem um nome curto (2–3 palavras) e uma tese de 1 linha.
3. `neo.py direcoes <id> --json '[{"nome": "…", "tese": "…"}, …]'`.
   O usuário liga e desliga as direções no canvas e aperta "gerar", e isso vira um pedido com `variacoes`.

### acao = "gerar" (nó Pedido)
1. `neo.py pegar <id>`, que acende o loader no canvas.
2. Escreva os prompts:
   - **`literal: true`** → use a `intencao` exatamente como está, um prompt repetido `quantidade` vezes.
   - **Com `variacoes`** (exploração de direções) → um prompt por variação, desenvolvendo a `tese` de cada uma.
   - **Caso geral** → reescreva a intenção como `quantidade` prompts completos, variando um eixo de cada vez (composição, densidade, acento). Não produza N cópias quase iguais.
   - **Com entradas** → todas as imagens vão como referência, na ordem das `entradas`. Diga no prompt o papel de cada uma ("IMAGE 1 is the approved layout: keep…", "IMAGE 2 is the style reference: copy its palette…"). Comentários com pin são instruções localizadas: converta (x, y) em região ("canto superior esquerdo", "painel da direita") e aplique.
3. Rode o gerador, que cria os placeholders, gera em paralelo e pendura tudo no canvas:
   `uv run ferramentas/gerar.py <id> --json '[{"nome": "…", "prompt": "…"}, …]'`
   - **Saída 3** = bateu num teto de custo (mais de 6 imagens no pedido ou acima do teto diário). Pergunte ao usuário no chat e rode de novo com `--confirmado` só depois do sim.
   - **Falha da API** → as imagens ficam com `erro` e o pedido também. Tente uma vez de novo; persistindo, devolva com `neo.py erro <id> "motivo"`.
4. Se algo foi decidido (direção escolhida, motivo de um descarte), registre: `neo.py diario <slug> "…"`.
5. Não narre cada passo no chat. Uma linha basta ("JAR-120: 3 variações penduradas, $0.41").

### acao = "video" (nó Pedido com `midia: "video"`)
O vídeo é **referência de movimento** de uma imagem: mostra como a tela "vive" (o que respira, acende, é selecionado). Não é a implementação. A primeira entrada é o quadro inicial; o pedido traz `modelos` (um vídeo por modelo), `duracao` (s) e `resolucao`.
1. `neo.py pegar <id>`.
2. Escreva **um** prompt em inglês, a partir da `intencao` (ou ela literal, se `literal: true`). Comentários com pin na imagem dizem o que deve se mexer e onde. Regras que seguram a UI no lugar:
   - Abra com "Animate this exact UI screenshot of <app>…".
   - "Locked static camera, no zoom or pan." "All text, labels, numbers, panels and icons stay perfectly sharp and unchanged; never morph or rewrite text."
   - Nomeie **cada** elemento que se mexe e como (respira, pisca, LED percorre o arco, barra oscila). O que não foi nomeado fica parado.
   - Termine com "Calm pacing, no new elements, no scene change."
   - No máximo 1000 caracteres (limite do Runway). Exemplo: `projects/jarvisos/videos/JAR-043-idle/prompt-curto.txt`.
3. Salve o prompt num arquivo do scratchpad e rode: `uv run ferramentas/gerar_video.py <id> --prompt-arquivo <txt>`. Cria um nó de vídeo por modelo (com placeholder), gera em paralelo (1–5 min cada) e baixa em `videos/<COD>.mp4` com capa em `thumbs/`. Rode em segundo plano.
   - **Saída 3** = estimativa acima de $2 no pedido ou do teto diário. Pergunte no chat e rode com `--confirmado` só depois do sim.
4. Modelos: o app só oferece cinco (`VIDEO_NO_APP` em `base.py`): Grok Imagine 1.5 Lite (rápido e barato), **Wan 3.0 (padrão)**, Wan 3.0 Prime, Hailuo 3 e Seedance 2.5 (poderoso e caro). Os outros do catálogo (`ferramentas/dados/modelos_video.json`, com ranking e veredito do teste) só pelo modo pasta do `gerar_video.py`.

## 3. Pedidos feitos pelo chat (fallback)

"Gera 3 variações da JAR-042 mais neon":
`neo.py pedido <slug> --entradas JAR-042 --intencao "mais neon" --quantidade 3` → depois o mesmo fluxo de "gerar".
O pedido nasce no canvas e mantém a linhagem. Projeto novo pelo chat: `neo.py novo "Nome" --tipo app --descricao "…"`.

## 4. Como escrever prompts de UI

- Abra sempre com o formato: "High-fidelity <16:9 desktop | 9:16 mobile> app UI screen, full screen, no browser chrome, no device frame".
- Conteúdo concreto do brief: rótulos reais em PT-BR, números plausíveis, os componentes que a tela precisa mostrar. Peça "very little text" quando o brief pedir limpeza.
- Estilo em termos visuais verificáveis: paleta, tipografia (família e peso), materiais, luz, densidade e grade. Evite adjetivos vagos ("moderno", "bonito").
- Ao iterar sobre uma imagem, diga **o que manter** e depois **o que mudar**. Mudanças em demasia viram outra direção.
- Modelo padrão: `openai/gpt-image-2` (aceita várias referências, ~$0,06–0,14 por imagem). `google/gemini-3.1-flash-image` (`flash`) serve para testes baratos.

## 5. Outras ações

- Marcar: `neo.py estado JAR-042 JAR-051 aprovada|favorita|descartada|neutra`. Use quando o usuário aprovar pelo chat.
- Responder um comentário: `neo.py comentar JAR-042 "…" [--pin x,y]`. Aparece como pin escuro (do Claude) no visualizador.
- Ver o projeto inteiro: `neo.py ver <slug>`, uma árvore compacta com estados e comentários.
- Brief: `neo.py brief <slug>` lê; `--arquivo novo.md` troca.

## 6. Implementações (HTML)

Imagem → HTML estático: skill `img-to-html`. Imagem + vídeo aprovado → HTML vivo e interativo: skill `video2html`
(`.claude/skills/video2html/SKILL.md`, `/video2html AZE-014`): leia antes de implementar qualquer vídeo, ela tem a régua
(estático ≤ 5/255, energia por região, checar.py) que a versão precisa passar. As duas gravam em `projects/<slug>/impl/<código da imagem>/vN/`, e a página 🔥 da imagem mostra as versões.

Outros agentes (Codex, OpenCode…) também implementam vídeos: a spec é `docs/AGENTES.md`. Toda versão, inclusive as do Claude, é
reservada e reportada com `uv run ferramentas/impl.py iniciar <VÍDEO> --agente "Claude Opus 5.5"` · `etapa <IMG/vN> "…" --progresso 0.x`
· `pronto <IMG/vN>`. O `impl.json` que isso escreve é o que o app mostra (agente, etapa, progresso, "parado?").
**Imagens e modelos 3D gerados no trabalho são cartões:** `impl.py asset <IMG/vN> <arquivo.png>` (sai do vídeo) e
`impl.py asset <IMG/vN> <modelo.glb> --de <imagem> --capa <render.png>` (sai da imagem). Visão geral da linhagem: `AGENTS.md`.
**Alteração pedida numa versão existente nunca a edita:** `impl.py evoluir <IMG/vN> --agente "…" --pedido "…"` cria a `vN.M`
(v1 → v1.1 → v1.2), e o usuário aprova no cartão.

### Notas antigas (spec v2)

As implementações (imagem ✅ → HTML vivo com `img-to-html`, depois a fase "Vida" com `animate`) estão especificadas em `specs.md` §8–9. Quando o usuário pedir, siga a spec:
- abra uma sessão própria por implementação;
- salve em `projects/<slug>/impl/<código>/vN/`;
- registre no diário.
