"""Tarjeta de tasa 1080x1350 compuesta en Python puro (stdlib).

Los assets (fondo.png, hojas de glifos, layout.json) viven en assets_share/
junto a este módulo y se generan con tools/generar_sprites.py en desktop.
No depende de Pillow: decodifica PNG (filtro 0) con zlib y compone con
alpha blending por píxel sobre filas bytearray.
"""

import json
import math
import os
import struct
import zlib
from datetime import datetime

ANCHO, ALTO, RADIO = 1080, 1350, 56
MARGEN = 96

BLANCO = (255, 255, 255)
LIMA = (0xD4, 0xFF, 0x4F)
ROJO = (0xFF, 0x6B, 0x6B)

# Ritmo vertical compartido con el generador de sprites (baseline = y de línea base).
LAYOUT = {
    "marca": {"x": 96, "baseline": 132},
    "subtitulo": {"x": 96, "baseline": 186, "tracking": 3},
    "fecha": {"x_derecha": 984, "baseline": 130, "opacidad": 140},
    "usd": {
        "num_x": 96, "num_baseline": 566, "bs_gap": 24,
        "chip_x": 96, "chip_top": 612, "chip_h": 60, "chip_pad": 26,
        "chip_baseline": 41,
    },
    "eur": {
        "num_x": 96, "num_baseline": 974, "bs_gap": 24,
        "chip_x": 96, "chip_top": 1020, "chip_h": 60, "chip_pad": 26,
        "chip_baseline": 41,
    },
    "footer": {"x": 96, "baseline": 1272, "opacidad": 115, "gap": 10},
}

_DIR_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets_share")

_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

_hojas = {}
_layout = None


def formatear_es_ve(valor: float, decimales: int = 2) -> str:
    """Formato es-VE: miles con "." y decimales con "," (igual que la app)."""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "@").replace(".", ",").replace("@", ".")


# ---------------------------------------------------------------- PNG puro

def _chunk(tipo: bytes, cuerpo: bytes) -> bytes:
    return (
        struct.pack(">I", len(cuerpo)) + tipo + cuerpo
        + struct.pack(">I", zlib.crc32(tipo + cuerpo) & 0xFFFFFFFF)
    )


def escribir_png(ancho: int, alto: int, rgba: bytes) -> bytes:
    """Empaqueta RGBA (8 bit, filtro 0) como PNG con IHDR/IDAT/IEND."""
    paso = ancho * 4
    crudo = bytearray(alto * (paso + 1))
    for y in range(alto):
        o = y * (paso + 1)
        crudo[o] = 0
        crudo[o + 1:o + 1 + paso] = rgba[y * paso:(y + 1) * paso]
    return b"".join([
        b"\x89PNG\r\n\x1a\n",
        _chunk(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 6, 0, 0, 0)),
        _chunk(b"IDAT", zlib.compress(bytes(crudo), 9)),
        _chunk(b"IEND", b""),
    ])


def _leer_png(ruta: str):
    """Lee un PNG RGBA 8 bit escrito con filtro 0. Devuelve (ancho, alto, filas)."""
    with open(ruta, "rb") as f:
        datos = f.read()
    if datos[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{ruta}: no es un PNG")
    pos, ihdr, idat = 8, None, []
    while pos + 8 <= len(datos):
        (n,) = struct.unpack_from(">I", datos, pos)
        tipo = datos[pos + 4:pos + 8]
        cuerpo = datos[pos + 8:pos + 8 + n]
        (crc,) = struct.unpack_from(">I", datos, pos + 8 + n)
        if zlib.crc32(tipo + cuerpo) & 0xFFFFFFFF != crc:
            raise ValueError(f"{ruta}: CRC inválido en {tipo!r}")
        if tipo == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", cuerpo)
        elif tipo == b"IDAT":
            idat.append(cuerpo)
        elif tipo == b"IEND":
            break
        pos += 12 + n
    if ihdr is None:
        raise ValueError(f"{ruta}: falta IHDR")
    ancho, alto, prof, ctipo = ihdr[0], ihdr[1], ihdr[2], ihdr[3]
    if prof != 8 or ctipo != 6 or ihdr[6] != 0:
        raise ValueError(f"{ruta}: se espera RGBA 8 bit sin entrelazar")
    bruto = zlib.decompress(b"".join(idat))
    paso = ancho * 4
    if len(bruto) != alto * (paso + 1):
        raise ValueError(f"{ruta}: tamaño de IDAT inesperado")
    filas = bytearray(alto * paso)
    for y in range(alto):
        o = y * (paso + 1)
        if bruto[o] != 0:
            raise ValueError(f"{ruta}: filtro {bruto[o]} en fila {y}; regenera assets")
        filas[y * paso:(y + 1) * paso] = bruto[o + 1:o + 1 + paso]
    return ancho, alto, filas


# ---------------------------------------------------------------- hojas

def cargar_hoja(clave: str) -> dict:
    """Carga hoja_clave.png + .json y devuelve {char: glifo} recortado."""
    hoja = _hojas.get(clave)
    if hoja is not None:
        return hoja
    base = os.path.join(_DIR_ASSETS, f"hoja_{clave}")
    with open(base + ".json", encoding="utf-8") as f:
        meta = json.load(f)
    ancho, _, pix = _leer_png(base + ".png")
    glifos = {}
    for ch, g in meta["glifos"].items():
        cw, chh = g["w"], g["h"]
        if cw:
            datos = bytearray(cw * chh * 4)
            for fila in range(chh):
                o0 = ((g["y"] + fila) * ancho + g["x"]) * 4
                datos[fila * cw * 4:(fila + 1) * cw * 4] = pix[o0:o0 + cw * 4]
        else:
            datos = b""
        glifos[ch] = {
            "avance": g["avance"], "dx": g["dx"], "dy": g["dy"],
            "w": cw, "h": chh, "datos": bytes(datos),
        }
    hoja = {"glifos": glifos}
    _hojas[clave] = hoja
    return hoja


def _cargar_layout() -> dict:
    global _layout
    if _layout is None:
        with open(os.path.join(_DIR_ASSETS, "layout.json"), encoding="utf-8") as f:
            _layout = json.load(f)
    return _layout


# ---------------------------------------------------------------- dibujo

def _pegar(img, ancho_l, alto_l, gpx, gw, gh, dx, dy, tinte, opacidad):
    """Pega un sprite RGBA en (dx, dy) mezclando: bg*(255-a)/255 + fg*a/255."""
    x0, y0 = max(dx, 0), max(dy, 0)
    x1, y1 = min(dx + gw, ancho_l), min(dy + gh, alto_l)
    if x0 >= x1 or y0 >= y1:
        return
    tr, tg, tb = tinte
    for gy in range(y0 - dy, y1 - dy):
        fila_g = gy * gw * 4
        fila_o = ((dy + gy) * ancho_l + dx) * 4
        for gx in range(x0 - dx, x1 - dx):
            a = gpx[fila_g + gx * 4 + 3]
            if a:
                if opacidad != 255:
                    a = (a * opacidad + 127) // 255
                inv = 255 - a
                o = fila_o + gx * 4
                img[o] = (img[o] * inv + tr * a + 127) // 255
                img[o + 1] = (img[o + 1] * inv + tg * a + 127) // 255
                img[o + 2] = (img[o + 2] * inv + tb * a + 127) // 255


def _ancho_texto(hoja, texto, tracking=0):
    total, n = 0, len(texto)
    for i, ch in enumerate(texto):
        g = hoja["glifos"].get(ch)
        if g is None:
            raise ValueError(f"glifo faltante en la hoja: {ch!r}")
        total += g["avance"]
        if i < n - 1:
            total += tracking
    return total


def _dibujar_texto(img, hoja, texto, x, y_base, tinte=BLANCO, opacidad=255, tracking=0):
    """Dibuja texto con pen en x y línea base en y_base. Devuelve la pen final."""
    for ch in texto:
        g = hoja["glifos"].get(ch)
        if g is None:
            raise ValueError(f"glifo faltante en la hoja: {ch!r}")
        if g["w"]:
            _pegar(img, ANCHO, ALTO, g["datos"], g["w"], g["h"],
                   x + g["dx"], y_base + g["dy"], tinte, opacidad)
        x += g["avance"] + tracking
    return x


def _pildora(w, h, radio, alfa_fondo):
    """Sprite alfa de píldora redondeada (solo canal alfa; el tinte lo pone _pegar)."""
    px = bytearray(w * h * 4)
    for yy in range(h):
        dy = max(radio - yy - 0.5, yy + 0.5 - (h - radio), 0.0)
        fila = yy * w * 4
        for xx in range(w):
            ddx = max(radio - xx - 0.5, xx + 0.5 - (w - radio), 0.0)
            d = math.hypot(ddx, dy) - radio
            if d < 0.5:
                cob = max(0.0, min(1.0, 0.5 - d))
                px[fila + xx * 4 + 3] = int(cob * 255) * alfa_fondo // 255
    return bytes(px)


def _bloque_tasa(img, grande, media, chip_hoja, numero, diff, cfg):
    """Número grande + Bs. + chip de variación de un bloque de moneda."""
    _dibujar_texto(img, grande, numero, cfg["num_x"], cfg["num_baseline"], BLANCO, 255)
    x_bs = cfg["num_x"] + _ancho_texto(grande, numero) + cfg["bs_gap"]
    _dibujar_texto(img, media, "Bs.", x_bs, cfg["num_baseline"], BLANCO, 166)
    if abs(diff) > 0.001:
        texto = ("▲ +" if diff > 0 else "▼ -") + formatear_es_ve(abs(diff), 2)
        tinte = ROJO if diff > 0 else LIMA
        w_txt = _ancho_texto(chip_hoja, texto)
        pw, ph = cfg["chip_pad"] * 2 + w_txt, cfg["chip_h"]
        _pegar(img, ANCHO, ALTO, _pildora(pw, ph, ph // 2, 26), pw, ph,
               cfg["chip_x"], cfg["chip_top"], BLANCO, 255)
        _dibujar_texto(img, chip_hoja, texto, cfg["chip_x"] + cfg["chip_pad"],
                       cfg["chip_top"] + cfg["chip_baseline"], tinte, 255)


def _fecha_larga() -> str:
    hoy = datetime.now()
    return f"{_DIAS[hoy.weekday()]} {hoy.day} de {_MESES[hoy.month - 1]} de {hoy.year}"


def generar_imagen_tasa(usd: float, eur: float, prev_usd: float,
                        prev_eur: float, actualizado: str) -> bytes:
    """Compone la tarjeta y devuelve los bytes PNG (RGBA 1080x1350)."""
    _, _, img = _leer_png(os.path.join(_DIR_ASSETS, "fondo.png"))
    peque = cargar_hoja("peque")
    media = cargar_hoja("media")
    grande = cargar_hoja("grande")
    chip_hoja = cargar_hoja("chip")
    layout = _cargar_layout()

    fecha = _fecha_larga()
    cfg_f = LAYOUT["fecha"]
    _dibujar_texto(img, peque, fecha,
                   cfg_f["x_derecha"] - _ancho_texto(peque, fecha),
                   cfg_f["baseline"], BLANCO, cfg_f["opacidad"])

    _bloque_tasa(img, grande, media, chip_hoja,
                 formatear_es_ve(usd, 2), usd - prev_usd, LAYOUT["usd"])
    _bloque_tasa(img, grande, media, chip_hoja,
                 formatear_es_ve(eur, 2), eur - prev_eur, LAYOUT["eur"])

    slot = layout["footer"]
    ancho_hora = _ancho_texto(peque, actualizado)
    _dibujar_texto(img, peque, actualizado,
                   slot["x0"] + (slot["x1"] - slot["x0"] - ancho_hora) // 2,
                   slot["baseline"], BLANCO, LAYOUT["footer"]["opacidad"])

    return escribir_png(ANCHO, ALTO, bytes(img))
