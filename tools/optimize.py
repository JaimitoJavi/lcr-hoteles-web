#!/usr/bin/env python3
"""Optimiza las imágenes de public/img (requiere Pillow: pip install pillow).

- Recomprime los originales de más de 200 KB si así pesan al menos un 10 % menos.
- Crea versiones pequeñas (640 y 1000 px de ancho) en public/img/r/ para servir menos peso en móvil.
- Escribe content/img_sizes.json (ancho, alto y versiones) que usa build.py para srcset, width y height.
Uso:  python3 tools/optimize.py
"""
import json, os, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "public", "img"); R = os.path.join(IMG, "r")
os.makedirs(R, exist_ok=True)
sizes, saved, before, after = {}, 0, 0, 0
for f in sorted(os.listdir(IMG)):
    p = os.path.join(IMG, f)
    if not f.endswith(".webp") or not os.path.isfile(p): continue
    im = Image.open(p); w, h = im.size
    size0 = os.path.getsize(p); before += size0
    if size0 > 200_000:
        tmp = p + ".tmp"; im.save(tmp, "WEBP", quality=78, method=6)
        if os.path.getsize(tmp) < size0 * 0.9: os.replace(tmp, p); saved += size0 - os.path.getsize(p)
        else: os.remove(tmp)
    vs = []
    for tw in (640, 1000):
        if w > tw * 1.15:
            out = os.path.join(R, f"{f[:-5]}-w{tw}.webp")
            th = round(h * tw / w)
            im.resize((tw, th), Image.LANCZOS).save(out, "WEBP", quality=72, method=6)
            vs.append(tw)
    sizes[f] = {"w": w, "h": h, "v": vs}
    after += os.path.getsize(p)
json.dump(sizes, open(os.path.join(ROOT, "content", "img_sizes.json"), "w"), indent=0)
print(f"originales: {before/1e6:.1f} MB -> {after/1e6:.1f} MB (ahorro {saved/1e6:.1f} MB); variantes en public/img/r: {sum(len(v['v']) for v in sizes.values())}")
