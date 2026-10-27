# AZE-011 · Jarvis "Papel em Relevo" · mapa de vida (exemplo)

**Imagem:** `reference.png` (AZE-011, 1536×864) · **Vídeo:** `analise/video-ref.mp4` (AZE-014, Grok Imagine 1.5 Lite, 4,04 s)
**Leituras:** `analise/movimento.png` + `regioes.json` (20 regiões, energia global 6,7, piso de ruído 0,9) · `analise/gemini.md`
**Pedido do Leo (vale mais que o vídeo):** "o ponto verde pulsa de leve, sem anel neon; só as linhas até Comercial,
Prospecção e Propostas acendem; os pontos de Tarefas não mudam".

## Ritmo geral

Vida contínua e orgânica por baixo (a tinta revolve como fumaça na água, as partículas da esquerda derivam e se
desfazem, as barras oscilam) e, por cima, um ciclo de fala: o ponto verde do núcleo respira (período medido 2,5 s em
r03) e a luz sai dele para os três agentes ativos. O vídeo tem 4 s; o loop do HTML fica em 7,5 s (três respirações)
para os três feixes caberem com folga.

## Elementos

| Elemento | Regiões | Ocioso (medido no vídeo) | Interação (nossa) | Técnica | Alvo |
|---|---|---|---|---|---|
| Massa de tinta do núcleo | r01, r05, r12, r14, r02 (difusa) | revolve sem sair do lugar, energia 39 a 45 em toda a massa; nada de giro rígido | o cursor perto empurra a tinta (deslocamento local) | `isolar_camada --elipse` → escura em WebGL com UV deslocado por fbm + rotação ≤ 3° | 1,0 |
| Partículas da esquerda | r11, r19, r16, r13, r15, r04 (difusa) | derivam para a esquerda e somem; r11 é a mais forte (70) | aceleram um instante quando o Jarvis fala | atlas das manchas pequenas da escura, Canvas 2D, semente fixa | 1,0 |
| Ponto verde que fala | r03 | respira, período 2,5 s; no vídeo vira anel neon grande | pulso mais rápido enquanto o chat "digita" | halo radial em `screen`, escala 0,96 a 1,06 | **0,5** (pedido) |
| Anel neon em volta do ponto | (dentro de r03) | anel grande e brilhante | – | não entra | **artefato** |
| Linhas até os 3 agentes | (abaixo do limiar: luz fraca) | a luz percorre do núcleo ao agente, um de cada vez | hover no agente dispara a linha dele; agente citado no chat acende | SVG, dash enchendo + segura + decai | medido no `pares.jpg` |
| 4ª linha até Stories | – | aparece no vídeo | – | não entra | **artefato** |
| Barras CPU / Memória / Rede | r10, r08, r07 | oscilam (energia 33 a 43); Rede com período 1,6 s | dados vivos plausíveis | SVG por ruído suave, fase por barra | 1,0 |
| Pontos de Tarefas | r17, r18 | mudam de quantidade | – | ficam parados | **artefato** (pedido) |
| Microfone | r06 | anel pulsando (30,6), picos 2,8 / 3,7 / 4,0 s | clique: modo ouvindo | anel CSS que cresce e some | 0,7 |
| Ponto solto r20 | r20 | brilho pequeno perto do arco (11,8) | – | conferir no `pico/r20.jpg`: se for ruído, artefato | 1,0 |

## Linha do tempo ociosa (loop de 7,5 s)

```
contínuo  tinta revolve · partículas derivam · barras oscilam
0,0  ponto verde respira (2,5 s, sine.inOut), três vezes no loop
0,6  luz → Comercial ········ 1,4 nó acende ··· 2,6 decai
2,4  luz → Prospecção ······· 3,2 nó acende ··· 4,4 decai
4,2  luz → Propostas ········ 5,0 nó acende ··· 6,2 decai
5,6  microfone pulsa ········ 6,6
7,5  recomeça (todos os nós no estado da imagem)
```

Interagir (hover num agente, digitar, clicar no microfone) pausa os eventos; a vida contínua não para. Volta em 6 s.

## vida.json

```json
{"elementos": [
  {"nome": "massa de tinta", "regioes": ["r01", "r05", "r12", "r14", "r02"], "alvo": 1.0},
  {"nome": "partículas", "regioes": ["r11", "r19", "r16", "r13", "r15", "r04"], "alvo": 1.0},
  {"nome": "ponto verde", "regioes": ["r03"], "alvo": 0.5, "motivo": "pedido: pulsa de leve, sem anel neon"},
  {"nome": "barras", "regioes": ["r10", "r08", "r07"], "alvo": 1.0},
  {"nome": "pontos de tarefas", "regioes": ["r17", "r18"], "artefato": true, "motivo": "pedido: não mudam"},
  {"nome": "microfone", "regioes": ["r06"], "alvo": 0.7, "motivo": "anel discreto, sem neon"}
]}
```
