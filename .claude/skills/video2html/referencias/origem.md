# De onde veio cada parte (2026-10-27)

Pedido do Leo: estudar o que existe com o mesmo intuito (GitHub, X, Reddit) e montar uma skill própria do Neo Stitch,
como foi feito com o método de motion do Movez na `/video-apresentacao`.

| Referência | Licença | O que veio |
|---|---|---|
| [rtadewald/skills · video2html](https://github.com/rtadewald/skills/tree/main/video2html) (Rodrigo Tadewald, autor do Neo Stitch) | **sem licença** no repositório | a espinha: dois leitores do vídeo (pixel + Gemini), mapa de vida com tabela elemento/ocioso/interação/técnica, camadas em vez de fundo único, `?estatico`, escada de técnica, armadilhas de WebGL/GSAP, gates |
| [lovisdotio/motion2code](https://github.com/lovisdotio/motion2code) (Lovis Odin) | MIT | "você não consegue assistir ao vídeo", filmar por relógio e não em tempo real, pares quadro a quadro com nota, checagem de contrato/console/rede/determinismo, `compare.html` com sobreposição, vocabulário de movimento medido nos quadros |
| [tn0123/one-shot-ui](https://github.com/tn0123/one-shot-ui) | MIT | diferença irredutível (não perseguir grão e ruído), texto escondido/cortado como falha estrutural que o pixel não pega |
| motor da `/video-apresentacao` (AZEO) | nosso | o relógio virtual (`lib/relogio.mjs`), a crítica em rodadas até toda nota ser 8 |
| buscas sem achado útil | | Reddit: relatos de que modelos travam indo direto de vídeo para código (reforça as etapas); Space Jam 1996 refeito por screenshot (o pixel diff ajuda, não garante) |

**Sobre a licença da video2html:** o repositório do Rodrigo não declara licença, então os scripts e o texto dele não
foram copiados. Tudo aqui foi escrito do zero sobre as ideias. O fork `leoazevedodeveloper/neo-stitch` é público:
mantenha assim (ideia sim, cópia não) antes de dar push.

**O que é nosso e nenhuma das três tem:**
- **Energia por região** (`comparar_vida.py`): a razão página/vídeo com alvo por elemento. É o que pegaria a
  AZE-011/v1 (0,10x) na hora; a video2html só marca PARADO/fraco, sem régua de amplitude.
- **`vida.json`**: as decisões do usuário (contido, recusado) viram números que os comparadores respeitam.
- **Placa por ajuste suave do papel** (`isolar_camada.py` sem `--placa`): separa tinta de papel sem API.
- **Régua de passa/não passa** em todos os scripts (saída 1), para modo autônomo não entregar fora dela.
