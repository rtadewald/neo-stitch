# Neo Stitch — Especificação

> Documento de decisões fechado na sessão de grill (2026-10-22). Fonte de verdade para a implementação.

## 1. O que é

App **local** para explorar interfaces (sites, apps, dashboards, webapps) a partir de **imagens de alto impacto visual** geradas por IA, organizadas como uma **árvore num canvas** (estilo ComfyUI/Magnific Spaces). Imagens aprovadas viram um **HTML vivo** — fiel à imagem e com os componentes animados — que é **exportado** para ser implementado de verdade em outra pasta.

**O Neo Stitch não implementa produto.** Ele termina no pacote HTML/CSS/JS + handoff.

### Problema que resolve
O processo atual (ex.: `20-jarvisOS/prototipos`, 125 imagens) perde informação:
- prompts não são salvos (`.log` só tem caminho, modelo e custo);
- não há linhagem pai → filho (só implícita em nomes de pasta);
- `aprovados/` foi montada à mão, quebrando o vínculo com a origem (arquivos movidos, renomeados, "cópia" do Finder);
- nomes repetidos entre pastas (`a-centro.png` ×12), esquemas de versão inconsistentes.

## 2. Escopo

| Versão | Conteúdo |
|--------|----------|
| **v1** | Canvas de exploração completo + import do JarvisOS. Modelo de dados já prevê implementações. |
| **v2** | Implementações (img-to-html) no canvas: preview, versões, comparação, exportar. |
| **v3+** | Skills de elementos especiais (shaders, 3D) usadas na fase "Vida". |

## 3. Arquitetura

- **Backend:** servidor Python rodado com `uv` (padrão do `19-agent-video-editor`): stdlib `ThreadingHTTPServer`, roteador simples, arquivos estáticos com Range, só em `127.0.0.1`.
- **Frontend:** Vite + React + **React Flow** (`@xyflow/react`).
- **Protocolo app ↔ Claude:** arquivos JSON em disco, escritas atômicas (temp + `os.replace`), polling da UI (~4 s), merge no servidor para não sobrescrever respostas do Claude. Sem MCP/websocket.
- **Arquivo de "trabalhando":** o Claude sinaliza o pedido em execução e a UI mostra loader no nó.
- **Uso:** single-user, local, sem login, sem deploy.
- **Skill do projeto:** `.claude/skills/neo-stitch/SKILL.md` com fluxos sob demanda: novo projeto, rodar pedidos, importar, implementar, exportar.
- **Script de geração próprio:** `ferramentas/gerar.py` (reaproveita a lógica de `~/.agents/skills/openrouter-img/scripts/generate_image.py`, que **não é alterada**):
  - grava no nó do pedido: prompt final, refs, modelo, resolução, aspect ratio, custo, tempo;
  - gera **N imagens em paralelo**;
  - aceita **várias referências** (`input_references` da API já é uma lista; a skill atual só envia uma — validar suporte multi-ref no gpt-image-2).
- `OPENROUTER_API_KEY` vem do `.env` (nunca commitar).

## 4. Estrutura de pastas (proposta)

```
21-neo-stitch/
  specs.md
  CLAUDE.md / AGENTS.md
  .claude/skills/neo-stitch/
  ferramentas/          # servidor.py, gerar.py, importar_jarvis.py, codigo.py…
  app/                  # frontend Vite + React + React Flow
  projects/
    <slug>/
      projeto.json      # config, padrões de geração, tetos de custo, prefixo do código
      brief.md
      diario.md
      nodes/            # um JSON por nó (evita conflito de escrita)
      fila/             # pedidos pendentes / trabalhando
      images/           # <código>.png
      refs/             # referências externas
      impl/<código>/vN/ # (v2) saída do img-to-html: index.html + assets/
```

## 5. Modelo do canvas

### Tipos de nó
| Nó | Conteúdo |
|----|----------|
| **Brief** | Raiz do projeto. Explicação do projeto + `brief.md` mantido pelo Claude. Define os padrões do projeto. |
| **Tela** | Filho do Brief. Um ramo por tela (home, chat, config…). |
| **Pedido** | Entradas (imagens pai, refs, intenção em texto), quantidade, modelo, formato, checkbox **literal**, **prompt final**, custo, status (rascunho / enviado / trabalhando / concluído / erro). |
| **Imagem** | Resultado de um pedido. Código curto estável (ex.: `JAR-042`), estado, comentários. |
| **Referência** | Imagem externa arrastada/colada (Pinterest, prints…). |
| **Implementação** (v2) | Filha de uma imagem ✅. Ver §8. |

- **Linhagem automática:** pai → Pedido → filhos. O Pedido fica sempre visível entre pai e filhos (guarda o "porquê").
- **Recombinação:** selecionar N imagens/refs → "Novo pedido" (nasce ligado a todas).
- **Consistência entre telas:** imagem aprovada de uma tela pode ser referência de estilo em pedidos de outra.
- **Fios manuais estilo Comfy:** opcionais.
- **Códigos citáveis:** todo nó tem código curto (`<PREFIXO>-NNN`) para usar no chat.

### Layout
- Filhos nascem automaticamente à direita do pedido (árvore esquerda → direita).
- Posições arrastáveis e persistidas; botão "reorganizar" refaz o auto-layout de um ramo.

### Estados da imagem
`neutra` · ⭐ `favorita` (explorar mais) · ✅ `aprovada` (candidata a HTML) · `descartada` (recolhida/esmaecida, **nunca apagada**).

### Comentários
- Por nó, com **pin opcional** numa coordenada da imagem (ou do HTML, na v2).
- Ao criar um pedido a partir de imagem comentada, os comentários entram como contexto.
- Na implementação, viram a lista de ajustes da próxima versão.

## 6. Fluxo com o Claude

1. **Novo projeto:** usuário explica no chat ou no formulário do Brief (refs opcionais). Claude cria o projeto, o `brief.md` e os padrões.
2. **Exploração inicial divergente:** Claude propõe ~6 **direções de estilo** bem diferentes, cada uma com nome e tese, em texto no Brief → usuário corta/ajusta → só então gera.
3. **Pedidos:** usuário monta no canvas e clica **Enviar**.
   - **Modo automático (padrão):** Claude observa a fila com Monitor enquanto a sessão do canvas está aberta, acorda, reescreve a intenção em prompt completo (ou usa literal), gera e pendura os resultados.
   - **Fallback manual:** "roda os pedidos" no chat.
4. **Intenção vs. prompt:** por padrão o Claude reescreve; o nó mostra ambos. Checkbox **literal** desliga a reescrita.
5. **Padrões de geração:** por projeto (tipo site/app/dashboard/webapp → aspect ratio e modelo sugeridos), sobrescrevíveis por pedido. Quantidade padrão: **3**. Modelo padrão atual: `openai/gpt-image-2`, 1K.
6. **Limite de gasto:** pedidos de até 6 imagens rodam direto; acima disso, ou se o projeto passar do teto diário (ex.: $20), o Claude pergunta antes. Painel mostra custo total e do dia (~$0,13–0,15/img no gpt-image-2).
7. **Sem chat no app.** Conversa fica no Claude Code; o app é o canal assíncrono (pedidos, comentários, aprovações).
8. **Diário:** `diario.md` por projeto, mantido pelo Claude, visível num painel — registra decisões ("JAR-042 aprovada porque…", "abordagem shader venceu porque…").

## 7. Import do JarvisOS (v1)

Origem: `/Users/rtadewald/Projetos Locais/Tools/20-jarvisOS/prototipos` (não alterar a origem — copiar).
- Projeto "JarvisOS"; cada pasta vira um **Pedido legado** marcado "sem prompt original" (nunca inventar prompts).
- `referencia*` / `ref-*` viram nós de **Referência**; `hint.txt` vira a intenção do pedido legado.
- Linhagem reconstruída por aproximação a partir dos nomes (`idle` → `idle-v2-stark` → `idle-v3-eve`; `neuronio` / `neuronio-02`; `pinterest/NN-pin-*`).
- `_descartados/` → estado `descartada`; `aprovados/` → estado ✅ na imagem de origem quando identificável (dedup por hash); ambíguos ficam sinalizados.
- `contact-sheet` / `.log` / `.DS_Store` não viram nós (custo do `.log` pode ir para o pedido).

## 8. Implementações (v2 — modelo já na v1)

- Nó **Implementação** filho de imagem ✅; uma imagem pode ter **várias abordagens** (ex.: "img-to-html puro" vs. "fundo em shader").
- **Versões imutáveis** `v1, v2…` em `projects/<slug>/impl/<código>/vN/` (formato do img-to-html: `index.html`, `assets/`, `reference.*`, `wireframe.txt`).
- **Duas fases na mesma implementação:**
  1. **Fidelidade** — skill `img-to-html` (5 etapas com aprovação).
  2. **Vida** — animações com a skill `animate` (e futuramente shaders/3D). O que for bom volta para o catálogo do `animate`.
  O nó mostra a fase atual.
- **Uma sessão do Claude Code por implementação**, aberta pela sessão do canvas com um brief (imagem, abordagem, pasta de saída). O nó guarda o link da sessão.
- **Visualização:** preview ao vivo (iframe) no nó, abrir em aba cheia, modo **comparar** (imagem original sobreposta ao HTML com slider de opacidade).

## 9. Exportar (v2)

Comando/botão **Exportar** copia a versão aprovada (fase Vida) para um destino escolhido, como pacote autocontido:
- `index.html` + `assets/`
- imagem de origem
- `HANDOFF.md`: tokens de design (cores, fontes, espaçamentos), lista de componentes animados e origem de cada um, ressalvas.

Esse pacote é o ponto de partida para o Claude da outra pasta implementar front/back.

## 10. Fatos do ambiente (levantados em 2026-10-22)

- Skills em `~/.agents/skills/` (`~/.claude/skills` é symlink):
  - `openrouter-img` — `POST https://openrouter.ai/api/v1/images`, 1 imagem por chamada (`n: 1`), 1 `--input-image`, salva só o PNG. Aliases: `gpt2` = `openai/gpt-image-2`, `pro` = `google/gemini-3-pro-image`, `flash` = `google/gemini-3.1-flash-image`, além de flux.2, seedream, qwen-image-3-pro, grok-imagine.
  - `to-img` — wrapper (gpt2, 1K, 16:9, 3 variações em `mocks/`), sem metadados.
  - `img-to-html` — imagem → pasta `design-systems/<slug>/` (HTML/CSS puro, sem build), 5 etapas com aprovação, verificação manual por screenshot.
  - Relacionadas: `plan-screen`, `to-wireframe`, `nano-banana-pro`, `animate`.
- Referência de padrão: `19-agent-video-editor` (`ferramentas/servidor.py`, `ferramentas/base.py` — `gravar_json`, `para_lixeira`; `app/comum.js`; códigos curtos em `biblioteca/codigos.json` + `ferramentas/codigo.py`).

## 11. Pontos a validar na implementação

- Suporte real a múltiplas `input_references` no `openai/gpt-image-2` via OpenRouter (se não houver: colagem das refs numa imagem única ou modelo alternativo para pedidos multi-ref).
- Custo/latência do modo automático (Monitor) com a sessão aberta por longos períodos.
- Desempenho do React Flow com centenas de nós de imagem (thumbnails vs. original).

## 12. Estado da implementação (2026-10-23)

**v1 entregue.** Rodar: `uv run ferramentas/servidor.py` → http://localhost:8730/ (detalhes no `README.md`; operação do Claude na skill `neo-stitch`).

- Backend Python stdlib: `servidor.py` (API + arquivos + app), `neo.py` (lado do Claude), `gerar.py` (OpenRouter, paralelo, multi-ref), `ouvir.sh` (Monitor + batimento do ponto "Claude" no app), `importar_jarvis.py`.
- Frontend Vite + React + React Flow, tema claro: Home (projetos + novo projeto com tipo e descrição), canvas com nós Brief/Tela/Pedido/Imagem/Referência, seleção → pedido (`N`), estados `F`/`A`/`D`, ligar referência a pedido arrastando a alça, colar/arrastar imagens, visualizador com pins, painel Brief/Diário, custo total/dia, esconder descartadas.
- **Árvore de ideias (ajuste de 2026-10-23):** cada imagem é um nó; um pedido nasce da imagem de onde saiu e os filhos saem dele. O layout é automático (esquerda → direita, irmãos empilhados, pai centrado), e cada nó recolhe ou expande o próprio galho (`recolhido`, persistido). Só referências soltas são arrastáveis.
- Validado de ponta a ponta: novo projeto → Claude propõe direções → liga/desliga → gera → seleciona → novo pedido → Claude gera derivado.

**Pontos da §11 resolvidos:**
- Multi-referência no `openai/gpt-image-2` via OpenRouter **funciona** (testado com 2 refs; ambas respeitadas). Custo medido em 1K: ~$0,055/imagem; `flash` ~$0,067 nesta configuração.
- Desempenho: o JarvisOS (119 nós, 85 imagens) abre e navega bem com thumbs JPEG de 640px e `onlyRenderVisibleElements`.

**Import do JarvisOS:** os prompts originais das 85 imagens foram **recuperados da transcrição** da sessão que as gerou (`ferramentas/dados/jarvis_prompts.json`) — a §7 previa pedidos "sem prompt", mas não foi preciso. Linhagem real: idle → stark v2; EVE; 11 pins do Pinterest; neurônio (escuro/claro) a partir dos layouts aprovados. 10 aprovadas e 8 descartadas casadas por conteúdo.

**Pedido de vídeo (2026-10-23):** o vídeo é referência de movimento de uma imagem, gerado antes do img-to-html. Pedido com `midia: "video"`, `modelos` (um vídeo por modelo), `duracao`, `resolucao` (padrão Wan 3.0, 6 s, 720p; teto $2 por pedido; o app oferece 5 modelos: Grok 1.5 Lite, Wan 3.0, Wan 3.0 Prime, Hailuo 3, Seedance 2.5). A fila manda `acao: "video"`; o Claude escreve um prompt com travas (câmera fixa, texto intacto, só os elementos nomeados se mexem) e roda `gerar_video.py` (API assíncrona de vídeo da OpenRouter, sem áudio). Os nós `video` penduram no pedido; a imagem de origem mostra o selo `▶ N`; o visualizador toca o vídeo com pins que guardam o segundo. Catálogo, ranking público e veredito do teste dos 25 modelos em `ferramentas/dados/modelos_video.json`; o teste completo (JAR-043 "idle em uso") é o pedido JAR-122.

**Fogo (2026-10-23, substituído em 2026-10-26):** a imagem que avançava ganhava selo de fogo, página própria e entrada na barra. Saiu: no lugar dele, as **vistas** (abaixo). O servidor ainda calcula `base.avancos` (vídeos e versões de `impl/` por imagem), que o app usa para montar os nós de HTML.

**Vistas (2026-10-26):** qualquer nó abre o canvas recortado a partir dele (`#/p/<slug>/f/<código>`; o mesmo Canvas, não uma página à parte). A barra lateral tem os pinados (em cima) e o histórico das 10 últimas vistas; `projeto.json` guarda `pinados` e `historico`, mudados por `POST /api/projetos/<slug>/vistas {acao: abrir|pinar|despinar, id}`. Cada vista fica num lugar só. A Home mostra os pinados do projeto selecionado; o ⌘A considera só as aprovadas.

**video2html (2026-10-24):** skill global `~/.agents/skills/video2html` (imagem aprovada + vídeo → HTML vivo e interativo). Lê o
movimento (mapa de pixels + Gemini 3.8 Flash), escreve o mapa de vida (`vida.md`), reconstrói em camadas (img-to-html) e anima em
código (CSS/SVG → Canvas → Three.js, GSAP) — vídeo nunca vira asset. Protótipo: `impl/JAR-095/v1` (do vídeo JAR-154); validação:
`impl/JAR-115/v1` (do JAR-170). As versões de `impl/` aparecem como nós no canvas, rodando.

**Fica para depois:** UI para editar padrões/tetos do projeto (só via API/`projeto.json`), v2 (implementações).
