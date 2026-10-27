# Armadilhas já pagas

## Método
- **Animar de memória.** A AZE-011/v1 mexia 0,10x o vídeo e ninguém mediu. Sempre `ler_video.py` antes, sempre
  `comparar_vida.py` depois.
- **Papel ou textura sintética no lugar do da imagem.** `feTurbulence` como grão de papel soma 3 a 6/255 de erro na
  tela inteira. A placa sai da referência.
- **`?estatico` que mexe.** Se algum módulo lê o relógio em `?estatico`, a foto pega um instante qualquer e o
  comparador mede lixo. Todo módulo desenha t = 0 quando `vida.estatico`.
- **Gemini como juiz.** Ele erra eventos curtos e não conhece o que o usuário recusou (na AZE-014 ele pediu de volta
  os "anéis de choque" neon que o Leo tinha vetado). Segunda opinião, nunca a régua.
- **Região viva que "não mexe" porque a camada é menor que o movimento.** No vídeo a massa inteira mexe; se só as
  faíscas mexem, a região fica FRACO. A camada inteira precisa participar.

## Pagas na AZE-011/v2 (2026-10-27)
- **Duas fases misturadas (flow map clássico) = fantasma.** Amostrar a textura em dois deslocamentos e misturar faz
  cada gota aparecer duas vezes, meio apagada: a tinta vira borrão. Uma amostra por pixel, sempre.
- **Deslocamento grande e fino estica.** Turbulência de 30 px numa escala de 40 px transforma gota redonda em oval e
  desmancha o cacho de fumaça. O que no vídeo ANDA (gota, cacho) pede fluxo muito largo (escala ~260 px, gradiente baixo):
  ele carrega a forma inteira.
- **A casca não mexe.** O contorno fino da esfera tremendo vira gelatina; proteja a faixa r ≈ 1 no shader.
- **Detalhe procedural precisa de média zero.** Ruído somado à tinta escurece a esfera (fidelidade de tom cai) e, forte,
  vira "vermes"/mármore. Duas cristas defasadas, uma menos a outra, intensidade baixa (0,25): fiapo, não mancha.
- **Gota de Canvas translúcida parece poeira cinza.** As do vídeo são tinta sólida: alfa quase 1, somem encolhendo.
  E menos do que parece: 420 já igualaram a energia do vídeo.
- **Energia aprova ruído.** Foi preciso a régua de textura (`ÁSPERO`/`LISO`) para a tabela concordar com o olho.
- **Caixinha de uma gota só mede sorte.** Campo de partículas vai com `agregar: true` no `vida.json`.
- **A luz tem que correr em cima da linha da imagem.** Um caminho "parecido" (faísca → dobra → nó) aparece como uma
  segunda linha. Ajuste a reta nos pixels (PCA), estenda até perto da faísca e use exatamente ela.
- **Texto dinâmico vaza.** O texto da imagem cabe no balão; o do usuário não. `nowrap` no chat escondeu isso até a demo.
- **Escala fixa das barras pequenas não lê.** Barra de 13 px oscilando 40 % não aparece; Rede precisou de ±130 %.
- **O comparador só vê os primeiros segundos.** Ele corta a página na duração do vídeo (4 s): movimento lento demais
  (fluxo que só muda em 10 s) não conta. Velocidade do fluxo ~0,3 a 0,8 por segundo.

## Filmagem e determinismo
- O `filmar.py` troca rAF, timers, `performance.now`, `Date` e `Math.random` antes da página carregar. Código que
  espera tempo real (`await new Promise(r => setTimeout(r, 500))` antes de desenhar o 1º quadro) só anda quando o
  filmador passa o relógio: o `--aquecer` (0,5 s) cobre isso; espera maior, aumente.
- Vídeo, áudio e `IntersectionObserver` não obedecem ao relógio virtual (e vídeo nem pode estar na página).
- WebGL no Chrome do Windows roda em ANGLE/D3D11: o mesmo quadro pode variar ±1 nível entre rodadas. O `checar.py`
  trata determinismo como aviso por isso.
- Antes de filmar, `checar.py`: um erro de JS faz `vida` não existir e o `--antes` falhar em silêncio.

## WebGL e camadas
- `ShaderMaterial` não converte espaço de cor: textura com `NoColorSpace` e `renderer.outputColorSpace =
  THREE.LinearSRGBColorSpace` para os pixels saírem iguais aos da imagem.
- Devolva cor **premultiplicada** (`rgb * a`) do shader, senão o fundo do recorte vaza como um retângulo.
- O `UnrealBloomPass` descarta o alfa: brilho em outro canvas (só as partes claras, fundo preto) com
  `mix-blend-mode: screen` e máscara radial. Sem `OutputPass` nessa camada (clareia tudo).
- Máscaras complementares (esfera / resto) com borda suave nas duas criam um anel claro na costura: uma das duas é
  binária.

## GSAP e SVG
- Não ponha `transform-box`/`transform-origin` no CSS de elemento SVG que o GSAP escala (ele escala a partir de 0,0).
  Em círculos, anime `attr: { r }`.
- A timeline ociosa reinicia o estado no tempo 0, e cada disparo encerra o anterior do mesmo elemento
  (`gsap.killTweensOf`).
- `page.evaluate` que devolve um objeto do GSAP trava o Playwright: o `--antes` do `filmar.py` já embrulha e devolve null.

## Windows
- Scripts com `uv run` (dependências inline). `ffmpeg`/`ffprobe` no PATH (`winget install Gyan.FFmpeg`).
- O shell aberto antes de instalar o `uv` não o enxerga: terminal novo, ou o caminho completo do `uv.exe`.
- O servidor do Neo Stitch serve `projects/` em http; textura WebGL não carrega de `file://`.
