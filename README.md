<div align="center">

<img src="docs/logo.svg" width="96" alt="Neo Stitch">

# Neo Stitch

**Esboce com imagens. Dê vida com vídeo. Entregue em HTML.**

Um canvas local onde ideias de interface crescem em árvore —<br>
do prompt à imagem, da imagem ao movimento, do movimento ao código.

<br>

![Python](https://img.shields.io/badge/python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)
![só biblioteca padrão](https://img.shields.io/badge/backend-só%20stdlib-111318?style=flat-square)
![React](https://img.shields.io/badge/react-19-61dafb?style=flat-square&logo=react&logoColor=black)
![React Flow](https://img.shields.io/badge/react%20flow-12-ff0072?style=flat-square)
![OpenRouter](https://img.shields.io/badge/openrouter-imagens%20%2B%20vídeo-3d5afe?style=flat-square)
![Claude Code](https://img.shields.io/badge/feito%20com-Claude%20Code-d97757?style=flat-square)

</div>

<br>

<p align="center">
  <img src="docs/demo.gif" alt="O Neo Stitch em uso: a árvore de ideias, o enquadramento de uma família, o visualizador e a página de desenvolvimento com os vídeos de cada modelo" width="100%">
</p>

<p align="center"><sub>A árvore de ideias do JarvisOS → enquadrar uma família com o botão do meio → o visualizador com as irmãs → a página 🔥 com um vídeo por modelo.</sub></p>

<br>

## Por quê

Ferramentas como o Stitch geram telas direto em código, e o código puxa tudo para o genérico. Modelos de imagem fazem o contrário: inventam interfaces que nenhum template entrega. O Neo Stitch aposta nisso. **Primeiro a imagem, depois o movimento, por último o HTML** — e você só gasta código no que já foi aprovado.

Cada ideia vira um nó num canvas infinito. Você pede, o Claude Code gera, você marca as melhores e pede de novo a partir delas. O resultado é uma árvore viva de exploração, com a linhagem de cada tela à vista: de onde veio, o que saiu dela, quanto custou.

## Como funciona

```
 brief ─▶ tela ─▶ pedido ─▶ 🖼 imagens ─▶ pedido ─▶ 🖼 imagens …
                                  │
                                  ▼  (a imagem aprovada ganha 🔥)
                          🎬 pedido de vídeo ─▶ vídeos (um por modelo)
                                  │
                                  ▼
                          </> HTML vivo  (impl/<código>/vN)
```

1. **Você pede no canvas.** Selecione imagens ou referências, tecle `N`, escreva a intenção e envie com `⌘↵`.
2. **O Claude Code atende.** Ele ouve a fila do app (`fila.jsonl`), lê o contexto do pedido — entradas, comentários com pin, o brief — e escreve os prompts.
3. **As imagens penduram na árvore.** Geradas em paralelo no OpenRouter (GPT Image 2 por padrão, com várias referências), com custo e prompt guardados em cada nó.
4. **A aprovada ganha vida.** Um pedido de vídeo (`V`) anima a tela em vários modelos de uma vez, com a interface travada: câmera fixa, texto intacto, só se mexe o que foi pedido.
5. **O vídeo vira HTML.** Com o movimento aprovado, a tela é reconstruída em HTML/CSS de verdade — fontes, caixas, cores e ícones medidos contra a imagem.

## Da imagem ao HTML

O JarvisOS — o painel de um orquestrador de agentes de voz — foi o primeiro projeto a fazer o caminho inteiro.

### JAR-043 · "motivo"

<table>
  <tr>
    <th width="33%">🖼 Imagem</th>
    <th width="33%">🎬 Vídeo</th>
    <th width="33%"></> HTML</th>
  </tr>
  <tr>
    <td><img src="docs/evolucao/jar043-imagem.jpg" alt="JAR-043, a imagem gerada"></td>
    <td><img src="docs/evolucao/jar043-video.gif" alt="JAR-043 animada pelo Hailuo 3"></td>
    <td><img src="docs/evolucao/jar043-html.jpg" alt="JAR-043 recriada em HTML"></td>
  </tr>
  <tr>
    <td><sub>GPT Image 2 reinterpretando uma referência do Pinterest (uma esfera de tinta se desfazendo).</sub></td>
    <td><sub>Hailuo 3, 6 s: a esfera respira, o LED percorre o arco e "Storytelling" é selecionado.</sub></td>
    <td><sub>HTML/CSS em <code>cqw</code> (escala com a janela), textos reais e o fundo reconstruído. Diferença média para o mock: <b>2,8/255</b>.</sub></td>
  </tr>
</table>

### JAR-115 · neurônio

<table>
  <tr>
    <th width="50%">🖼 Imagem</th>
    <th width="50%">🎬 Vídeo (4 s)</th>
  </tr>
  <tr>
    <td><img src="docs/evolucao/jar115-imagem.jpg" alt="JAR-115, o neurônio"></td>
    <td><img src="docs/evolucao/jar115-video.gif" alt="JAR-115 animada pelo Hailuo 3 Max"></td>
  </tr>
  <tr>
    <td><sub>Layout aprovado + referência de um neurônio como núcleo.</sub></td>
    <td><sub>Hailuo 3 Max: o núcleo pulsa e faíscas correm pelos dendritos até os agentes ativos.</sub></td>
  </tr>
</table>

### Um pedido, seis modelos

Cada pedido de vídeo roda em vários modelos ao mesmo tempo, e a página 🔥 da imagem toca todos juntos para comparar. Abaixo, a JAR-095 com o mesmo prompt:

<p align="center"><img src="docs/evolucao/modelos-jar095.gif" alt="A JAR-095 animada por seis modelos de vídeo" width="100%"></p>

Testamos os 25 modelos de image-to-video do OpenRouter em quatro telas. O que importa aqui não é o vídeo mais bonito, e sim o que **não mexe na interface**:

| Modelo | Custo (6 s, 720p) | No nosso teste |
|---|---|---|
| **Hailuo 3** | ~$0,78 | O mais fiel: texto e layout intactos em todas as telas |
| **Hailuo 3 Max** | ~$0,48 | Estável e barato; às vezes troca números da telemetria |
| Seedance 2.5 | ~$1,40 | Sutil e fiel; recusa personagens com direitos autorais |
| Wan 3.0 / 3.0 Prime | ~$0,51 / $0,84 | Bonitos, mas tendem a acender tudo e a trocar rótulos |
| Grok Imagine 1.5 Lite | ~$0,19 | Rápido e barato para rascunho; exagera no movimento |

## Recursos

- **Árvore de ideias** que se arranja sozinha: empilhada, em grade ou em blocos 3×3 / 4×4 / 5×5. Arraste qualquer nó e o galho vai junto.
- **Pedidos como pontos:** o pedido concluído encolhe num ponto sobre a linha (passe o mouse para ver o card), e a árvore fica só com as imagens.
- **Recolher com intenção:** cada galho fecha numa pílula com a contagem; `⌘1`/`⌘2`/`⌘3` mostram uma geração de cada vez; `⌘A` deixa só o caminho até as aprovadas.
- **Visualizador** com comentários em pontos da imagem (ou em segundos do vídeo), "Veio de" / "Saiu daqui" e um filme estilo Finder com as irmãs.
- **Pedidos de vídeo** com vários modelos, duração, resolução e estimativa de custo antes de enviar.
- **🔥 Em desenvolvimento:** imagens que viraram vídeo ou HTML ganham página própria, acessível pela tela inicial e pela barra lateral.
- **Desfazer tudo:** `⌘Z`/`⌘⇧Z` para posições, galhos, marcações, pedidos e itens apagados (nada sai do disco: vai para a lixeira do projeto).
- **Custos sob controle:** custo por imagem, por pedido e por dia, com tetos que pedem confirmação.
- **Local e simples:** um servidor Python sem dependências, um JSON por nó, nada de banco de dados.

## Instalação

**Requisitos:** macOS ou Windows (no Windows as miniaturas e as medidas saem do `ffmpeg`/`ffprobe`, que precisam estar no PATH: `winget install Gyan.FFmpeg`), [uv](https://docs.astral.sh/uv/) com Python 3.11+, Node 20+, [Claude Code](https://claude.com/claude-code), uma chave do [OpenRouter](https://openrouter.ai/) e, para as capas dos vídeos, `ffmpeg`.

```bash
git clone https://github.com/rtadewald/neo-stitch.git
cd neo-stitch

# o app (React + React Flow)
npm --prefix app install
npm --prefix app run build

# a chave do OpenRouter (fica fora do git)
echo 'OPENROUTER_API_KEY=sk-or-...' > .env

# o servidor: API + arquivos + app em http://localhost:8730/
uv run ferramentas/servidor.py
```

Abra o Claude Code na pasta do projeto e diga **"ouça o canvas"**. Ele liga o Monitor da fila e o ponto verde "Claude" acende no topo do app. A partir daí, cada pedido enviado no canvas é atendido na hora.

Para mexer no app com recarga instantânea: `npm --prefix app run dev` (porta 5173, repassa a API para a 8730).

## Usar

| Atalho | O quê |
|---|---|
| `N` | Novo pedido com a seleção (imagens e referências) |
| `V` | Pedido de vídeo a partir da imagem selecionada |
| `F` · `A` · `D` | Favorita · aprova · descarta |
| `⌘A` | Só o caminho até as aprovadas (e as 🔥) |
| `⌘1` `⌘2` `⌘3` | Mostra uma, duas ou três gerações |
| `⌘Z` · `⌘⇧Z` | Desfaz · refaz |
| `⌘V` | Cola uma imagem como referência, embaixo do cursor |
| roda do mouse · arrastar | Zoom · navegar |
| `⌘` + arrastar · `⌘` + clique | Caixa de seleção · põe/tira da seleção |
| botão do meio num nó | Enquadra a família dele (dois cliques no vazio: tudo) |
| duplo clique | Abre o visualizador |

O guia completo está em [docs/USO.md](docs/USO.md).

## Como o Claude entra

O app não chama nenhuma IA sozinho. Ele escreve uma linha na `fila.jsonl` a cada pedido, e o Claude Code, seguindo a skill [`neo-stitch`](.claude/skills/neo-stitch/SKILL.md), faz o resto:

```bash
uv run ferramentas/neo.py ver JAR-042          # o pedido com todo o contexto
uv run ferramentas/gerar.py JAR-042 --json …   # gera as imagens e pendura no canvas
uv run ferramentas/gerar_video.py JAR-122 --prompt-arquivo prompt.txt   # um vídeo por modelo
```

Os mesmos comandos funcionam pelo chat: "gera 3 variações da JAR-042 mais neon" cria o pedido no canvas, com a linhagem.

## Estrutura

```
ferramentas/          Python, só biblioteca padrão (uv run)
  servidor.py         API + arquivos (com Range, para os vídeos) + app compilado
  base.py             caminhos, trava por projeto, nós, códigos, custos
  neo.py              o lado do Claude: fila, contexto, direções, estados, diário
  gerar.py            imagens (OpenRouter /images, em paralelo, várias referências)
  gerar_video.py      vídeos (OpenRouter /videos, assíncrono, vários modelos)
  openrouter.py       cliente HTTP mínimo
app/src/              Vite + React 19 + React Flow 12
  Canvas.tsx          o canvas: árvore, atalhos, seleção, menu, organização
  nodes.tsx           os nós: brief, tela, pedido, imagem, referência, vídeo
  Viewer.tsx          o visualizador com pins e linhagem
  Fogo.tsx            a página 🔥 de cada imagem (canvas imagem → vídeos e sites) e a barra fogo/aprovadas
  layout.ts           a árvore e os modos de arranjo
projects/<slug>/      os dados (um JSON por nó, imagens, vídeos, impl/) — fora do git
.claude/skills/       a skill que ensina o Claude a operar o canvas
```

Decisões e escopo completos em [specs.md](specs.md).

## Próximos passos

- [x] O HTML dentro do app: as versões de `impl/<código>/vN` na página 🔥, lado a lado com a imagem e o vídeo.
- [x] Do vídeo ao HTML animado: a skill `video2html` usa o vídeo aprovado como referência de movimento na reconstrução.
- [ ] Pedir o HTML pelo app (um botão na página 🔥 que vira uma ação da fila).
- [ ] Editar padrões e tetos do projeto pela interface.

<br>

<div align="center">
<sub>Feito por <a href="https://github.com/rtadewald">Rodrigo Tadewald</a> com <a href="https://claude.com/claude-code">Claude Code</a> · imagens e vídeos via <a href="https://openrouter.ai/">OpenRouter</a></sub>
</div>
