# Receitas por tipo de elemento vivo

Escolha pelo que o elemento É na imagem, não pelo que seria mais fácil de codar. Sempre a camada sai da própria
`reference.png`; o código mexe nela, não a redesenha.

## Tinta, fumaça, partículas sobre papel ou fundo liso

O caso da AZE-011 (núcleo de tinta) e da JAR-043 (esfera de tinta).

1. `isolar_camada.py reference.png assets/camadas --caixa x,y,w,h --elipse` (a caixa justa no objeto; `--elipse`
   quando ele é redondo, para não levar junto arco, rótulos e linhas da vizinhança).
2. Confira `placa.png`: tem que ser só papel. Sobrou sombra do objeto: aumente `--raio` ou gere a placa com GPT Image 2
   ("remove the ink object, keep the paper texture and everything else exactly") e passe `--placa`.
3. Antes de usar `escura.png`, apague dela o que o código vai redesenhar por cima (as linhas até os agentes, um ponto
   de brilho): pinte de branco na escura (multiply com branco = nada). Senão a linha antiga gira junto com a tinta.
4. Na página: `placa.png` no fundo; `escura.png` com `mix-blend-mode: multiply`; `clara.png` com `screen` só se houver
   brilho mais claro que o papel. Posicione exatamente onde o script disse (`left/top`).
5. Movimento: o que funcionou na AZE-011/v2 (`projects/azeo/impl/AZE-011/v2/assets/nucleo.js`, 0,89x, textura 1,0x):
   - a escura vira textura num `<canvas>` WebGL (multiply); **uma amostra por pixel**, deslocada pela soma de:
     turbulência fina (curl de fbm, escala ~40 px, ~8 px, velocidade ~0,8/s) · fluxo largo (escala ~150 px, ~25 px) ·
     "viagem" muito larga na nuvem de fora (escala ~260 px, ~40 px: gotas e cachos andam inteiros) · giro ≤ 0,04 rad.
     Turbulência fina mais forte no miolo (fiapos suaves aguentam) e quase nula na casca (contorno fica parado).
   - fiapos novos (o modelo de vídeo regenera a fumaça): duas cristas de fbm defasadas, uma menos a outra, modulando só
     a tinta que existe, intensidade ~0,25. Mais que isso vira mármore.
   - gotas que saem e se desfazem: Canvas 2D, origens = pixels de tinta da borda da nuvem; cada gota é função pura do
     tempo (ciclo por hash), sólida, some encolhendo; ~400.
   - luz do "falar": gradiente radial em screen preso ao pulso, cobrindo a esfera, recortado pelo círculo dela.
   - em `?estatico` nada disso roda e fica a `<img>` da escura: idêntico à imagem por construção.
   - barato, quando não precisa de WebGL: `feTurbulence` + `feDisplacementMap` (3 a 10 px) mudando por tempo.
6. A régua: energia E textura de cada região no `comparar_vida.py`, mais a tira de quadros a cada rodada. A v1 da
   AZE-011 mexia a 0,08x; a v2 passou por borrão (0,65x, LISO) e por mármore (0,94x, ÁSPERO) antes de acertar.

## Objeto redondo vivo (esfera, planeta, orbe)

- `SphereGeometry` com projeção frontal da textura (uv = posição/(2R) + 0,5, preso no vértice: gira junto).
- Câmera **ortográfica** (a perspectiva infla o centro) e posição com meio pixel, para o texel cair no pixel.
- Estenda a textura além da borda com a cor da borda: girar nunca mostra fundo branco.
- Giro pequeno (≤ 7°) se algo cobre parte do objeto na imagem.

## Personagem ou objeto que precisa de volume (olhar o cursor)

- Recorte pixel-exato: `uvx --python 3.12 --from "rembg[cpu,cli]" rembg i -m birefnet-general crop.png saida.png`
  (o modelo baixa ~1 GB na 1ª vez).
- Placa sem ele: GPT Image 2 apagando o objeto do recorte da referência.
- 2.5D: mapa de profundidade gerado pelo GPT Image 2 ("depth map aligned pixel-for-pixel, white = closest, smooth")
  num `PlaneGeometry` subdividido + `ShaderMaterial` que desloca z. Giro ≤ 9°, mais que isso deforma.

## Arte luminosa fina (neurônio, circuito, filamentos) sobre fundo escuro

- Placa sem nada (GPT Image 2) + `isolar_camada.py --placa placa.png`: a `clara.png` vira a camada em `screen`.
- O que "anda pelo desenho" (faíscas, sinais): extraia o esqueleto da máscara dos traços (scikit-image `skeletonize`)
  e anime pontos sobre as polilinhas.
- Onda de cor que se espalha: 2ª cópia da camada tingida (`sepia + saturate + hue-rotate`) revelada por máscara radial
  que cresce.

## Feixe ou linha que acende até um destino

- SVG `<path>` com as coordenadas medidas na imagem (o ponto do núcleo e o ponto do agente).
- Em repouso o caminho é **fraco** (opacidade 0,2 a 0,35); se já brilha parado, a luz passando não se lê.
- A luz **enche** a linha (`stroke-dashoffset` de L a 0, `power2.out`, 0,6 a 1 s), segura ~1,2 s e decai. Não um
  cometa curto. O nó de destino acende quando a luz chega (mesma timeline, `"<+=dur"`).
- Linha que já está desenhada na placa: apague da placa e desenhe no SVG, senão são duas.

## Telemetria (barras, números, pontos de tarefa)

- Barras em SVG ou `<div>` com altura por JS a partir de um ruído suave com semente; amplitude e frequência da curva
  da região no `regioes.json` (picos e período).
- Números que o vídeo deixou parados ficam parados (texto que muda no vídeo é artefato). Se for viver, varia pouco e
  plausível, e só fora do `?estatico`.

## Texto, ícones e controles

- Sempre HTML real. Família e peso do design system (ou o Google Font mais próximo), depois calibração pela caixa de
  tinta: recorte a linha na referência e na foto, binarize, compare a caixa (x, y, largura, altura) e ajuste até ±2 px.
- Ícone difícil: recorte direto da referência (`assets/crops/`), ou SVG desenhado no mesmo traço.
- Cartões em relevo (papel prensado): `box-shadow` com a luz na direção da imagem, amostrada na borda clara e na
  escura do cartão. Cantos chanfrados: `clip-path: polygon(...)` (o `corner-shape` ainda não é universal).

## Brilho (bloom) sem estragar o fundo claro

- Fundo claro não aguenta bloom global. Brilho é um gradiente radial ou um `<canvas>` separado só com as partes
  claras, em `screen`, recortado por máscara radial. Intensidade no máximo a do vídeo; acima disso é neon.
