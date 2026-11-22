# Contrato dos nós (projects/<slug>/nodes/<CÓDIGO>.json)

Todo nó tem: `id` (código `PRE-NNN`, dado uma vez e nunca reaproveitado), `tipo`, `criado`, `atualizado`,
`pos` ({x, y} ou `null` = o app posiciona perto da origem e grava), `comentarios` ([{id, autor: voce|claude, texto,
pin: {x, y} de 0 a 1 ou null, criado}]). `legado: true` = importado (não conta no custo do dia).

| tipo | campos próprios |
|------|-----------------|
| `brief` | `titulo`, `status` (rascunho → enviado → trabalhando → proposto), `direcoes` [{nome, tese, ativa}] — o texto longo é `brief.md` |
| `tela` | `titulo`, `pai` (o brief) |
| `pedido` | `tela`, `entradas` [códigos de imagens/referências/vídeos], `intencao`, `literal`, `quantidade`, `modelo`, `aspecto`, `resolucao`, `status` (rascunho · enviado · trabalhando · concluido · erro), `variacoes` [{nome, tese?, prompt?}], `saidas` [códigos], `custo`, `erro`, `enviado_em`, `iniciado_em`, `concluido_em`, `midia` (imagem · video · 3d · ds); se vídeo: `modelos` [ids], `duracao` (s). Pedidos de assets (`impl.py asset`) têm o vídeo na 1ª entrada; pedidos 3D (`midia: 3d`), a imagem de origem; pedidos de design system (`midia: ds`), as páginas de origem (`IMG/vN`) |
| `imagem` | `pedido`, `nome`, `prompt` (o que gerou), `modelo`, `aspecto`, `resolucao`, `estado` (neutra · descartada; o `aprovada` dos nós antigos conta como neutra — o que importa é pinado), `arquivo` (images/…png), `thumb` (thumbs/…jpg), `largura`, `altura`, `custo`, `segundos`, `gerando` (placeholder), `erro`, `asset` (true: imagem gerada durante uma página por `impl.py asset` — placa, personagem limpo, textura —, não uma tela; o filtro do app a mostra em "Assets") |
| `video` | `pedido`, `nome`, `prompt`, `modelo`, `duracao`, `resolucao`, `estado`, `arquivo` (videos/…mp4), `thumb` (capa jpg), `largura`, `altura`, `custo`, `segundos`, `gerando`, `erro`. Pai = o pedido; comentários podem ter `pin.t` (segundo do vídeo) |
| `referencia` | `titulo`, `tela`, `arquivo` (refs/…), `thumb`, `largura`, `altura`, `origem` |
| `modelo` | `pedido`, `nome`, `prompt` (para que serve), `origem` (versão e arquivo de onde veio), `estado`, `arquivo` (models/…glb), `thumb` (render no ângulo do quadro), `largura`, `altura`, `giro` (graus para ficar de frente no visualizador), `custo` |
| `ds` | `pedido` (concluído, `midia: ds`, com as páginas nas `entradas`), `nome`, `prompt`, `origem` (a pasta de onde veio), `estado`, `pagina` (ds/<código>/design-system.html), `arquivo` (a capa), `thumb`, `largura`, `altura`, `custo`. Nasce só por `neo.py ds` |

**Páginas (implementações) não são nós:** são pastas `impl/<IMAGEM>/vN/` com `impl.json` (contrato em `docs/AGENTES.md`).
Campos de linhagem no `impl.json`: `video` (de onde saiu), `entradas` (o modelo 3D e as imagens que a página usa: o app a
pendura na 1ª e liga as outras), `base` (a versão de onde uma evolução saiu), `assets_pedido` e `pedidos_modelo` (os pedidos
que `impl.py asset` criou para as imagens e os modelos da versão).

## Quem escreve o quê

- **App (PATCH):** só `pos`, `titulo`, `estado`, `direcoes` (ligar/desligar), e — enquanto o pedido é rascunho — `intencao`, `literal`,
  `quantidade`, `modelo`, `aspecto`, `resolucao`, `entradas`, `variacoes`, `midia`, `modelos`, `duracao`. Comentários do usuário via rota própria.
- **Claude (neo.py / gerar.py / gerar_video.py):** `status`, `direcoes`, `variacoes` com prompts, imagens, design systems, custos, erros, comentários `claude`.

Toda escrita passa pela trava do projeto (`base.travado`) e por `gravar_json` (temp + rename). Apagar um nó (pelo app,
com confirmação) leva o galho inteiro dele (`base.galho`) num lote para `projects/<slug>/lixeira/<id>-<ts>/`; `POST
…/nos/<id>/restaurar` traz o lote de volta. Nada sai do disco. Descartar (estado) é só uma marcação. O cartão de um design
system só vai para a lixeira com o pedido dele, e a pasta `ds/<código>/` fica onde está.

## Linhagem (a árvore que o app desenha)

O canvas é uma **árvore de ideias** arranjada automaticamente (esquerda → direita, irmãos empilhados, pai centrado):
brief → telas → pedidos → imagens → pedidos → imagens…
- O pai de um pedido é a **imagem ou o vídeo de onde ele saiu** (1ª entrada que é imagem ou vídeo); sem isso, a 1ª
  referência (que pende da tela); sem entradas, a tela. Entradas extras viram arestas tracejadas (recombinação).
- Imagens, vídeos e modelos penduram no pedido que os gerou. A cadeia de uma implementação: imagem → pedido de vídeo →
  vídeo → pedido de assets → assets (imagens com `asset: true`: placa, personagem limpo) → pedido 3D → modelos → (página: o nó de HTML).
- Um design system pendura no pedido dele, que sai da 1ª página de origem; as outras páginas viram arestas tracejadas.
- `recolhido: true` em qualquer nó fecha o galho dele; `escondidos: [ids]` esconde só esses filhos (o ⌘A "só pinados" usa isso). O app mostra "+N" na pílula.
- `desloc: {x, y}` = ajuste manual do usuário sobre a posição automática; vale para o nó e todo o galho dele (arrastar um
  nó leva os filhos junto). `null` volta ao lugar automático. Referências soltas (fora da árvore) usam `pos` absoluta;
  o `pos` dos nós da árvore é ignorado.
