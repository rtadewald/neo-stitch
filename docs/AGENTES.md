# Vídeo → HTML: o guia para qualquer agente

Este guia serve para qualquer agente de código (Claude Code, Codex, OpenCode, Gemini CLI…) transformar um vídeo do Neo
Stitch numa **página HTML viva e interativa**. Ele também garante que o usuário acompanhe no app quem está
trabalhando, em que etapa e quanto já custou.

Antes deste guia, leia o [AGENTS.md](../AGENTS.md) da raiz (as regras do repositório).

**Como funciona:** cada página é uma pasta `projects/<projeto>/impl/<IMAGEM>/vN/` com uma ficha, o `impl.json`. O
comando `ferramentas/impl.py` escreve essa ficha e registra no canvas tudo o que você gerar. O app lê a ficha e atualiza
o cartão da página sozinho. Vários agentes podem trabalhar no mesmo vídeo ao mesmo tempo: cada um ganha a sua versão
(`v4`, `v5`…).

## Os cinco comandos

Rode na raiz do repositório. `<V>` é a versão que o passo 1 devolve (ex.: `JAR-043/v4`).

| Quando | Comando |
|---|---|
| 1. no começo | `uv run ferramentas/impl.py iniciar <VÍDEO> --agente "<seu nome>"` |
| 2. a cada etapa, e no máximo a cada 10 min | `uv run ferramentas/impl.py etapa <V> "o que está fazendo" --progresso 0.4 --custo <total>` |
| 3. a cada imagem ou modelo 3D gerado | `uv run ferramentas/impl.py asset <V> <arquivo> --nome "…" --custo <US$> …` |
| 4. a cada parada para aprovação | `uv run ferramentas/impl.py aguardar <V> <página.html> "o que aprovar"` |
| 5. no fim | `uv run ferramentas/impl.py pronto <V> --nota "o que a página faz" --custo <total>` |

Se der errado: `impl.py erro <V> "motivo"` ou `impl.py abandonar <V> --nota "…"`. Para ver quem trabalha em quê:
`impl.py ver`.

## 1. Comece

```bash
uv run ferramentas/impl.py iniciar JAR-142 --agente "Codex 5.6"
```

`JAR-142` é o código do vídeo (o usuário o copia do app). O comando reserva a próxima versão da imagem de onde o vídeo
saiu (ex.: `JAR-043/v4`) e prepara a pasta:

- `reference.png`: a imagem. **É o conteúdo**: textos, layout, cores, componentes.
- `analise/video-ref.mp4`: o vídeo. **É o movimento**: o que respira, acende, gira.
- `impl.json`: a ficha, já como `trabalhando`. O cartão aparece no app na hora, com o seu nome.

**O nome do agente** é curto (até 24 caracteres): a ferramenta ou o modelo, com a versão. Ex.: `Codex 5.6`,
`Claude Opus 5.5`, `OpenCode Kimi K3`. Use sempre o mesmo nome.

## 2. Trabalhe só dentro da sua pasta

- O entregável é `index.html` + `assets/` (CSS, JS, imagens), com caminhos relativos. A página abre em
  `http://localhost:8730/projects/<projeto>/impl/<IMAGEM>/vN/index.html`.
- Bibliotecas por CDN, com versão fixa (ex.: `three@0.170.0`, `gsap@3.13.0`).
- Escreva um `README.md` na pasta: o que vive, como foi feito, o que ficou de fora e por quê.
- Não mexa em outras versões, em `nodes/` nem no código do app. Não apague nada.

## 3. Reporte o andamento

```bash
uv run ferramentas/impl.py etapa JAR-043/v4 "componentes: cards e gráficos" --progresso 0.6 --custo 0.42
uv run ferramentas/impl.py vivo JAR-043/v4      # só o sinal de vida, sem mudar a etapa
```

- Atualize a cada etapa e **no máximo a cada 10 minutos**. Sem notícia há 15 minutos, o cartão mostra "parado?".
- `--custo` é o **total** gasto em APIs nesta versão até agora (imagens, 3D, descrição de vídeo), não o incremento.
- O texto da etapa é livre, curto, em português. Um guia de progresso: lendo o material 0.1 · estrutura e textos 0.3 ·
  assets 0.45 · partes vivas 0.65 · interações 0.85 · verificação 0.95.

## 4. Registre tudo o que gerar

Toda imagem e todo modelo 3D gerado no trabalho vira um cartão no canvas. Registre **assim que o arquivo existir**,
mesmo os que você não vai usar.

**Uma imagem** (placa de fundo sem os elementos vivos, personagem isolado para o 3D, textura). Ela sai do vídeo:

```bash
uv run ferramentas/impl.py asset JAR-043/v4 assets/fundo.png --nome "placa de fundo" \
  --nota "o fundo sem os elementos vivos" --custo 0.02 --usa
```

`--usa` diz que a página usa essa imagem: ela entra nas `entradas` da página, e o app as liga com uma linha.

**Um modelo 3D**. Ele sai da imagem que o gerou (`--de`). Registre **todos** os modelos gerados, cada um com um render
no ângulo do quadro como capa, e marque o escolhido como aprovado:

```bash
uv run ferramentas/impl.py asset JAR-043/v4 phase1/models/tripo.glb --nome "Tripo H3.1" --de JAR-181 \
  --capa phase1/models/tripo-yaw.png --giro -90 --custo 0.40 --estado aprovada
```

- `--giro`: graus para o modelo ficar de frente no visualizador do app, quando ele vem virado.
- O modelo aprovado vira a 1ª das `entradas`: no app, a página sai dele.

## 5. Pare para aprovação dentro do app

Quando o usuário precisa ver e aprovar algo no meio do trabalho (a Fase 1 do `video2html`, uma escolha entre opções),
faça uma página para isso e rode:

```bash
uv run ferramentas/impl.py aguardar JAR-043/v4 phase1/index.html "o robô 3D no lugar: olha o cursor e fala"
```

- O cartão passa a rodar essa página, com o selo **aguardando você**. Dois cliques a abrem.
- Depois, **pare**: mostre no chat o caminho e um print, e espere um "ok" explícito. Se o usuário pedir ajustes, faça,
  rode `aguardar` de novo e espere de novo.
- Ao voltar a trabalhar, o próximo `etapa` tira o cartão do modo "aguardando".
- **Toda pasta de fase** (`phase1/`, `phase2/`… com um `index.html`) tem de passar por `aguardar`: o `pronto` recusa
  terminar se alguma nunca foi mostrada.

## 6. Termine

```bash
uv run ferramentas/impl.py pronto JAR-043/v4 --nota "robô em Three.js, arco em SVG, o chat responde" --custo 1.20
```

`pronto` exige o `index.html`, a `--nota` e o `--custo` total. Depois dele, o cartão roda a página, e o usuário a
aprova ou descarta ali mesmo.

## 7. Alterações pedidas: evoluções (v1.1, v1.2…)

Quando pedirem uma mudança numa versão que já existe, **não mexa nela**. Crie a evolução:

```bash
uv run ferramentas/impl.py evoluir JAR-095/v1 --agente "Codex 5.6" --pedido "o robô sempre olha para o cursor"
```

- Isso copia a `v1` para a próxima livre (`v1.1`, depois `v1.2`…) e grava na ficha a `base` e o `pedido` (nas palavras de
  quem pediu). Evoluir a `v1.1` gera a `v1.2`. Uma abordagem nova, do zero, é outra versão (`iniciar` → `v2`).
- Trabalhe só na pasta nova, reporte com `etapa` e termine com `pronto --nota "o que mudou" --custo …`. No `README.md`,
  acrescente no topo uma seção "vN.M — <a mudança>".

## 8. O que é um bom resultado

O alvo é uma página que **responde a tudo**, no nível do
[Auralis](https://ds.asimov.academy/design-systems/auralis-design-system/design-system.html) e do
[New Era](https://ds.asimov.academy/design-systems/new-era-design-system/design-system.html). Abra as duas e interaja
antes de começar.

- **O conteúdo vem da imagem; o movimento vem do vídeo.** Textos e layout fiéis à `reference.png`. O que o vídeo inventa
  (texto que derrete, rótulo que muda, objeto que se deforma) não entra.
- **Tudo que se mexe é código** (CSS, SVG, Canvas, Three.js, shaders, GSAP). Vídeo nunca vira asset. Imagens estáticas
  geradas (placas de fundo, texturas) podem.
- **O que tem volume é 3D de verdade.** Personagem, robô, mascote, produto: um modelo 3D (GLB de image-to-3D), rigado e
  animado em Three.js. **2.5D é proibido**, inclusive como plano B: camadas recortadas com paralaxe, mapa de profundidade,
  CSS 3D sobre uma imagem, sprites. Se o 3D falhar em todos os modelos, pare e fale com o usuário.
- **Vá além do vídeo.** Cada componente importante reage ao cursor e às ações (o chat responde, o item citado acende, o
  personagem olha para o mouse), e o movimento ocioso do vídeo vira uma função que a interação também chama.
- Desempenho e acessibilidade não são prioridade agora.

Quem tem a skill `video2html` segue o método dela, junto com este guia (seções 3 a 6).

## 9. A ficha: impl.json

Quem a escreve é o `impl.py`. Escreva à mão só se não puder rodar `uv`: grave num arquivo temporário e renomeie por cima.

```json
{
  "agente": "Codex 5.6",
  "video": "JAR-142",
  "imagem": "JAR-043",
  "versao": "v4",
  "status": "aguardando",
  "etapa": "o robô 3D no lugar",
  "progresso": 0.35,
  "custo": 0.82,
  "previa": "phase1/index.html",
  "paradas": [{ "pagina": "phase1/index.html", "texto": "o robô 3D no lugar", "quando": "2026-10-24T20:05:12" }],
  "entradas": ["JAR-189", "JAR-180"],
  "inicio": "2026-10-24T19:40:00",
  "atualizado": "2026-10-24T20:05:12",
  "fim": null,
  "nota": ""
}
```

| Campo | Significado |
|---|---|
| `status` | `trabalhando` → `aguardando` (parado esperando o usuário) → … → `pronto`; ou `erro`, `abandonado` |
| `custo` | US$ gastos em APIs nesta versão, o total até agora |
| `previa` | a página que o cartão roda enquanto a versão não está pronta (relativa à pasta) |
| `paradas` | cada vez que o trabalho parou para aprovação (`impl.py aguardar`) |
| `entradas` | o que a página usa: o modelo 3D aprovado primeiro, depois as imagens com `--usa`. Sem `entradas`, a página pende do vídeo |
| `base`, `pedido` | só nas evoluções: a versão de origem e a alteração pedida |
| `estado`, `desloc` | só o app escreve: a aprovação do usuário e a posição do cartão arrastado |

## 10. Como aparece no app

- **trabalhando:** o cartão mostra o seu nome, a etapa e a barra de progresso; sem notícia há 15 min, "parado?".
- **aguardando:** o cartão roda a página da `previa`, com borda âmbar e o selo "aguardando você".
- **pronto:** o cartão roda o `index.html`; dois cliques abrem a página interativa; ✓ e ✕ aprovam ou descartam.
- **evolução:** pende da versão de origem por uma linha tracejada (v1 → v1.1 → v1.2).
- **erro / abandonado:** o cartão fica apagado, com o motivo.

Todo cartão de página também tem os botões de abrir a pasta no Finder, pinar e abrir a vista a partir dele.
