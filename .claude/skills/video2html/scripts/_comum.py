"""Peças comuns dos scripts da video2html: ffmpeg, leitura de quadros, chave do OpenRouter, saída UTF-8.

Cada script declara as próprias dependências (cabeçalho `# /// script`) e roda com `uv run`. O `uv run` põe a pasta do
script no sys.path, então `import _comum` funciona de qualquer lugar.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# no Windows o console sai em cp1252 e derruba prints com → e acentos fora do latin-1
for _s in (sys.stdout, sys.stderr):
    try:
        if _s and (_s.encoding or '').lower() not in ('utf-8', 'utf8'):
            _s.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass

PASTA_SCRIPTS = Path(__file__).resolve().parent
ANALISE = (480, 270)  # resolução de análise de movimento (16:9)


def exigir(*programas: str) -> None:
    faltam = [p for p in programas if not shutil.which(p)]
    if faltam:
        sys.exit(f'ERRO: falta no PATH: {", ".join(faltam)} (Windows: winget install Gyan.FFmpeg)')


def ffmpeg(*args: str) -> None:
    exigir('ffmpeg')
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', *args], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'ERRO no ffmpeg: {r.stderr.strip()[-800:]}')


def info_video(video: Path) -> dict:
    exigir('ffprobe')
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                        'stream=width,height,r_frame_rate:format=duration', '-of', 'json', str(video)],
                       capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    s = d['streams'][0]
    num, den = s['r_frame_rate'].split('/')
    return {'largura': int(s['width']), 'altura': int(s['height']), 'fps': float(num) / float(den or 1),
            'duracao': float(d['format']['duration'])}


def ler_quadros(video: Path, tamanho: tuple[int, int] = ANALISE, fps: float | None = None,
                ate: float | None = None) -> np.ndarray:
    """Todos os quadros do vídeo como array (T, H, W, 3) uint8, já redimensionados."""
    import numpy as np
    exigir('ffmpeg')
    w, h = tamanho
    filtro = f'scale={w}:{h}:flags=area' + (f',fps={fps}' if fps else '')
    cmd = ['ffmpeg', '-v', 'error', '-i', str(video)]
    if ate:
        cmd += ['-t', f'{ate:.3f}']
    cmd += ['-vf', filtro, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    bruto = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(bruto, np.uint8).reshape(-1, h, w, 3)


def luminancia(q: np.ndarray) -> np.ndarray:
    import numpy as np
    q = q.astype(np.float32)
    return q[..., 0] * 0.299 + q[..., 1] * 0.587 + q[..., 2] * 0.114


def energia_por_pixel(quadros: np.ndarray) -> tuple[np.ndarray, float]:
    """Desvio temporal da luminância por pixel, menos o piso de ruído (o chiado de compressão do vídeo gerado).
    Devolve (mapa, piso). O mapa está em níveis de 0 a 255."""
    import numpy as np
    lum = luminancia(quadros)
    desvio = lum.std(axis=0)
    piso = float(np.percentile(desvio, 50))
    return np.clip(desvio - piso, 0, None), piso


def chave_openrouter() -> str:
    if os.environ.get('OPENROUTER_API_KEY'):
        return os.environ['OPENROUTER_API_KEY']
    candidatos = [p / '.env' for p in [Path.cwd(), *Path.cwd().parents]] + [Path.home() / '.env']
    for env in candidatos:
        if env.is_file():
            for linha in env.read_text(encoding='utf-8', errors='ignore').splitlines():
                if linha.strip().startswith('OPENROUTER_API_KEY='):
                    return linha.split('=', 1)[1].strip().strip('"\'')
    sys.exit('ERRO: defina OPENROUTER_API_KEY (ambiente, .env do projeto ou ~/.env).')


def gravar_json(caminho: Path, dados) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding='utf-8')


def ler_json(caminho: Path | None, padrao=None):
    if not caminho or not Path(caminho).is_file():
        return padrao
    return json.loads(Path(caminho).read_text(encoding='utf-8'))
