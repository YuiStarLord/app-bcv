"""
ScrapBCV — Tasas oficiales del BCV (Venezuela)
ORIGINAL BY YUISTARLOD
MAINTAINED BY HAKKAYORO
"""

import asyncio
import logging
import math
import os
import re
import sys
import tempfile
import time
from datetime import datetime

import urllib3
import requests
from bs4 import BeautifulSoup

import flet as ft
from flet import (
    Clipboard,
    Share,
    ShareFile,
    SharedPreferences,
    UrlLauncher,
)

import generador_imagen

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# El CI reemplaza este literal con sed; no editar el formato.
APP_VERSION = "v0.0.0-dev"

URL_BCV = "https://www.bcv.org.ve/"
URL_RELEASES = "https://api.github.com/repos/YuiStarLord/app-bcv/releases/latest"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )
}
TIMEOUT_BCV = 10

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("scrapbcv")

_DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
_MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

def parse_es_ve(texto: str) -> float:
    """Parsea números en formato es-VE ("1.006,03" o "894.89")."""
    s = texto.strip()
    if not s:
        raise ValueError("número vacío")
    if "," in s:
        # Coma decimal; los puntos eran separadores de miles.
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s):
        # Solo puntos con patrón de miles ("1.234.567").
        s = s.replace(".", "")
    return float(s)

def formatear_es_ve(valor: float, decimales: int = 2) -> str:
    """Da formato es-VE: miles con "." y decimales con ","."""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "@").replace(".", ",").replace("@", ".")

def aplicar_mascara(texto: str) -> str:
    """Máscara del campo de monto: dígitos escalados a 2 decimales ("0,00")."""
    digitos = re.sub(r"\D", "", texto)
    if not digitos or int(digitos) == 0:
        return "0,00"
    return formatear_es_ve(int(digitos) / 100, 2)

def fecha_hoy_es_ve() -> str:
    hoy = datetime.now()
    return f"{_DIAS[hoy.weekday()]} {hoy.day} {_MESES[hoy.month - 1]} {hoy.year}"

def _extraer_tasa(soup: BeautifulSoup, id_div: str) -> float:
    div = soup.find("div", id=id_div)
    strong = div.find("strong") if div else None
    if strong is None:
        raise ValueError(f"El sitio del BCV cambió de estructura: falta div#{id_div} > strong")
    return parse_es_ve(strong.text)

async def obtener_datos_bcv(prefs: SharedPreferences | None = None):
    """Devuelve (usd, eur, prev_usd, prev_eur, offline) usando caché si hay prefs."""
    # El BCV es caprichoso: un reintento evita falsos offline por picos de red.
    respuesta = None
    for intento in range(2):
        try:
            respuesta = await asyncio.to_thread(
                requests.get, URL_BCV, headers=HEADERS, verify=False, timeout=TIMEOUT_BCV
            )
            break
        except requests.RequestException as exc:
            log.warning("Intento %d falló: %s", intento + 1, exc)
    try:
        if respuesta is None or respuesta.status_code != 200:
            raise RuntimeError(
                f"El BCV no respondió ({respuesta.status_code if respuesta else 'sin conexión'})"
            )
        soup = BeautifulSoup(respuesta.content, "html.parser")
        usd = _extraer_tasa(soup, "dolar")
        eur = _extraer_tasa(soup, "euro")
        log.info("Tasas obtenidas: USD=%s, EUR=%s", usd, eur)

        prev_usd, prev_eur = usd, eur
        if prefs:
            cached_usd = await prefs.get("cached_usd")
            cached_eur = await prefs.get("cached_eur")
            prev_usd = await prefs.get("prev_usd") or cached_usd or usd
            prev_eur = await prefs.get("prev_eur") or cached_eur or eur
            # La caché se escribe SIEMPRE (también en la primera ejecución);
            # la anterior solo se actualiza cuando la tasa cambió.
            if cached_usd is None or usd != float(cached_usd):
                if cached_usd is not None:
                    await prefs.set("prev_usd", str(cached_usd))
                    prev_usd = cached_usd
                await prefs.set("cached_usd", str(usd))
            if cached_eur is None or eur != float(cached_eur):
                if cached_eur is not None:
                    await prefs.set("prev_eur", str(cached_eur))
                    prev_eur = cached_eur
                await prefs.set("cached_eur", str(eur))
            await prefs.set("last_update", time.strftime("%H:%M"))
        return usd, eur, float(prev_usd), float(prev_eur), False
    except Exception as exc:
        log.error("Error al obtener datos del BCV: %s", exc)
        if prefs:
            cached_usd = await prefs.get("cached_usd")
            cached_eur = await prefs.get("cached_eur")
            if cached_usd is not None and cached_eur is not None:
                prev_usd = await prefs.get("prev_usd") or cached_usd
                prev_eur = await prefs.get("prev_eur") or cached_eur
                log.info("Usando datos en caché")
                return float(cached_usd), float(cached_eur), float(prev_usd), float(prev_eur), True
        return 0.0, 0.0, 0.0, 0.0, True

async def main(page: ft.Page):
    page.title = "ScrapBCV"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.theme = ft.Theme(color_scheme_seed="#3F51B5")
    page.dark_theme = ft.Theme(color_scheme_seed="#3F51B5")
    page.padding = 16
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    if page.platform and page.platform.is_desktop():
        page.window.width, page.window.height = 400, 760
        page.window.min_width, page.window.min_height = 350, 600

    prefs = SharedPreferences()
    clipboard = Clipboard()
    share = Share()

    estado = {
        "usd": 0.0, "eur": 0.0, "prev_usd": 0.0, "prev_eur": 0.0,
        "tasa_actual": 0.0, "tasa_anterior": 0.0,
        "modo_inverso": False, "offline": False, "ultima_ref": "?", "tab": 0,
    }

    # ---------- Handlers (antes de la UI que los referencia) ----------

    def calcular_texto() -> str:
        try:
            val = float(txt_monto.value.replace(".", "").replace(",", "."))
        except (ValueError, AttributeError):
            val = 0.0
        simbolo = "$" if estado["tab"] == 0 else "€"
        if estado["modo_inverso"]:
            total = val / estado["tasa_actual"] if estado["tasa_actual"] > 0 else 0.0
            return f"{formatear_es_ve(total)} {simbolo}"
        return f"{formatear_es_ve(val * estado['tasa_actual'])} Bs."

    async def animar_tasa(hasta: float):
        """Odómetro: cuenta desde la tasa mostrada hasta la nueva (ease-out)."""
        desde = estado.get("tasa_mostrada") or 0.0
        if abs(hasta - desde) < 0.005:
            estado["tasa_mostrada"] = hasta
            lbl_tasa.value = f"{formatear_es_ve(hasta)} Bs."
            lbl_tasa.update()
            return
        estado["animacion_id"] = estado.get("animacion_id", 0) + 1
        mi_turno = estado["animacion_id"]
        pasos = 26
        for i in range(1, pasos + 1):
            if estado["animacion_id"] != mi_turno:
                return  # una animación más nueva la relevó
            t = i / pasos
            suave = 1 - (1 - t) ** 3
            lbl_tasa.value = f"{formatear_es_ve(desde + (hasta - desde) * suave)} Bs."
            lbl_tasa.update()
            await asyncio.sleep(0.02)
        estado["tasa_mostrada"] = hasta
        lbl_tasa.value = f"{formatear_es_ve(hasta)} Bs."
        lbl_tasa.update()

    def resultado_texto() -> ft.Text:
        return ft.Text(
            calcular_texto(), size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_600
        )

    def _actualizar_prefijos():
        if estado["modo_inverso"]:
            txt_monto.prefix, lbl_modo.value = "Bs ", "Bolívares → Divisas"
        else:
            txt_monto.prefix = "$ " if estado["tab"] == 0 else "€ "
            lbl_modo.value = "Divisas → Bolívares"

    def al_escribir_monto(_):
        digitos = re.sub(r"\D", "", txt_monto.value or "")
        if not digitos or int(digitos) == 0:
            # Vacío o solo ceros: se deja el placeholder, sin recargar el campo.
            txt_monto.value = ""
            txt_monto.update()
            switcher_res.content = resultado_texto()
            page.update()
            return
        txt_monto.value = aplicar_mascara(txt_monto.value)
        # En dos pasos (verificado): el valor primero y la selección después,
        # o Flutter recoloca el cursor al inicio y cada dígito se antepone.
        txt_monto.update()
        page.update()
        txt_monto.focus()
        fin = len(txt_monto.value)
        txt_monto.selection = ft.TextSelection(base_offset=fin, extent_offset=fin)
        txt_monto.update()
        switcher_res.content = resultado_texto()
        page.update()

    def al_cambiar_tab(indice: int):
        estado["tab"] = indice
        _actualizar_pildora()
        _actualizar_prefijos()
        _aplicar_tasas()

    def invertir_sentido(_):
        estado["modo_inverso"] = not estado["modo_inverso"]
        giro = btn_swap.rotate if isinstance(btn_swap.rotate, (int, float)) else 0
        btn_swap.rotate = giro + math.pi
        _actualizar_prefijos()
        switcher_res.content = resultado_texto()
        page.update()

    async def pegar_monto(_):
        try:
            texto = await clipboard.get()
        except Exception as exc:
            log.error("No se pudo leer el portapapeles: %s", exc)
            return
        if texto:
            digitos = re.sub(r"\D", "", texto)
            txt_monto.value = aplicar_mascara(texto) if digitos and int(digitos) else ""
            txt_monto.update()
            page.update()
            txt_monto.focus()
            fin = len(txt_monto.value)
            txt_monto.selection = ft.TextSelection(base_offset=fin, extent_offset=fin)
            txt_monto.update()
            switcher_res.content = resultado_texto()
            page.update()

    async def copiar_resultado(_):
        try:
            await clipboard.set(switcher_res.content.value)
            _avisar("Resultado copiado")
        except Exception as exc:
            log.error("No se pudo copiar: %s", exc)

    async def compartir_calculo(_):
        moneda = "USD" if estado["tab"] == 0 else "EUR"
        simbolo = "$" if estado["tab"] == 0 else "€"
        texto = (
            f"💸 {txt_monto.value} {simbolo} = {switcher_res.content.value}\n"
            f"📈 Tasa BCV: {formatear_es_ve(estado['tasa_actual'])} Bs/{moneda}\n"
            f"📅 {datetime.now().strftime('%d/%m/%Y')} — vía ScrapBCV"
        )
        try:
            await share.share_text(texto, title="Cálculo BCV · ScrapBCV")
        except Exception as exc:
            log.error("No se pudo compartir el cálculo: %s", exc)
            await clipboard.set(texto)
            _avisar("No se pudo abrir el diálogo de compartir; se copió al portapapeles")

    def _texto_tasa() -> str:
        moneda = "USD" if estado["tab"] == 0 else "EUR"
        return (
            f"📊 Tasa BCV {moneda}: {formatear_es_ve(estado['tasa_actual'])} Bs.\n"
            f"📅 {fecha_hoy_es_ve()} — vía ScrapBCV"
        )

    async def compartir_tasa_imagen(_):
        try:
            log.info("Compartir tasa: generando imagen en segundo plano…")
            png = await asyncio.to_thread(
                generador_imagen.generar_imagen_tasa,
                estado["usd"], estado["eur"],
                estado["prev_usd"], estado["prev_eur"],
                estado["ultima_ref"],
            )
            log.info("Compartir tasa: imagen lista (%d bytes)", len(png))
            base = os.environ.get("FLET_APP_STORAGE_CACHE") or tempfile.gettempdir()
            ruta = os.path.join(base, f"tasa_bcv_{time.strftime('%Y%m%d')}.png")
            with open(ruta, "wb") as f:
                f.write(png)
            log.info("Compartir tasa: abriendo hoja de compartir (%s)", ruta)
            await share.share_files(
                [ShareFile(path=ruta, mime_type="image/png", name=os.path.basename(ruta))],
                text=_texto_tasa(), title="Tasa del día · ScrapBCV",
            )
            log.info("Compartir tasa: hoja cerrada")

        except Exception as exc:
            log.error("No se pudo compartir la imagen: %s", exc)
            try:
                await clipboard.set(_texto_tasa())
                _avisar("No se pudo abrir el diálogo de compartir; se copió al portapapeles")
            except Exception:
                _avisar("No se pudo compartir la tasa")

    def _avisar(mensaje: str):
        page.show_dialog(ft.SnackBar(content=ft.Text(mensaje)))

    def mostrar_creditos(_):
        page.show_dialog(
            ft.AlertDialog(
                title=ft.Text("Créditos"),
                content=ft.Column(
                    [
                        ft.Text("Autor original: YuiStarLord"),
                        ft.Text("Mantenedor: HakkaYoro"),
                        ft.Text(f"Versión: {APP_VERSION}"),
                        ft.Text("Hecho con ❤️ y Flet"),
                    ],
                    tight=True, spacing=10,
                ),
                actions=[ft.TextButton("Cerrar", on_click=lambda _: page.pop_dialog())],
            )
        )

    def _aplicar_tasas():
        indice = estado["tab"]
        estado["tasa_actual"] = estado["usd"] if indice == 0 else estado["eur"]
        estado["tasa_anterior"] = estado["prev_usd"] if indice == 0 else estado["prev_eur"]
        page.run_task(animar_tasa, estado["tasa_actual"])

        diff = estado["tasa_actual"] - estado["tasa_anterior"]
        if abs(diff) > 0.001:
            # Semántica original: rojo si sube (más caro), verde si baja.
            chip_variacion.label = ft.Text(
                f"{'▲' if diff > 0 else '▼'} {'+' if diff > 0 else '-'}{formatear_es_ve(abs(diff))}",
                size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_200 if diff > 0 else ft.Colors.LIME_300,
            )
            chip_variacion.visible = True
        else:
            chip_variacion.visible = False

        punto_estado.bgcolor = "#F44336" if estado["offline"] else "#4CAF50"
        if estado["offline"]:
            txt_estado.value, txt_estado.color = f"Última ref: {estado['ultima_ref']}", ft.Colors.RED_400
            lbl_actualizado.value = "Sin conexión"
        else:
            txt_estado.value, txt_estado.color = "En línea", ft.Colors.GREY_600
            lbl_actualizado.value = f"Actualizado {estado['ultima_ref']}"
        punto_estado.opacity = 1
        switcher_res.content = resultado_texto()
        page.update()

    async def refrescar():
        ring.visible, txt_estado.value = True, "Sincronizando…"
        page.update()
        usd, eur, prev_usd, prev_eur, offline = await obtener_datos_bcv(prefs)
        estado.update(usd=usd, eur=eur, prev_usd=prev_usd, prev_eur=prev_eur, offline=offline)
        estado["ultima_ref"] = (
            await prefs.get("last_update") or "?" if offline else time.strftime("%H:%M")
        )
        ring.visible = False
        _aplicar_tasas()

    async def bucle_reintento():
        while True:
            await asyncio.sleep(30)
            if estado["offline"]:
                log.info("Offline: reintentando conexión…")
                await refrescar()

    async def pulso_estado():
        while True:
            await asyncio.sleep(1)
            if estado["offline"]:
                punto_estado.opacity = 0.3 if punto_estado.opacity == 1 else 1
                page.update()

    async def animar_entrada():
        await asyncio.sleep(0.05)
        tarjeta_hero.opacity, tarjeta_hero.offset = 1, ft.Offset(0, 0)
        page.update()
        await asyncio.sleep(0.12)
        tarjeta_calc.opacity, tarjeta_calc.offset = 1, ft.Offset(0, 0)
        page.update()

    async def al_ciclo_vida(e: ft.AppLifecycleStateChangeEvent):
        if e.state == ft.AppLifecycleState.RESUME:
            await refrescar()

    async def comprobar_actualizaciones():
        if APP_VERSION == "v0.0.0-dev":
            return  # compilación local: no comparar contra releases
        try:
            response = await asyncio.to_thread(requests.get, URL_RELEASES, timeout=5)
            if response.status_code != 200:
                return
            datos_release = response.json()
            nueva = datos_release.get("tag_name", "")
            if not nueva or nueva.lstrip("v") <= APP_VERSION.lstrip("v"):
                return

            async def descargar(_):
                try:
                    await UrlLauncher().launch_url(datos_release.get("html_url", ""))
                except Exception as exc:
                    log.error("No se pudo abrir el navegador: %s", exc)

            page.show_dialog(
                ft.AlertDialog(
                    title=ft.Text("Actualización disponible"),
                    content=ft.Text(f"Nueva versión {nueva} disponible.\n\n{datos_release.get('body') or ''}"),
                    actions=[
                        ft.TextButton("Descargar", on_click=descargar),
                        ft.TextButton("Cerrar", on_click=lambda _: page.pop_dialog()),
                    ],
                )
            )
        except Exception as exc:
            log.info("Sin verificar actualizaciones: %s", exc)

    # ---------- UI ----------

    punto_estado = ft.Container(
        width=10, height=10, border_radius=5, bgcolor=ft.Colors.GREY_400,
        opacity=1, animate_opacity=300,
    )
    txt_estado = ft.Text("Conectando…", size=13, color=ft.Colors.GREY_600)

    lbl_tasa = ft.Text("0,00 Bs.", size=40, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)

    chip_variacion = ft.Chip(
        label=ft.Text("", size=13, weight=ft.FontWeight.BOLD),
        bgcolor=ft.Colors.with_opacity(0.25, ft.Colors.WHITE), visible=False,
    )

    lbl_actualizado = ft.Text("", size=12, color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE))
    ring = ft.ProgressRing(width=14, height=14, stroke_width=2, color=ft.Colors.WHITE, visible=False)

    # Selector de moneda propio: píldora deslizante animada (las Tabs de 1.1
    # cambiaron de API y este control es totalmente nuestro).
    blanco70 = ft.Colors.with_opacity(0.55, ft.Colors.WHITE)

    def _color_opcion(indice: int):
        return ft.Colors.WHITE if estado["tab"] == indice else blanco70

    txt_op_usd = ft.Text("USD", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    txt_op_eur = ft.Text("EUR", size=15, weight=ft.FontWeight.BOLD, color=blanco70)
    pildora = ft.Container(
        width=120, height=40, border_radius=20,
        bgcolor=ft.Colors.with_opacity(0.25, ft.Colors.WHITE),
        animate_offset=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
    )
    selector_moneda = ft.Stack(
        [
            pildora,
            ft.Row(
                [
                    ft.GestureDetector(
                        content=ft.Container(content=txt_op_usd, width=120, height=40, alignment=ft.Alignment.CENTER),
                        on_tap=lambda _: al_cambiar_tab(0),
                        mouse_cursor=ft.MouseCursor.CLICK,
                    ),
                    ft.GestureDetector(
                        content=ft.Container(content=txt_op_eur, width=120, height=40, alignment=ft.Alignment.CENTER),
                        on_tap=lambda _: al_cambiar_tab(1),
                        mouse_cursor=ft.MouseCursor.CLICK,
                    ),
                ],
                spacing=0,
            ),
        ],
        width=240, height=40,
    )

    def _actualizar_pildora():
        pildora.offset = ft.Offset(estado["tab"], 0)
        txt_op_usd.color = _color_opcion(0)
        txt_op_eur.color = _color_opcion(1)

    tarjeta_hero = ft.Container(
        width=480, padding=24, border_radius=28,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT, colors=["#3949AB", "#7E57C2"]
        ),
        shadow=ft.BoxShadow(
            blur_radius=24, color=ft.Colors.with_opacity(0.25, ft.Colors.BLACK), offset=ft.Offset(0, 8)
        ),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Tasa oficial · BCV", size=13, color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE)),
                        ft.Text(fecha_hoy_es_ve(), size=13, color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE)),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                selector_moneda,
                lbl_tasa,
                chip_variacion,
                ft.Row(
                    [
                        lbl_actualizado,
                        ring,
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.REFRESH, icon_color=ft.Colors.WHITE,
                                    tooltip="Actualizar tasas", on_click=lambda _: page.run_task(refrescar),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.IOS_SHARE, icon_color=ft.Colors.WHITE,
                                    tooltip="Compartir tasa del día", on_click=compartir_tasa_imagen,
                                ),
                            ],
                            spacing=4,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=12,
        ),
        opacity=0, offset=ft.Offset(0, 0.06),
        animate_opacity=ft.Animation(450, ft.AnimationCurve.EASE_OUT), animate_offset=ft.Animation(450, ft.AnimationCurve.EASE_OUT),
    )

    lbl_modo = ft.Text("Divisas → Bolívares", size=13, color=ft.Colors.GREY_500)

    txt_monto = ft.TextField(
        value="", hint_text="0,00", prefix="$ ", expand=True,
        keyboard_type=ft.KeyboardType.NUMBER, on_change=al_escribir_monto,
        text_align=ft.TextAlign.RIGHT, border=ft.OutlineInputBorder(border_radius=16),
        text_size=24,
    )

    switcher_res = ft.AnimatedSwitcher(
        content=resultado_texto(), duration=250, transition=ft.AnimatedSwitcherTransition.FADE
    )

    btn_swap = ft.FilledTonalIconButton(
        icon=ft.Icons.SWAP_VERT, tooltip="Invertir sentido", on_click=invertir_sentido,
        animate_rotation=ft.Animation(400, ft.AnimationCurve.EASE_OUT_BACK),
    )

    tarjeta_calc = ft.Container(
        width=480, padding=24, border_radius=24,
        border=ft.Border.all(1, ft.Colors.with_opacity(0.15, ft.Colors.GREY)),
        content=ft.Column(
            [
                lbl_modo,
                ft.Row(
                    [
                        txt_monto,
                        ft.IconButton(icon=ft.Icons.CONTENT_PASTE, tooltip="Pegar", on_click=pegar_monto),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        switcher_res,
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.CONTENT_COPY, tooltip="Copiar resultado", on_click=copiar_resultado,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.SHARE_OUTLINED, tooltip="Compartir cálculo", on_click=compartir_calculo,
                                ),
                            ],
                            spacing=0,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row([btn_swap], alignment=ft.MainAxisAlignment.CENTER),
            ],
            spacing=14,
        ),
        opacity=0, offset=ft.Offset(0, 0.06),
        animate_opacity=ft.Animation(450, ft.AnimationCurve.EASE_OUT), animate_offset=ft.Animation(450, ft.AnimationCurve.EASE_OUT),
    )

    columna = ft.Column(
        [
            ft.Row(
                [
                    ft.Row(
                        [punto_estado, txt_estado], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.IconButton(icon=ft.Icons.INFO_OUTLINE, tooltip="Créditos", on_click=mostrar_creditos),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text("ScrapBCV", size=28, weight=ft.FontWeight.BOLD),
            tarjeta_hero,
            tarjeta_calc,
            ft.Text(
                "Tasas oficiales del Banco Central de Venezuela · ScrapBCV",
                size=11, color=ft.Colors.GREY_500, text_align=ft.TextAlign.CENTER,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=16,
        scroll=ft.ScrollMode.ADAPTIVE, expand=True,
    )

    page.add(ft.SafeArea(content=columna, expand=True))

    # ---------- Arranque ----------

    page.on_app_lifecycle_state_change = al_ciclo_vida

    async def arrancar():
        await refrescar()
        page.run_task(bucle_reintento)
        page.run_task(pulso_estado)
        page.run_task(comprobar_actualizaciones)
        page.run_task(animar_entrada)

    page.run_task(arrancar)
    log.info("Interfaz lista")

if __name__ == "__main__":
    try:
        ft.run(main)
    except Exception as e:
        log.critical("Error crítico al iniciar la app: %s", e)
