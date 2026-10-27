---
name: video2html
description: >-
  Transforma uma imagem de UI aprovada + o vídeo dela animada (image-to-video do Neo Stitch) num HTML vivo e
  interativo, fiel à imagem parada e com o movimento do vídeo em código (CSS/SVG, Canvas, WebGL, GSAP). Mede tudo:
  lê o vídeo por pixel (onde, quanto, quando) e pelo Gemini (o quê, como), separa o que vive em camadas, compara a
  página parada com a imagem e a página em movimento com o vídeo região por região, e só entrega com os números
  dentro da régua e a crítica em 8. Use quando o usuário pedir para implementar um vídeo do Neo Stitch como HTML,
  "dar vida" a uma imagem aprovada, citar /video2html ou um código de vídeo (ex.: AZE-014) para virar página.
---

# Vídeo → HTML vivo (Neo Stitch)

Você não consegue assistir ao vídeo. Então trate o trabalho como **reconstrução medida**: transforme o vídeo em
números e imagens que dá para olhar, escreva o que se mexe e quando, construa em camadas, e prove cada coisa contra a
fonte com um script. "Parece certo" não é prova. Sem número, não passa.

**Entrada:** o código de um vídeo (`AZE-014`). A imagem é a 1ª entrada do pedido de vídeo dele.
**Saída:** `projects/<slug>/impl/<IMAGEM>/vN/`, registrada pelo `ferramentas/impl.py` (o cartão aparece no 🔥).

## Por que esta skill existe

A AZE-011/v1 foi feita só com o `docs/AGENTES.md`, sem método. Medida com os scripts daqui: parada, **12,8/255** de
diferença para a imagem (o alvo é 5); em movimento, **0,10x** da energia do vídeo, as 20 regiões vivas PARADAS;
`?estatico` que mexia e nenhuma linha do tempo ociosa. O Leo viu "zero animação, nada fiel" antes de qualquer número.
Os três erros de raiz, que esta skill fecha:
1. **Não leu o vídeo.** Animou de memória, com amplitude de enfeite. → fase 1 obrigatória, energia como régua.
2. **Não calibrou nada contra a imagem.** Textos alguns px fora e de outro tamanho, papel sintético no lugar do
   papel da imagem. → placa tirada da própria imagem, texto calibrado pela caixa de tinta, `comparar_estatico.py`.
3. **Não verificou o que entregou.** → `checar.py` + `comparar_vida.py` + crítica com nota, antes de dizer pronto.

## Princípios

1. **O conteúdo vem da imagem; o movimento vem do vídeo.** Texto, layout, cor e tipografia: a `reference.png`. O que
   se mexe, quanto e quando: o vídeo, medido. O que o modelo de vídeo inventou (texto que muda, rótulo que troca,
   objeto novo, câmera) **não entra**.
2. **As decisões do usuário valem mais que o vídeo.** Se ele pediu "pulsa de leve, sem anel neon", isso vira alvo
   menor ou artefato no `vida.json`, e nenhum comparador nem o Gemini te convencem do contrário.
3. **Amplitude é parte da fidelidade.** Um movimento 10x menor que o do vídeo não é "sutil", é ausente. Mire razão de
   energia entre 0,6 e 1,8 em cada região viva (o `vida.json` diz quando é outro alvo).
4. **Tudo que se mexe é código, em camada própria.** Nunca vídeo/GIF como camada; nunca assar na placa algo que o
   `vida.md` anima. Escada de técnica, o degrau mais baixo que convence: CSS/SVG → Canvas 2D → WebGL/Three.js.
5. **Ir além do vídeo.** O ocioso vira uma linha do tempo, e cada movimento é uma função que a interação também chama:
   passar o mouse no agente dispara o feixe até ele, o chat responde e acende quem foi citado.
6. **Determinismo.** A página é filmada com relógio virtual (`filmar.py`): rAF, timers, `performance.now`, `Date` e
   `Math.random` obedecem ao filmador. Código normal funciona; o que quebra é estado que depende de tempo real.
7. **Marca.** Projeto com design system (AZEO: `C:\Projetos\AZEO-Brain\_azeo\assets\design\DESIGN-SYSTEM.md`): cor de
   texto e fonte vêm do token, não do olho; a imagem gerada pode ter errado a fonte (GPT Image erra), e o HTML corrige.
   Desvio pedido em relação à imagem entra no `--ignorar` do comparador estático e no README.

## Pipeline e régua

```
0. preparar      impl.py iniciar · copiar modelo/
1. ler           ler_video + descrever_video + olhar  → vida.md + vida.json          [gate 1: mapa de vida]
2. estático      placa + camadas + texto calibrado    → comparar_estatico ≤ 5/255   [gate 2: ?estatico × imagem]
3. vida          vida.js (ocioso + mov + interação)   → checar.py limpo
4. verificar     filmar + comparar_vida               → nenhuma região PARADO/FRACO
5. crítica       nota 1-10 em 5 eixos, corrige os 3 piores, repete                [gate 3: todas ≥ 8]
6. entregar      README + assets no canvas + impl.py pronto
```

**Gates:** mostre (caminho dos arquivos + o número), pergunte e **pare**. Se o usuário disser **modo autônomo**, siga
sem parar e registre tudo no README. Os números valem nos dois modos: modo autônomo não é licença para entregar fora da
régua.

| Régua | Script | Passa |
|---|---|---|
| contrato | `checar.py` | zero erro de console/rede, `vida.ocioso` existe, `?estatico` congela, normal mexe, nenhum texto cortado |
| parado | `comparar_estatico.py` | média ≤ 5/255, nenhuma célula > 14, deslocamento (0, 0) |
| movimento | `comparar_vida.py` | nenhuma região PARADO/FRACO/ÁSPERO/LISO; energia global 0,6 a 1,8 do alvo; textura 0,7 a 1,35 |
| crítica | você, olhando | fidelidade, vida, coreografia, interação, acabamento: todas ≥ 8 |

Scripts em `.claude/skills/video2html/scripts/`, rodados da raiz do repo com `uv run` (dependências inline). Precisam
de ffmpeg no PATH, Google Chrome instalado e, para o `descrever_video.py`, `OPENROUTER_API_KEY` no `.env`.
Abaixo, `S=.claude/skills/video2html/scripts`, `V=projects/<slug>/impl/<IMG>/vN` e
`U=http://localhost:8730/projects/<slug>/impl/<IMG>/vN/index.html`.

## 0. Preparar

1. `uv run ferramentas/impl.py iniciar <VÍDEO> --agente "Claude Opus 5.5"`: reserva a vN e já põe `reference.png`
   e `analise/video-ref.mp4` na pasta. Reporte etapas com `impl.py etapa <IMG/vN> "…" --progresso 0.x` a cada fase
   e pelo menos a cada 10 min.
2. Copie `modelo/` desta skill para a vN (`index.html`, `assets/styles.css`, `assets/vida.js`, `comparar.html`).
3. Leia o pedido de vídeo (`uv run ferramentas/neo.py ver <VÍDEO>` e o pedido pai): a intenção, os comentários com
   pin e o que o usuário disse no chat sobre o movimento. Isso alimenta os alvos do `vida.json`.

## 1. Ler o vídeo → mapa de vida

1. `uv run $S/ler_video.py $V/analise/video-ref.mp4 $V/analise` → abra `movimento.png`, `quadros/folha.jpg` e
   `curvas.png`. As regiões (`r01`…) com energia, picos e período são a régua da fase 4.
2. `uv run $S/descrever_video.py $V/analise/video-ref.mp4 $V/analise/gemini.md --regioes $V/analise/regioes.json`
   (~$0,01): o QUE e o COMO, com artefatos. O tempo fino vem do passo 1, não daqui.
3. Abra os quadros de pico (`analise/pico/rNN.jpg`) das regiões grandes e confira com os olhos. Agrupe regiões que
   são o mesmo elemento (núcleo em 3 pedaços = "núcleo"). Marque artefatos.
4. Escreva **`vida.md`** (modelo: [referencias/vida.exemplo.md](referencias/vida.exemplo.md)): ritmo geral; tabela
   **elemento | regiões | ocioso (medido) | interação (nossa) | técnica (degrau) | alvo**; linha do tempo ociosa em
   segundos; como a interação pausa e retoma o ocioso.
5. Escreva **`vida.json`**, a versão que os scripts leem:
   ```json
   {"elementos": [
     {"nome": "núcleo de tinta", "regioes": ["r01", "r03", "r05"], "alvo": 1.0},
     {"nome": "gotas", "regioes": ["r11", "r13", "r19"], "alvo": 1.0, "agregar": true},
     {"nome": "ponto que fala", "regioes": ["r03"], "alvo": 0.5, "motivo": "pedido: pulsa de leve, sem anel"},
     {"nome": "anel neon do microfone", "regioes": ["r06"], "artefato": true, "motivo": "recusado no pedido"}
   ]}
   ```
   `agregar: true` em elemento estatístico (campo de gotas, faíscas, chuva): as caixinhas do `ler_video` em volta de
   uma gota só medem sorte, e ele passa a ser julgado pela área toda. Alvo menor que 1 ou artefato só com motivo do
   usuário (o pedido, o comentário, o chat), nunca para passar na régua.
6. **Gate 1:** mostre o `vida.md` e pare.

## 2. Fase estática (a imagem, em camadas)

Meta: `?estatico` indistinguível da imagem. Monte de baixo para cima, medindo cada passo.

1. **Placa (o fundo sem o que vive).** Da própria imagem, nunca de textura sintética:
   `uv run $S/isolar_camada.py $V/reference.png $V/assets/camadas --caixa x,y,w,h [--elipse]` separa o objeto vivo
   em `escura.png` (multiply) + `clara.png` (screen) sobre `placa.png`, recompondo a imagem com erro ~0. Para fundo
   com desenho forte, gere a placa com GPT Image 2 apagando o objeto e passe `--placa`. Receitas por tipo de objeto
   (tinta sobre papel, orbe, personagem, arte luminosa fina, feixes): [referencias/receitas.md](referencias/receitas.md).
   Depois tire da placa o que vira HTML/SVG: `uv run $S/limpar_placa.py <placa> $V/assets/placa.png --apagar
   escuro:x,y,w,h …` (texto), `verde:` (traço do acento), `tudo:` (caixa inteira, com `--grao-de x,y` de um trecho de
   papel limpo para não ficar liso). Abra a placa: mancha cinza ou retângulo claro onde havia algo = refaça.
   Coisa fixa que cruza a tinta viva (linhas até os agentes) vira camada própria POR CIMA da tinta, com os pixels da
   imagem: assim a fumaça mexe embaixo sem entortá-la.
2. **Texto e controles em HTML de verdade.** Ache as caixas de tinta de todas as linhas de texto (componentes escuros
   ligados na horizontal, ver `construir/` da AZE-011/v2). Família e peso: `uv run $S/achar_fonte.py $V/reference.png
   --caixa x,y,w,h --texto "…" --familias mono|sans|"A,B"` dá o ranking do Google Fonts; se o projeto tem design system,
   a fonte dele manda e o ranking só diz o quanto a imagem se afasta (com eixo de largura/peso, como Science Gothic
   `wdth`, dá para chegar no desenho da imagem dentro da marca). Escreva `textos.json` (id, caixa_ref, âncora) e
   calibre: `uv run $S/calibrar_texto.py "$U?estatico" textos.json $V/assets/textos.css --ref $V/reference.png` ajusta
   left/top/font-size (e letter-spacing com `largura`) até ±1 px em 2 a 4 rodadas. Itens repetidos (agentes, barras)
   saem de coordenadas medidas na imagem (centro e raio de um arco por mínimos quadrados sobre os pontos).
   Texto que muda em execução (chat) precisa de largura e quebra (`white-space: normal` + `width` do balão) e limite de
   caracteres: o texto da imagem cabe, o do usuário não.
3. **`?estatico`** (já no `vida.js` do modelo): `<html data-estatico>`, ocioso pausado em 0, módulos desenhando t = 0,
   relógio com a hora da imagem, dados parados. Fotografe e compare:
   ```bash
   uv run $S/filmar.py "$U?estatico" $V/verificacao/estatico.png --foto
   uv run $S/comparar_estatico.py $V/reference.png $V/verificacao/estatico.png $V/verificacao/estatico [--ignorar x,y,w,h]
   ```
   Leia `calor.png` e `piores/`. Deslocamento global ≠ (0, 0) = escala ou viewport errados: corrija antes de tudo.
   Texto "duplicado" no calor = posição ou tamanho fora. Grão do papel e ruído de IA que sobram são irredutíveis:
   anote e não persiga.
4. **Gate 2:** a foto ao lado da imagem + o número. Pare.

## 3. Fase de vida

Contrato (o `checar.py` confere): `window.vida = { ocioso, interagiu, mov, estatico }`.
- **`mov`**: uma função por elemento do `vida.md` (`feixe(id)`, `pulso()`, `ativar(agente)`), que devolve um tween ou
  timeline. O ocioso e a interação chamam as mesmas.
- **`ocioso`**: `gsap.timeline({ repeat: -1 })` montada com os **tempos medidos** (picos e período do `regioes.json`).
  O tempo 0 reinicia o estado (o que ligou no meio, desliga no fim); cada disparo mata o anterior do mesmo elemento.
- **Módulos procedurais** (partículas, fumaça, WebGL): `desenhar(t)` função pura de t, registrada no relógio único do
  modelo (`registrar`). Aleatório só com semente (`aleatorio()`).
- **`interagiu()`** pausa o ocioso e retoma em ~6 s. Hover, clique, chat e microfone chamam `mov` + `interagiu()`.
- Amplitude: comece **na** amplitude do vídeo (a energia da região diz o quanto). Contido só onde o `vida.json` manda.
- Como medir o caráter de cada movimento a partir dos quadros (ease, duração, ritmo):
  [referencias/vocabulario.md](referencias/vocabulario.md). Erros já pagos: [referencias/armadilhas.md](referencias/armadilhas.md).

Depois de cada bloco de vida: `uv run $S/checar.py "$U" --pasta $V`. Erro de console invalida tudo que vem depois.

## 4. Verificar o movimento

```bash
uv run $S/filmar.py "$U" $V/verificacao/html.mp4 --segundos <duração do vídeo> --antes "vida.ocioso.restart()"
uv run $S/comparar_vida.py $V/analise/video-ref.mp4 $V/verificacao/html.mp4 $V/verificacao \
  --regioes $V/analise/regioes.json --vida $V/vida.json
```
- `PARADO`/`FRACO` numa região viva: o elemento não está vivo o bastante, ou a camada dele não cobre a região (ex.:
  só as faíscas mexem e o vídeo mexe a massa inteira). Corrija e filme de novo.
- `EXAGERADO`: confira se não é vida nossa de propósito (interação, dado vivo); se for, anote; se não, baixe.
- `ÁSPERO` / `LISO`: mexe na quantidade certa com o caráter errado. Áspero = ruído, "vermes", detalhe procedural forte
  demais. Liso = borrão, fantasma (misturar duas amostras deslocadas), deslocamento grande esticando a tinta. A energia
  sozinha aprova os dois; foi assim que a AZE-011/v2 chegou a 0,94x com a esfera virando mármore.
- **Olhe junto de cada número.** Monte uma tira de 4 a 6 quadros da mesma área (vídeo em cima, página embaixo) a cada
  rodada que mexe na técnica. Quase toda correção boa da AZE-011/v2 veio dessa tira, não da tabela: gota redonda
  esticada em oval, cacho de fumaça desmanchando, gotas cinza em vez de pretas, luz fora da linha da imagem.
- Abra `pares.jpg` e `lado-a-lado.mp4` (ou `comparar.html` pelo servidor, com sobreposição e diferença).
- Segunda opinião (centavos): `uv run $S/descrever_video.py $V/analise/video-ref.mp4 $V/verificacao/gemini.md --comparar
  $V/verificacao/html.mp4`. Ele não conhece o `vida.json`: se pedir de volta o que o usuário recusou, ignore.
- Demo das interações: `filmar.py "$U" $V/verificacao/interacao.mp4 --segundos 8 --antes "<dispare hover, chat e clique>"`.

## 5. Crítica em rodadas

Olhe `estatico.png` × `reference.png`, `pares.jpg` e quadros da demo de interação. Dê nota de 1 a 10:
1. **Fidelidade parada:** dá para confundir com a imagem? (o número ajuda, o olho decide)
2. **Vida:** cada coisa que vive no vídeo vive aqui, com a amplitude certa?
3. **Coreografia:** ritmo, ease e encadeamento batem com o vídeo, sem tempo morto nem tudo mexendo junto?
4. **Interação:** os gatilhos reais existem e usam os mesmos movimentos? Responde a tudo que parece clicável?
5. **Acabamento:** nítido, sem serrilhado, sem costura de camada, sem brilho que vaza, fonte e cor do token?

Corrija os 3 piores problemas, refilme, compare de novo, nova rodada. Registre cada rodada no README (notas + o que
mudou). **Gate 3** só com todas ≥ 8.

## 6. Entregar

- `README.md` da vN: o que vive e como, os números finais (estático, energia por elemento, checar), custos, o que
  ficou de fora e por quê, desvios pedidos.
- Toda imagem gerada no trabalho (placa feita por IA, recorte, textura) vira cartão:
  `uv run ferramentas/impl.py asset <IMG/vN> <arquivo.png> --nome "…" --nota "…" --custo 0.04`.
- `uv run ferramentas/impl.py pronto <IMG/vN> --nota "…"` (exige `index.html`).
- Uma linha no chat: o que vive, os três números, o link da página.

Alteração pedida numa versão pronta **nunca a edita**: `impl.py evoluir <IMG/vN> --agente "…" --pedido "…"` cria a
vN.M, e a régua inteira vale de novo na versão nova.

## Layout da pasta

```
vN/
  reference.png  vida.md  vida.json  README.md  impl.json
  index.html  comparar.html
  textos.json  construir/ (scripts de medição do projeto: caixas de texto, linhas, pontos, fatias)
  assets/  styles.css  textos.css  vida.js  <módulos>.js  placa.png  camadas/
  analise/  video-ref.mp4  regioes.json  mascaras.npz  movimento.png  curvas.png  paleta.json  quadros/  pico/  gemini.md
  verificacao/  estatico.png  estatico/  html.mp4  movimento.json  movimento.txt  pares.jpg  lado-a-lado.mp4  gemini.md
```

## Não fazer

- Começar a animar antes do `vida.md` e do `vida.json`.
- Copiar o vídeo ao pé da letra (os erros dele inclusive) ou usar vídeo/GIF como camada.
- Desenhar papel, fumaça ou textura que a imagem já tem: tire da imagem (`isolar_camada.py`).
- Assar na placa algo que o `vida.md` anima.
- Dizer "pronto" com `checar.py` falhando, região viva PARADO/FRACO, estático acima de 5 ou nota abaixo de 8.
- Deixar o Gemini (ou qualquer comparador) passar por cima do que o usuário decidiu.
- Gravar a página em tempo real para comparar (perde quadros). Sempre `filmar.py`.

## Origem

Método construído em 2026-10-27 a partir de três referências estudadas: a `video2html` do Rodrigo Tadewald (autor
do Neo Stitch), o Motion2Code (Lovis Odin, MIT) e o One Shot UI (tn0123, MIT), mais o motor de vídeo da AZEO.
O que veio de cada uma e as licenças: [referencias/origem.md](referencias/origem.md).
