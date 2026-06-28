#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera assets/icon.ico (y icon.png) a partir del logo PNG existente.
Lo usa el pipeline de build antes de electron-builder. Requiere Pillow.
Uso:  python scripts/make_icon.py"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Fuentes candidatas (la primera que exista). El logo amarillo de FI es PNG => rasterizable.
CANDIDATOS = [
    os.path.join(ROOT, "app", "assets", "LOGO-FI-BRUTO-YELLOW.png"),
    os.path.join(ROOT, "assets", "LOGO-FI-BRUTO-YELLOW.png"),
]
SALIDA_ICO = os.path.join(ROOT, "assets", "icon.ico")
SALIDA_PNG = os.path.join(ROOT, "assets", "icon.png")

def cuadrar(img, lado=512, fondo=(28, 32, 38, 0)):
    """Encaja la imagen en un lienzo cuadrado transparente, centrada."""
    img = img.convert("RGBA")
    w, h = img.size
    escala = min(lado / w, lado / h)
    nuevo = (max(1, int(w * escala)), max(1, int(h * escala)))
    img = img.resize(nuevo, Image.LANCZOS)
    lienzo = Image.new("RGBA", (lado, lado), fondo)
    lienzo.paste(img, ((lado - nuevo[0]) // 2, (lado - nuevo[1]) // 2), img)
    return lienzo

def main():
    fuente = next((c for c in CANDIDATOS if os.path.exists(c)), None)
    if not fuente:
        raise SystemExit("No encontré un logo PNG de origen en app/assets/ ni assets/.")
    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    base = cuadrar(Image.open(fuente), 512)
    base.save(SALIDA_PNG, format="PNG")
    base.save(SALIDA_ICO, format="ICO",
              sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"OK  icono generado desde {os.path.relpath(fuente, ROOT)}")
    print(f"    -> {os.path.relpath(SALIDA_ICO, ROOT)}")
    print(f"    -> {os.path.relpath(SALIDA_PNG, ROOT)}")

if __name__ == "__main__":
    main()
