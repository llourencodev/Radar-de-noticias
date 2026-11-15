"""Gera o ícone do app a partir do símbolo do site (web/index.html): radar azul em círculo escuro."""
# Uso (na pasta mobile/): python tool/gerar_icone.py android/app/src/main/res icone-512.png
import os, sys
from PIL import Image, ImageDraw
RES = sys.argv[1]
BG = (15, 23, 42, 255)      # #0f172a
FG = (56, 189, 248, 255)    # #38bdf8
S = 2048

def radar(size_vb, scale_px, offset, d):
    # coordenadas do SVG (viewBox 32): anel r=9 (traço 2), linha 16,16 -> 26,9 (traço 2.5), ponto r=2.5
    k = scale_px / size_vb
    cx = cy = offset + 16 * k
    r, w = 9 * k, 2 * k
    d.ellipse([cx - r - w/2, cy - r - w/2, cx + r + w/2, cy + r + w/2], outline=FG, width=round(w))
    d.line([cx, cy, offset + 26 * k, offset + 9 * k], fill=FG, width=round(2.5 * k))
    e = 1.25 * k  # ponta arredondada
    x2, y2 = offset + 26 * k, offset + 9 * k
    d.ellipse([x2 - e, y2 - e, x2 + e, y2 + e], fill=FG)
    p = 2.5 * k
    d.ellipse([cx - p, cy - p, cx + p, cy + p], fill=FG)

# ícone clássico: círculo escuro r=14 de 16
legacy = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(legacy)
k = S / 32
d.ellipse([2 * k, 2 * k, 30 * k, 30 * k], fill=BG)
radar(32, S, 0, d)

# ícone adaptável (Android 8+): fundo sólido + radar dentro da área segura (66 de 108)
fg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
inner = S * 60 / 108          # o desenho (viewBox 32, anel ~ 20 de 32) cabe com folga no círculo seguro
radar(32, inner * 32 / 22, (S - inner * 32 / 22) / 2, ImageDraw.Draw(fg))

legacy_sizes = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
for dens, px in legacy_sizes.items():
    legacy.resize((px, px), Image.LANCZOS).save(f"{RES}/mipmap-{dens}/ic_launcher.png")
    fg.resize((px * 9 // 4, px * 9 // 4), Image.LANCZOS).save(f"{RES}/mipmap-{dens}/ic_launcher_foreground.png")
legacy.resize((512, 512), Image.LANCZOS).save(sys.argv[2])
