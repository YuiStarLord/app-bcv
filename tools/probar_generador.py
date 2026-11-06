"""Prueba del compositor puro Python: escribe muestras en /tmp y las valida.

Uso (desktop): PYTHONPATH=<venv site-packages> <venv>/bin/python tools/probar_generador.py
PIL se usa SOLO para validar el PNG final; el compositor no lo necesita.
"""

import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import generador_imagen

CASOS = [
    ("muestra_tasa.png", 896.1225, 1004.95657762, 895.12, 1003.40, "13:51"),
    ("muestra_tasa_sin_cambio.png", 896.1225, 1004.95657762, 896.1225, 1004.95657762, "13:51"),
]


def main() -> None:
    for nombre, usd, eur, prev_usd, prev_eur, hora in CASOS:
        t0 = time.perf_counter()
        png = generador_imagen.generar_imagen_tasa(usd, eur, prev_usd, prev_eur, hora)
        dt = time.perf_counter() - t0
        ruta = os.path.join("/tmp", nombre)
        with open(ruta, "wb") as f:
            f.write(png)

        from PIL import Image
        with Image.open(ruta) as im:
            im.load()
            assert im.size == (1080, 1350), f"dimensiones {im.size}"
            assert im.mode == "RGBA", f"modo {im.mode}"
            valido = f"{im.size[0]}x{im.size[1]} {im.mode}"
        print(f"{ruta}: {len(png):,} bytes en {dt*1000:.0f} ms (PNG válido: {valido})")


if __name__ == "__main__":
    main()
