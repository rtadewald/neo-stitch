# Neo Stitch — para agentes

Canvas local para explorar interfaces: **imagem → vídeo → HTML vivo**. O app roda em http://localhost:8730
(`uv run ferramentas/servidor.py`; código em `app/` e `ferramentas/`, dados em `projects/`).

Este arquivo explica **como registrar cada coisa no canvas** para a linhagem aparecer certa. Para implementar um vídeo
como HTML, depois de ler isto, siga [docs/AGENTES.md](docs/AGENTES.md).

## 1. O modelo em um minuto

- **Projeto** (`projects/<slug>/`): tem um prefixo (ex.: `JAR`) e uma árvore de nós.
- **Nó**: um JSON em `projects/<slug>/nodes/<CÓDIGO>.json`. O código (`JAR-042`) é dado uma vez e nunca é reaproveitado.
  Clicar num código no app copia-o para citar no chat.
- **Linhagem**: todo nó sai de um pai, e o app desenha a árvore a partir disso. Entre um nó e o que sai dele há sempre um
  **pedido**, que guarda o que foi pedido, as entradas e o custo.
- **Ninguém escreve em `nodes/` à mão.** Use os comandos abaixo: eles passam pela trava do projeto (o app escreve ao mesmo
  tempo) e mantêm a linhagem.

| Tipo | O que é | Arquivo |
|---|---|---|
| `brief`, `tela` | o começo do projeto e as telas que ele pede | — |
| `pedido` | o que se pediu, com as `entradas` (a 1ª define o pai) e as `saidas` | — |
| `imagem` | uma imagem gerada (tela, variação, ou asset tirado de um vídeo) | `images/<CÓD>.png` |
| `referencia` | uma imagem colada pelo usuário | `refs/<CÓD>.*` |
| `video` | um vídeo gerado a partir de uma imagem | `videos/<CÓD>.mp4` |
| `modelo` | um modelo 3D gerado a partir de uma imagem | `models/<CÓD>.glb` (capa em `thumbs/`) |

As **páginas** (HTML) não são nós: são pastas `projects/<slug>/impl/<IMAGEM>/vN/` com um `impl.json`. O app as desenha
na página de desenvolvimento da imagem (o 🔥), ligadas ao que as originou.

Contrato completo dos nós: [.claude/skills/neo-stitch/modelo.md](.claude/skills/neo-stitch/modelo.md).

## 2. A cadeia completa

```
brief → tela → pedido → IMAGEM ─→ pedido de vídeo → VÍDEO ─┬→ pedido de assets → IMAGEM (placa de fundo)  ─────────────┐
                                                           └→ pedido de assets → IMAGEM (personagem limpo)            │
                                                                                     └→ pedido 3D → MODELO 3D ✓ ─────┴→ PÁGINA (impl vN)
                                                                                                    MODELO 3D
                                                                                                    MODELO 3D
```

- **Vídeos saem de imagens.** Um pedido de vídeo tem a imagem como 1ª entrada (o quadro inicial) e gera um vídeo por modelo.
- **Imagens tiradas de um vídeo saem do vídeo.** A placa de fundo sem os elementos vivos, o personagem isolado para o 3D:
  cada uma vira um cartão no canvas, num pedido de assets que tem o vídeo como entrada.
- **Modelos 3D saem da imagem que os gerou.** Todos os gerados ficam registrados; o escolhido fica aprovado.
- **A página sai do que ela usa.** Com `entradas` no `impl.json` (o modelo escolhido primeiro, depois as imagens), o app
  pendura a página no modelo, liga as outras entradas por linha cheia e o vídeo por linha pontilhada. Sem `entradas`, a
  página pende do vídeo.

Na página 🔥 da imagem de origem, isso aparece da esquerda para a direita: imagem → vídeos → imagens tiradas do vídeo →
modelos 3D → páginas → evoluções (v1 → v1.1).

## 3. Como registrar cada coisa

Rode tudo na raiz do repositório.

### Uma imagem (gerada)

Pelo app, o usuário cria o pedido e a fila avisa o Claude. Pela linha de comando:

```bash
uv run ferramentas/neo.py pedido jarvisos --entradas JAR-042 --intencao "mais neon" --quantidade 3
uv run ferramentas/gerar.py JAR-0XX --prompt "…" --prompt "…" --prompt "…"     # gera e pendura as imagens
```

As imagens nascem do pedido, que nasce da `JAR-042`. Sem entradas, o pedido pende da tela.

### Um vídeo (de uma imagem)

```bash
uv run ferramentas/neo.py pedido jarvisos --entradas JAR-095 --midia video --modelos alibaba/wan-3.0 --duracao 6 \
  --intencao "o olho respira, os anéis giram"
uv run ferramentas/gerar_video.py JAR-0XX --prompt-arquivo prompt.txt          # um nó de vídeo por modelo
```

A imagem ganha o selo 🔥 (em desenvolvimento). Como escrever o prompt de vídeo: skill `neo-stitch`, seção "acao = video".

### Uma imagem tirada do vídeo (asset de uma implementação)

Toda imagem gerada durante uma implementação é um cartão: a placa de fundo sem os elementos vivos, o personagem isolado
que vai virar 3D, uma textura. Registre assim que ela existir:

```bash
uv run ferramentas/impl.py asset JAR-095/v6 phase1/subject.png --nome "robô limpo" \
  --nota "o robô isolado, fiel ao quadro: entrada do imagem → 3D" --custo 0.02
```

Ela sai do vídeo da versão, num pedido de assets próprio da versão.

### Um modelo 3D (de uma imagem)

Registre **todos** os modelos gerados, cada um com um render no ângulo do quadro como capa, e marque o escolhido:

```bash
uv run ferramentas/impl.py asset JAR-022/v1 phase1/models/tripo.glb --nome "Tripo H3.1" --de JAR-181 \
  --capa phase1/models/tripo-yaw.png --giro -90 --custo 0.40 --estado aprovada
```

- `--de`: a imagem de onde o modelo foi gerado (normalmente o personagem limpo do passo anterior).
- `--capa`: um PNG renderizado do modelo (com a skill `video2html`: `render_views.py … --yaw`).
- `--giro`: graus para o modelo ficar de frente no visualizador, quando ele vem com a frente em outro eixo.

No canvas, o cartão mostra a capa; clicar abre o modelo em 3D, girando (`/modelo.html`).

### Uma página (HTML vivo de um vídeo)

```bash
uv run ferramentas/impl.py iniciar JAR-154 --agente "Codex 5.6"          # reserva a próxima vN da imagem de origem
uv run ferramentas/impl.py etapa JAR-095/v6 "fase 2: componentes" --progresso 0.6
uv run ferramentas/impl.py pronto JAR-095/v6 --nota "o que a página faz"
uv run ferramentas/impl.py evoluir JAR-095/v6 --agente "Codex 5.6" --pedido "a alteração pedida"   # v6 → v6.1
```

Para a página sair do modelo e das imagens que ela usa, ponha no `impl.json` (o app lê sozinho):

```json
"entradas": ["JAR-189", "JAR-180"]
```

O passo a passo completo, o contrato `impl.json` e o padrão de qualidade estão em [docs/AGENTES.md](docs/AGENTES.md).

## 4. Regras

- Conteúdo em português (PT-BR).
- **Nunca apague** imagens, vídeos, modelos, nós ou versões: descarte (estado) ou mova para `projects/<slug>/lixeira/`.
- **Não escreva em `nodes/` à mão.** Os comandos acima existem para isso.
- **Tudo o que custou dinheiro vira nó** (imagem, vídeo, modelo), com `--custo`: o app soma o custo do projeto.
- **O usuário aprova**: estado `aprovada` e `descartada` vêm dele, pelo app ou pelo chat. A exceção é o modelo 3D que você
  escolheu para a página, que você registra já aprovado.
- As chaves (`OPENROUTER_API_KEY`, `FAL_KEY`) vêm de `~/.env`: nunca as imprima nem as commite.

## 5. Onde ler mais

| Para | Leia |
|---|---|
| implementar um vídeo como HTML (qualquer agente) | [docs/AGENTES.md](docs/AGENTES.md) |
| o método de vídeo → HTML (com os scripts de medição) | skill `video2html` (`.claude/skills/video2html/SKILL.md`) |
| operar o canvas (fila, prompts, geração) | skill `neo-stitch` (`.claude/skills/neo-stitch/SKILL.md`) |
| o contrato de cada tipo de nó | [.claude/skills/neo-stitch/modelo.md](.claude/skills/neo-stitch/modelo.md) |
| usar o app (atalhos, páginas, visualizador) | [docs/USO.md](docs/USO.md) |
| decisões e escopo | [specs.md](specs.md) |
