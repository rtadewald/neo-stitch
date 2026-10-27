# video2html (Neo Stitch)

Imagem aprovada + vídeo dela animada → HTML vivo, interativo e **medido**. O método está no [SKILL.md](SKILL.md); de
onde veio cada parte, em [referencias/origem.md](referencias/origem.md).

## Scripts

Rodam da raiz do repositório com `uv run .claude/skills/video2html/scripts/<script>.py` (dependências inline).
Precisam de ffmpeg/ffprobe no PATH e Google Chrome instalado.

| Script | Para quê | Passa quando |
|---|---|---|
| `ler_video.py` | onde, quanto e quando o vídeo mexe: regiões, energia, picos, período, quadros, paleta | (leitura) |
| `descrever_video.py` | o quê e como, pelo Gemini (~$0,01); `--comparar` para vídeo × página | (opinião) |
| `isolar_camada.py` | separa o objeto vivo do fundo: placa + camada escura (multiply) + clara (screen) | recompõe com erro ~0 |
| `limpar_placa.py` | apaga da placa texto (`escuro`), traço do acento (`verde`) ou caixa (`tudo`, com `--grao-de`) | sem mancha nem retângulo |
| `achar_fonte.py` | ranking das Google Fonts para uma linha de texto da imagem (IoU das letras) | (escolha) |
| `calibrar_texto.py` | posição, tamanho e espaçamento de cada texto pela caixa de tinta da imagem | ±1 px |
| `filmar.py` | foto ou vídeo da página com relógio virtual (determinístico) + log do console | sem erro de console |
| `checar.py` | contrato: `vida.ocioso`, `?estatico` congelado, mexe, sem texto cortado, origens | zero falha |
| `comparar_estatico.py` | `?estatico` × imagem: média, grade, deslocamento, piores células | média ≤ 5, célula ≤ 14 |
| `comparar_vida.py` | página × vídeo por região: energia contra o alvo do `vida.json` e textura (borrão/ruído) | nenhuma PARADO/FRACO/ÁSPERO/LISO |

## A régua na AZE-011: v1 (sem método) × v2 (com a skill)

```
                   v1                                   v2
checar             3 falhas                             passou
comparar_estatico  12,82/255                            1,89/255 (0,11 fora dos textos, fontes da marca)
comparar_vida      0,10x · 20 de 20 regiões PARADO      0,89x · todas OK · textura 0,80 a 1,25x
```

Detalhe, rodadas e o que ficou de fora: `projects/azeo/impl/AZE-011/v2/README.md`.
