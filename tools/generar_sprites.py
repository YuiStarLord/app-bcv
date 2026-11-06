"""Genera los assets de assets_share/ para el compositor puro Python.

SOLO desktop: necesita Pillow (no hay ruedas Android). Uso:
    PYTHONPATH=<venv site-packages> <venv>/bin/python tools/generar_sprites.py

Produce, junto a main.py:
  assets_share/fondo.png      fondo 1080x1350 RGBA con texto estático horneado
  assets_share/hoja_*.png     hojas de glifos blancos antialiaseados
  assets_share/hoja_*.json    métricas por glifo (x, y, w, h, dx, dy, avance)
  assets_share/layout.json    hueco del hora del footer (texto dinámico)
"""

import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import generador_imagen as gi  # constantes de layout + escritor PNG puro

FUENTE = os.path.join(RAIZ, "tools", "fonts", "Inter.ttf")
DESTINO = os.path.join(RAIZ, "assets_share")

CARACTERES = (
    "0123456789"
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "áéíóúñüÁÉÍÓÚÑ"
    ".,:·$€()+-▲▼%/ "
)

HOJAS = {
    "peque": (27, "Regular"),   # fecha y hora del footer
    "media": (44, "SemiBold"),  # "Bs."
    "grande": (118, "Bold"),    # cifras de tasa
    "chip": (30, "SemiBold"),   # texto de variación
}

NAVY = (0x12, 0x19, 0x4B)
PURPLE = (0x45, 0x25, 0x8F)
GLOW = (0x8E, 0x6B, 0xFF)


def _fuente(tam: int, instancia: str) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(FUENTE, tam)
    f.set_variation_by_name(instancia)
    return f


def _texto_con_tracking(draw, xy, texto, fuente, fill, tracking=0):
    x, y = xy
    for ch in texto:
        draw.text((x, y), ch, font=fuente, fill=fill, anchor="ls")
        x += fuente.getlength(ch) + tracking


def _generar_hoja(nombre: str, tam: int, instancia: str) -> None:
    f = _fuente(tam, instancia)
    asc, desc = f.getmetrics()
    baseline_hoja = asc + 2
    pad = 2

    # Cada glifo se dibuja en su propia celda (sin bearings negativos en crops)
    # y las celdas se pegan en fila única sobre la hoja.
    glifos, celdas = {}, []
    pen = 0
    for ch in CARACTERES:
        avance = int(round(f.getlength(ch)))
        if ch == " ":
            glifos[ch] = {"x": 0, "y": 0, "w": 0, "h": 0, "dx": 0, "dy": 0, "avance": avance}
            pen += avance + 10
            continue
        x0, y0, x1, y1 = f.getbbox(ch, anchor="ls")
        if x1 <= x0 or y1 <= y0:
            raise SystemExit(f"glifo vacío o ausente en Inter {instancia}: {ch!r}")
        cx0, cy0 = int(x0) - pad, int(y0) - pad
        cw = int(math.ceil(x1)) + pad - cx0
        chh = int(math.ceil(y1)) + pad - cy0
        cell = Image.new("RGBA", (cw, chh), (0, 0, 0, 0))
        ImageDraw.Draw(cell).text((-cx0, -cy0), ch, font=f,
                                  fill=(255, 255, 255, 255), anchor="ls")
        glifos[ch] = {
            "x": pen, "y": baseline_hoja + cy0,
            "w": cw, "h": chh, "dx": cx0, "dy": cy0, "avance": avance,
        }
        celdas.append((cell, pen, baseline_hoja + cy0))
        pen += cw + 10

    alto_hoja = asc + desc + 4
    hoja = Image.new("RGBA", (pen, alto_hoja), (0, 0, 0, 0))
    for cell, x, y in celdas:
        hoja.paste(cell, (x, y))

    with open(os.path.join(DESTINO, f"hoja_{nombre}.png"), "wb") as f_out:
        f_out.write(gi.escribir_png(hoja.width, alto_hoja, hoja.tobytes()))
    with open(os.path.join(DESTINO, f"hoja_{nombre}.json"), "w", encoding="utf-8") as f_out:
        json.dump({"tam": tam, "instancia": instancia, "glifos": glifos}, f_out)
    print(f"hoja_{nombre}: {hoja.width}x{alto_hoja}px, {len(glifos)} glifos")


def _generar_fondo() -> None:
    w, h = gi.ANCHO, gi.ALTO

    # Gradiente vertical navy -> morado (1px de alto, estirado).
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / (h - 1)
        grad.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(NAVY, PURPLE)))
    base = grad.resize((w, h)).convert("RGBA")

    # Glow radial suave arriba-izquierda (#8E6BFF ~18%).
    gs = 12
    glow = Image.new("L", (w // gs, h // gs), 0)
    for yy in range(glow.height):
        for xx in range(glow.width):
            dx = (xx * gs + gs / 2 - 200) / 660
            dy = (yy * gs + gs / 2 - 150) / 660
            d = math.hypot(dx, dy)
            v = max(0.0, 1.0 - d)
            glow.putpixel((xx, yy), int(v * v * 46))
    base.paste(Image.new("RGB", (w, h), GLOW), (0, 0), glow.resize((w, h), Image.BICUBIC))

    # Arcos decorativos finos (blanco 4-8%).
    deco = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(deco)
    d.ellipse((475, -315, 1275, 485), outline=(255, 255, 255, 20), width=3)
    d.ellipse((-440, 830, 320, 1590), outline=(255, 255, 255, 16), width=3)
    d.ellipse((860, 460, 1460, 1060), outline=(255, 255, 255, 10), width=2)
    base = Image.alpha_composite(base, deco)

    # Todo el texto estático y el separador se hornean en un overlay RGBA que
    # se funde con alpha_composite: así el RGB queda pre-mezclado contra el
    # gradiente y el putalpha posterior solo recorta las esquinas.
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    # Separador fino entre bloques USD y EUR (blanco 10%).
    sep = Image.new("RGBA", (984 - gi.MARGEN, 2), (255, 255, 255, 26))
    overlay.paste(sep, (gi.MARGEN, 728))

    # Header estático.
    draw = ImageDraw.Draw(overlay)
    cfg = gi.LAYOUT["marca"]
    draw.text((cfg["x"], cfg["baseline"]), "ScrapBCV",
              font=_fuente(58, "ExtraBold"), fill=(255, 255, 255, 255), anchor="ls")
    cfg = gi.LAYOUT["subtitulo"]
    _texto_con_tracking(draw, (cfg["x"], cfg["baseline"]), "TASAS OFICIALES · BCV",
                        _fuente(25, "Medium"), (255, 255, 255, 166), cfg["tracking"])

    # Labels de bloque.
    for clave, texto in (("usd", "DÓLAR ($)"), ("eur", "EURO (€)")):
        cfg = gi.LAYOUT[clave]
        _texto_con_tracking(draw, (cfg["num_x"], cfg["num_baseline"] - 162), texto,
                            _fuente(30, "SemiBold"), (255, 255, 255, 178), 2)

    # Footer estático con hueco para la hora dinámica.
    cfg = gi.LAYOUT["footer"]
    medio = _fuente(26, "Medium")
    x_pen = float(cfg["x"])
    draw.text((x_pen, cfg["baseline"]), "Actualizado", font=medio,
              fill=(255, 255, 255, cfg["opacidad"]), anchor="ls")
    x_pen += medio.getlength("Actualizado") + cfg["gap"]
    slot_w = int(math.ceil(medio.getlength("88:88"))) + 6
    draw.text((x_pen + slot_w + cfg["gap"], cfg["baseline"]), "· vía ScrapBCV",
              font=medio, fill=(255, 255, 255, cfg["opacidad"]), anchor="ls")

    base = Image.alpha_composite(base, overlay)

    # Esquinas redondeadas: alfa 0 fuera, RGB a 0 en la zona transparente.
    mascara = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, w - 1, h - 1), radius=gi.RADIO, fill=255)
    base.putalpha(mascara)
    px = base.load()
    lado = gi.RADIO + 2
    for cx0, cy0 in ((0, 0), (w - lado, 0), (0, h - lado), (w - lado, h - lado)):
        for yy in range(cy0, cy0 + lado):
            for xx in range(cx0, cx0 + lado):
                if px[xx, yy][3] == 0:
                    px[xx, yy] = (0, 0, 0, 0)

    with open(os.path.join(DESTINO, "fondo.png"), "wb") as f_out:
        f_out.write(gi.escribir_png(w, h, base.tobytes()))
    with open(os.path.join(DESTINO, "layout.json"), "w", encoding="utf-8") as f_out:
        json.dump({"footer": {"x0": int(x_pen), "x1": int(x_pen + slot_w),
                              "baseline": cfg["baseline"]}}, f_out)
    print(f"fondo: {w}x{h}px; hueco hora x=[{int(x_pen)}, {int(x_pen + slot_w)}]")


def main() -> None:
    os.makedirs(DESTINO, exist_ok=True)
    for nombre, (tam, instancia) in HOJAS.items():
        _generar_hoja(nombre, tam, instancia)
    _generar_fondo()
    print("assets listos en", DESTINO)


if __name__ == "__main__":
    main()
