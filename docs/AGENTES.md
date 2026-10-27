# Vídeo → HTML por qualquer agente

Esta é a spec para um agente de código (Claude Code, Codex, OpenCode, Gemini CLI…) transformar um vídeo do Neo Stitch num
**HTML vivo e interativo**, e para o app mostrar, em tempo real, **quem está trabalhando em qual versão e em que pé está**.
Vários agentes podem trabalhar no mesmo vídeo ao mesmo tempo: cada um ganha a sua versão (`v4`, `v5`…), e o canvas de
expansão mostra todas lado a lado.

O contrato é um arquivo: `projects/<projeto>/impl/<IMAGEM>/vN/impl.json`. O comando `ferramentas/impl.py` escreve esse
arquivo do jeito certo. Use o comando; escreva o JSON à mão só se não puder rodar `uv`.

## 1. Comece

Você recebe o código de um vídeo (ex.: `JAR-142`, copiado do app). Na raiz do repositório:

```bash
uv run ferramentas/impl.py iniciar JAR-142 --agente "Codex 5.6"
```

Isso reserva a próxima versão da imagem de onde o vídeo saiu (ex.: `JAR-043/v4`) e prepara a pasta:

- `reference.png`: a imagem aprovada. **É o conteúdo**: textos, layout, componentes.
- `analise/video-ref.mp4`: o vídeo. **É o movimento**: o que respira, acende, gira. Inspiração, não especificação.
- `impl.json`: a sua ficha, já com `status: "trabalhando"`.

O cartão da versão aparece na hora no app, com o seu nome.

**O nome do agente** é curto, até 24 caracteres: a ferramenta ou o modelo e a versão. Exemplos: `Codex 5.6`,
`Claude Opus 5.5`, `OpenCode Kimi K3`, `Gemini 3.1`. Use sempre o mesmo nome para o mesmo agente.

## 2. Trabalhe só dentro da sua pasta

- Entregável: `index.html` + `assets/` (CSS, JS, imagens) com caminhos relativos. Abre em
  `http://localhost:8730/projects/<projeto>/impl/<IMAGEM>/vN/index.html` (o servidor do Neo Stitch serve a pasta).
- Bibliotecas por CDN com versão fixa (ex.: `three@0.170.0`, `gsap@3.13.0`).
- Escreva um `README.md` na pasta: o que vive, como foi feito, o que ficou de fora e por quê.
- **Toda imagem que você gerar no trabalho é um asset do projeto** (placa de fundo sem os elementos vivos, personagem limpo
  para o 3D, textura): registre no canvas, saindo do vídeo, com
  `uv run ferramentas/impl.py asset <IMAGEM/vN> <arquivo.png> --nome "…" --nota "para que serve" --custo 0.04`.
- **Modelos 3D também** (todos os gerados, com o escolhido aprovado): saem da imagem que os gerou, com um render como capa:
  `uv run ferramentas/impl.py asset <IMAGEM/vN> <modelo.glb> --nome "…" --de <imagem> --capa <render.png> [--giro -90] --custo 0.40 [--estado aprovada]`.
  No `impl.json`, ponha o modelo escolhido em `entradas` (primeiro), para a página sair dele no app.
- Não mexa em outras versões, em `nodes/` nem nos arquivos do app. Não apague nada.

## 3. Reporte o andamento

A cada etapa, e **pelo menos a cada 10 minutos** (sem atualizar por 15 min, o app mostra "parado?"):

```bash
uv run ferramentas/impl.py etapa JAR-043/v4 "fase de vida: esfera em WebGL" --progresso 0.6
uv run ferramentas/impl.py vivo JAR-043/v4        # só o sinal de vida, sem mudar a etapa
```

Etapas sugeridas (o texto é livre, curto, em português):

1. lendo o vídeo e a imagem: 0.1
2. estrutura estática (layout, textos, componentes fiéis à imagem): 0.3
3. assets (placas de fundo, recortes): 0.45
4. vida (o ocioso do vídeo em código): 0.65
5. interações (cursor, cliques, o chat responde): 0.85
6. verificação (abrir, gravar, comparar com o vídeo): 0.95

## 4. Termine

```bash
uv run ferramentas/impl.py pronto JAR-043/v4 --nota "esfera em Three.js, feixes em SVG, chat responde"
uv run ferramentas/impl.py erro JAR-043/v4 "não consegui recortar o personagem"
uv run ferramentas/impl.py abandonar JAR-043/v4 --nota "outra abordagem na v5"
```

`pronto` exige o `index.html`. Depois dele, o cartão passa a rodar o HTML.

`uv run ferramentas/impl.py ver` lista quem está trabalhando em quê.

## 5. Alterações pedidas: evoluções (v1.1, v1.2…)

Quando pedirem uma mudança numa versão que já existe, **não mexa nela**. Crie a evolução:

```bash
uv run ferramentas/impl.py evoluir JAR-095/v1 --agente "Codex 5.6" --pedido "o robô sempre olha para o cursor"
```

- Isso copia a `v1` para a próxima `v1.N` livre (`v1.1`, depois `v1.2`…), sem `verificacao/`, e grava no `impl.json` a `base`
  (`v1`) e o `pedido` (o texto da alteração, nas palavras de quem pediu).
- Evoluir uma `v1.1` gera a `v1.2`: a linha continua na mesma versão principal. Uma abordagem nova do zero é outra versão
  principal (`iniciar` → `v2`).
- Trabalhe só na pasta nova, reporte com `etapa` e termine com `pronto --nota "o que mudou"`. No `README.md`, acrescente uma
  seção "vN.M — <a mudança>" no topo, com o que mudou e a prova.
- No app, a evolução pende da versão de onde saiu (linha tracejada). **Quem aprova é o usuário**, no próprio cartão
  (✓ aprovar · ✕ descartar). Isso grava `estado` no `impl.json`; o agente não escreve esse campo.

## 6. O contrato: impl.json

```json
{
  "agente": "Codex 5.6",
  "video": "JAR-142",
  "imagem": "JAR-043",
  "versao": "v4",
  "status": "trabalhando",
  "etapa": "fase de vida: esfera em WebGL",
  "progresso": 0.6,
  "inicio": "2026-10-24T19:40:00",
  "atualizado": "2026-10-24T20:05:12",
  "fim": null,
  "nota": "",
  "erro": null,
  "base": null,
  "pedido": null,
  "estado": "neutra"
}
```

- `status`: `trabalhando` → `pronto` | `erro` | `abandonado`.
- `entradas` (opcional): o que a página usa, registrado com `impl.py asset`: o modelo 3D escolhido primeiro, depois as
  imagens (ex.: `["JAR-189", "JAR-180"]`). O app pendura a versão na 1ª, liga as outras por linha cheia e o vídeo por linha
  pontilhada. Sem `entradas`, a versão pende do vídeo. A visão geral da linhagem está no [AGENTS.md](../AGENTS.md).
- `base` e `pedido`: só nas evoluções (ex.: `"v1"` e a alteração pedida). `estado` (`neutra` · `aprovada` · `descartada`): só o app escreve.
- `progresso`: de 0 a 1. `atualizado`: hora local ISO, a cada escrita.
- Quem escreve é o agente. O app só lê, e recarrega sozinho quando o arquivo muda.
- Escrevendo à mão: grave num arquivo temporário e renomeie por cima (escrita atômica). A pasta nova é sempre a próxima `vN`
  livre da imagem: crie-a com `mkdir` sem `-p`, e se já existir, tente a seguinte.

## 7. O que é um bom resultado

O alvo é uma página que **responde a tudo**, no nível do
[Auralis](https://ds.asimov.academy/design-systems/auralis-design-system/design-system.html) e do
[New Era](https://ds.asimov.academy/design-systems/new-era-design-system/design-system.html): abra e interaja com elas antes de começar.

- **O conteúdo vem da imagem; o movimento vem do vídeo.** Textos e layout fiéis à `reference.png`. O que o vídeo inventa
  (texto que derrete, rótulo que muda, relógio que deforma) não entra.
- **Tudo que se mexe é código** (CSS, SVG, Canvas, Three.js, shaders, GSAP). Vídeo nunca vira asset. Imagens estáticas
  geradas (placas de fundo, texturas) podem.
- **Vá além do vídeo.** Cada componente importante reage ao cursor e às ações (o chat responde, o agente citado acende, o
  personagem olha para o mouse), e o ocioso do vídeo vira uma função que a interação também chama.
- Desempenho e acessibilidade não são prioridade agora.

O método completo, com os scripts que medem a fidelidade e o movimento, está na skill
[`video2html`](../.claude/skills/video2html/SKILL.md). Qualquer agente pode ler o SKILL.md e rodar os scripts dela
(`uv run .claude/skills/video2html/scripts/…`); quem não puder segue ao menos esta seção.

## 8. Como aparece no app

Na página de expansão da imagem (o 🔥), a versão aparece pendurada no que a originou (o modelo 3D ou a imagem de
`entradas`, ou o vídeo):

- **trabalhando:** o cartão mostra o nome do agente, a etapa e a barra de progresso; sem atualizar há mais de 15 min, "parado?";
- **pronto:** o HTML roda no cartão, com o nome do agente na legenda; clicar abre a versão interativa; ✓ e ✕ aprovam ou descartam;
- **evolução:** pende da versão-base por uma linha tracejada (v1 → v1.1 → v1.2);
- **erro / abandonado:** o cartão fica apagado, com o motivo.

## Instrução para colar num agente

```text
No repositório do Neo Stitch (/Users/rtadewald/Projetos Locais/Tools/21-neo-stitch), leia docs/AGENTES.md e
implemente o vídeo JAR-142 como HTML vivo. Seu nome de agente: "Codex 5.6".
```
