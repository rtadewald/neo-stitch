# Ler o caráter do movimento nos quadros

O `ler_video.py` diz onde, quanto e quando. O caráter (o ease, a duração, se é contínuo ou em pulsos) sai dos quadros.
Agente sem medir usa `power1.inOut` em tudo, e é por isso que a recriação parece "boiando" ao lado do vídeo.

## Medir antes de escolher

- **Duração:** conte os quadros do movimento (a 24 fps, 3 quadros = 0,125 s). Use `quadros/q_*.jpg` (a cada 0,25 s) para
  o geral e extraia o trecho a quadro cheio quando precisar:
  `ffmpeg -ss 1.0 -t 1.0 -i analise/video-ref.mp4 analise/trecho/%03d.png`.
- **Ease:** acompanhe um ponto (o centro do brilho, a ponta da luz na linha) quadro a quadro. Distância entre quadros
  encolhendo = `out`; crescendo = `in`; passou do alvo e voltou = `back`; constante = `none`.
- **Contínuo ou em pulsos:** a curva da região no `curvas.png`. Plana com ruído = deriva contínua; picos espaçados =
  eventos (cada pico vira um item da timeline no tempo do pico); onda regular = período (o `periodo_s`).
- **Amplitude:** a energia da região. É a régua do `comparar_vida.py`; não "suavize" por gosto.

## O que costuma aparecer em vídeo de UI gerado, e o que escrever

| Nos quadros | No código |
|---|---|
| Massa de fumaça/tinta revolvendo sem sair do lugar | deslocamento por ruído fbm no tempo (shader) ou `feDisplacementMap` animado; rotação lenta ≤ 4° |
| Partículas saindo devagar e sumindo | deriva linear para fora + alfa caindo, vida de 2 a 4 s, renascem na origem; semente fixa |
| Brilho que respira | escala 0,96 a 1,04 + opacidade, `sine.inOut`, período medido |
| Luz percorrendo uma linha | dash enchendo, `power2.out` 0,6 a 1 s, segura, decai `power1.in` 0,8 s |
| Ponto/nó acendendo quando a luz chega | anel + halo, `back.out(2)` 0,2 a 0,3 s, assenta em 0,4 s |
| Barras oscilando | ruído suave por barra (fase diferente), amplitude da curva, sem sincronizar todas |
| Microfone/ícone pulsando | anel que cresce e some (escala 1 a 1,6, opacidade 0,6 a 0), 1 a 1,5 s |
| Onda de cor atravessando | máscara radial crescendo sobre uma cópia tingida da camada |
| Texto ou número mudando, letra derretendo | artefato: não entra (marque no `vida.json`) |
| Câmera andando ou dando zoom | artefato numa tela de UI: não entra |

## Ritmo do ocioso

- Um loop de 6 a 10 s com algo novo a cada 1 a 2 s (eventos com folga entre si), mais a vida contínua por baixo
  (fumaça, barras). Tudo disparando junto no tempo 0 é o erro mais comum.
- O loop fecha: o estado no fim é o do começo (o que acendeu no meio, apaga antes de recomeçar).
- Interação pausa o ocioso e ele volta sozinho em ~6 s; a vida contínua (fumaça, barras) nunca para.
