# Neo Stitch — guia para agentes

Leia este arquivo inteiro antes de mexer em qualquer coisa. Ele é curto de propósito: o que estiver aqui é regra.

## 1. O que é

O Neo Stitch é um canvas local para criar interfaces em três passos: **imagem → vídeo → HTML vivo**. O usuário vê tudo
no app (http://localhost:8730) como uma árvore de cartões. Cada cartão saiu de outro, e é essa linhagem que o app
desenha. De páginas prontas pode sair um **design system** (seção 6).

- `ferramentas/`: os comandos em Python (rode sempre com `uv run`, na raiz do repositório).
- `app/`: o app (React). Ao iniciar, o servidor o recompila se o código mudou (ex.: depois de um `git pull`).
- `projects/<slug>/`: os dados de cada projeto. **Você nunca edita esses arquivos à mão**: usa os comandos.

Para subir o app: `uv run ferramentas/servidor.py` (porta 8730; outra porta: `… servidor.py 8731`).

## 2. As cinco regras

1. **Tudo passa pelos comandos.** Nenhum arquivo em `projects/<slug>/nodes/` é escrito à mão. Os comandos travam o
   projeto (o app escreve ao mesmo tempo), dão os códigos e mantêm a linhagem. Se algo não aparece no app, é porque
   não passou por um comando.
2. **Tudo o que você gera vira um cartão, com o custo.** Imagem, vídeo, modelo 3D, página, design system: cada um entra no canvas pelo
   seu comando, com `--custo` em US$ (`0` se nada foi pago). O custo aparece na legenda do cartão.
3. **Toda parada para aprovação aparece no app.** Quando você precisa que o usuário olhe e aprove algo no meio do
   trabalho, rode `impl.py aguardar` (seção 5). Só mandar o caminho no chat não basta.
4. **Nunca apague nada.** Nem imagens, nem nós, nem versões. O que não serve é descartado (estado) ou movido para
   `projects/<slug>/lixeira/`.
5. **Quem marca é o usuário.** Ele **pina** o que importa e **descarta** o que não serve (pelo app ou pelo chat); não há mais
   "aprovar". A única marca que você grava é `--estado aprovada` no modelo 3D que escolheu para a página: ela só diz que a
   página sai dele.

Mais três: o conteúdo é em português (PT-BR); as chaves (`OPENROUTER_API_KEY`, `FAL_KEY`) vêm do `.env` daqui ou de `~/.env` (o usuário as define em **Config**, no app) e nunca
são impressas nem commitadas; não mexa no código do app (`app/`, `ferramentas/`) se a tarefa for de conteúdo.

## 3. O modelo

- **Projeto** (`projects/<slug>/`): tem um prefixo (ex.: `JAR`) e uma árvore de nós.
- **Nó**: um cartão. Tem um código (`JAR-042`), dado uma vez e nunca reaproveitado. No app, clicar no código o copia.
- **Pedido**: entre um nó e o que sai dele há sempre um pedido. Ele guarda o que foi pedido, as `entradas` (a 1ª é o
  pai), as `saidas` e o custo.
- **Página**: o HTML vivo não é um nó. É uma pasta `projects/<slug>/impl/<IMAGEM>/vN/` com um `impl.json`, e o app a
  desenha como um cartão ligado ao que ela usa.

| Tipo de nó | O que é | Como nasce |
|---|---|---|
| `brief`, `tela` | o começo do projeto e as telas que ele pede | `neo.py novo`, `neo.py tela` |
| `referencia` | uma imagem colada pelo usuário | pelo app |
| `imagem` | uma tela gerada (uma ideia de interface) | `gerar.py` (de um pedido) |
| `imagem` com `asset: true` | um **asset**: imagem gerada durante uma página para ser usada nela (placa de fundo, personagem limpo, textura, thumbnails sem texto). No app, é a categoria "Assets", separada das telas | `impl.py asset` (só ele) |
| `video` | um vídeo gerado de uma imagem | `gerar_video.py` (de um pedido de vídeo) |
| `modelo` | um modelo 3D gerado de uma imagem | `impl.py asset … .glb` |
| `ds` | um **design system**: catálogo extraído de páginas prontas, em `ds/<código>/`. No app, é a categoria "Design Systems", destacada como a referência | `neo.py ds` |

A cadeia completa, da esquerda para a direita no canvas:

```
tela → pedido → IMAGEM → pedido de vídeo → VÍDEO → pedido de assets → ASSET (personagem limpo) → pedido 3D → MODELO 3D ✓ → PÁGINA vN → evolução vN.1
                                                 └→ pedido de assets → ASSET (placa de fundo) ──────────────────────────────┘
PÁGINA vN → pedido → DESIGN SYSTEM   (as outras páginas do catálogo ligam por uma linha tracejada)
```

## 4. Imagens e vídeos

Normalmente o usuário cria o pedido no app e o envia; a fila avisa o agente. Para fazer pela linha de comando:

```bash
# imagens: um pedido que sai da JAR-042, depois a geração (cada --prompt vira uma imagem)
uv run ferramentas/neo.py pedido jarvisos --entradas JAR-042 --intencao "mais neon" --quantidade 3
uv run ferramentas/gerar.py JAR-0XX --prompt "…" --prompt "…" --prompt "…"

# vídeo: um pedido de vídeo que sai da imagem (o quadro inicial), depois a geração (um vídeo por modelo)
uv run ferramentas/neo.py pedido jarvisos --entradas JAR-095 --midia video --modelos alibaba/wan-3.0 --duracao 6 \
  --intencao "o olho respira, os anéis giram"
uv run ferramentas/gerar_video.py JAR-0XX --prompt-arquivo prompt.txt
```

`gerar.py` e `gerar_video.py` gravam o custo sozinhos. Como escrever bons prompts: skill `neo-stitch`
(`.claude/skills/neo-stitch/SKILL.md`).

## 5. Páginas: um vídeo vira HTML vivo

O passo a passo completo está em [docs/AGENTES.md](docs/AGENTES.md). **Leia antes de começar.** Em resumo, são cinco
comandos, sempre nesta ordem:

```bash
uv run ferramentas/impl.py iniciar JAR-154 --agente "Codex 5.6"     # 1. reserva a pasta JAR-095/v6 (o cartão aparece)
uv run ferramentas/impl.py etapa JAR-095/v6 "componentes" --progresso 0.6 --custo 0.40      # 2. a cada etapa (≤ 10 min)
uv run ferramentas/impl.py asset JAR-095/v6 fundo.png --nome "placa de fundo" --custo 0.02 --usa   # 3. cada arquivo gerado
uv run ferramentas/impl.py aguardar JAR-095/v6 phase1/index.html "o robô 3D no lugar"      # 4. cada parada para aprovação
uv run ferramentas/impl.py pronto JAR-095/v6 --nota "o que a página faz" --custo 1.20     # 5. o fim
```

- **Se você usa uma skill** (ex.: `video2html`), siga o método dela **e** estes comandos. Cada "pare para aprovação" da
  skill é um `impl.py aguardar`.
- `pronto` recusa terminar se faltar o `index.html` ou se alguma página de fase (`phase1/index.html`…) nunca foi
  mostrada com `aguardar`.
- Para alterar uma página que já existe, não mexa nela: `impl.py evoluir JAR-095/v6 --agente "…" --pedido "…"` cria a
  `v6.1`.

## 6. Design systems: páginas prontas viram um catálogo

Um design system é uma pasta com um `design-system.html` (Overview e Components) tirada de uma ou mais páginas. Monte a
pasta fora de `impl/`, sem mexer nas páginas, e registre com um comando só:

```bash
uv run ferramentas/neo.py ds jarvis-conteudo <pasta> --nome "Robô azul" --de JCO-193/v1,JCO-194/v1 --capa capa.png --custo 0
```

O comando copia a pasta para `projects/<slug>/ds/<código>/` e cria o pedido e o cartão, que no app fica na categoria
"Design Systems". O passo a passo está em [docs/AGENTES.md](docs/AGENTES.md), seção 11.

## 7. Onde ler mais

| Para | Leia |
|---|---|
| implementar um vídeo como HTML | [docs/AGENTES.md](docs/AGENTES.md) |
| registrar um design system | [docs/AGENTES.md](docs/AGENTES.md), seção 11 |
| operar o canvas (fila, prompts, geração) | skill `neo-stitch` (`.claude/skills/neo-stitch/SKILL.md`) |
| o contrato de cada tipo de nó | [.claude/skills/neo-stitch/modelo.md](.claude/skills/neo-stitch/modelo.md) |
| usar o app (atalhos, vistas, visualizador) | [docs/USO.md](docs/USO.md) |
| decisões e escopo | [specs.md](specs.md) |
