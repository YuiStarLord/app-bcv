'''
PROYECTO AISLADO PARA EMPRESA
ORIGINAL BY YUISTARLOD
MAINTAINED BY HAKKAYORO
'''

import flet as ft
import requests
from bs4 import BeautifulSoup
import urllib3
import time
import logging
import os
import platform

# Configuración de logs para Windows y Linux
if platform.system() in ["Windows", "Linux"]:
    logging.basicConfig(
        filename="app.log",
        filemode="w", # Sobrescribir en cada inicio
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logging.info(f"Iniciando aplicación en {platform.system()}")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def obtener_datos_bcv():
    logging.info("Iniciando obtención de datos del BCV")
    try:
        url = 'https://www.bcv.org.ve/'
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, verify=False, timeout=8)
        logging.debug(f"Respuesta del BCV: {response.status_code}")
        soup = BeautifulSoup(response.content, 'html.parser')
        usd = float(soup.find('div', id='dolar').find('strong').text.strip().replace(',', '.'))
        eur = float(soup.find('div', id='euro').find('strong').text.strip().replace(',', '.'))
        logging.info(f"Tasas obtenidas: USD={usd}, EUR={eur}")
        return usd, eur
    except Exception as e:
        logging.error(f"Error al obtener datos del BCV: {str(e)}")
        return 0.0, 0.0

def main(page: ft.Page):
    logging.info("Configurando interfaz de usuario")
    page.title = "ScrapBCV"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.padding = 20
    page.window_width = 400
    page.window_height = 700
    
    # Responsividad: Ajuste automático
    page.window_min_width = 350
    page.window_min_height = 600

    # Variables de estado
    datos = {"usd": 0.0, "eur": 0.0, "tasa_actual": 0.0, "modo_inverso": False}

    # UI Components
    lbl_tasa = ft.Text("Cargando...", size=16, weight="bold", color=ft.Colors.BLUE_GREY_400)
    lbl_status = ft.Text("", size=12, color=ft.Colors.GREY_500)
    
    txt_monto = ft.TextField(
        label="Monto", 
        prefix_text="$ ", 
        keyboard_type=ft.KeyboardType.NUMBER, 
        on_change=lambda e: calcular(),
        border_radius=15,
        text_size=20,
        expand=True,
        border_color=ft.Colors.BLUE_GREY_200,
        focused_border_color=ft.Colors.BLUE_600
    )
    
    lbl_res = ft.Text("0,00 Bs.", size=40, weight="bold", color=ft.Colors.GREEN_600, text_align="center")
    lbl_modo = ft.Text("Divisa ➔ Bolívares", size=14, italic=True, color=ft.Colors.GREY_700)

    def calcular():
        try:
            val_str = txt_monto.value.replace(",", ".") if txt_monto.value else "0"
            val = float(val_str)
            if not datos["modo_inverso"]:
                # Divisa a Bs
                total = val * datos["tasa_actual"]
                lbl_res.value = f"{total:,.2f} Bs.".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                # Bs a Divisa
                total = val / datos["tasa_actual"] if datos["tasa_actual"] > 0 else 0
                simbolo = "$" if tabs.selected_index == 0 else "€"
                lbl_res.value = f"{total:,.2f} {simbolo}".replace(",", "X").replace(".", ",").replace("X", ".")
        except ValueError:
            lbl_res.value = "Error"
        except Exception as e:
            logging.error(f"Error en cálculo: {str(e)}")
            lbl_res.value = "0,00"
        page.update()

    def invertir_sentido(e):
        logging.debug("Cambiando sentido de conversión")
        datos["modo_inverso"] = not datos["modo_inverso"]
        if datos["modo_inverso"]:
            txt_monto.label = "Bolívares"
            txt_monto.prefix_text = "Bs "
            lbl_modo.value = "Bolívares ➔ Divisa"
        else:
            es_dolar = tabs.selected_index == 0
            txt_monto.label = f"{'Dólares' if es_dolar else 'Euros'}"
            txt_monto.prefix_text = "$ " if es_dolar else "€ "
            lbl_modo.value = "Divisa ➔ Bolívares"
        
        calcular()
        page.update()

    def paste_monto(e):
        txt_monto.value = page.get_clipboard()
        calcular()
        page.update()

    def copy_resultado(e):
        page.set_clipboard(lbl_res.value)
        page.show_snack_bar(ft.SnackBar(ft.Text("Resultado copiado!"), open=True))

    def actualizar_datos():
        logging.info("Actualizando datos de la interfaz")
        lbl_status.value = "Sincronizando..."
        page.update()
        u, e = obtener_datos_bcv()
        datos["usd"], datos["eur"] = u, e
        datos["tasa_actual"] = u if tabs.selected_index == 0 else e
        lbl_tasa.value = f"Tasa: {datos['tasa_actual']:.2f} Bs."
        lbl_status.value = f"Ref: {time.strftime('%H:%M')}"
        calcular()
        page.update()

    # refresh
    page.on_app_lifecycle_state_change = lambda e: actualizar_datos() if e.data == "resume" else None

    tabs = ft.Tabs(
        selected_index=0,
        on_change=lambda e: (
            logging.debug(f"Cambiando a pestaña: {e.control.selected_index}"),
            datos.update({"tasa_actual": datos["usd"] if e.control.selected_index == 0 else datos["eur"]}),
            setattr(txt_monto, "label", f"{'Dólares' if e.control.selected_index == 0 else 'Euros'}" if not datos["modo_inverso"] else "Bolívares"),
            setattr(txt_monto, "prefix_text", ("$ " if e.control.selected_index == 0 else "€ ") if not datos["modo_inverso"] else "Bs "),
            actualizar_datos()
        ),
        tabs=[
            ft.Tab(text="USD", icon=ft.Icons.MONETIZATION_ON), 
            ft.Tab(text="EUR", icon=ft.Icons.EURO)
        ],
        indicator_color=ft.Colors.BLUE_600,
        label_color=ft.Colors.BLUE_600,
        unselected_label_color=ft.Colors.GREY_500,
    )

    logging.info("Agregando componentes a la página")
    page.add(
        ft.SafeArea(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("ScrapBCV", size=32, weight="bold", color=ft.Colors.BLUE_GREY_900),
                    ft.Container(
                        content=ft.Row([
                            lbl_status,
                            ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: actualizar_datos(), icon_color=ft.Colors.BLUE_600)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=ft.padding.only(bottom=10)
                    ),
                    tabs,
                    ft.Container(
                        content=ft.Column([
                            lbl_tasa,
                            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                            ft.Row([
                                txt_monto,
                                ft.IconButton(ft.Icons.CONTENT_PASTE, on_click=paste_monto, tooltip="Pegar", icon_color=ft.Colors.BLUE_GREY_400)
                            ], alignment=ft.MainAxisAlignment.CENTER),
                            
                            ft.Container(height=10),
                            
                            ft.IconButton(
                                icon=ft.Icons.SWAP_VERT_CIRCLE, 
                                icon_size=50, 
                                on_click=invertir_sentido, 
                                tooltip="Invertir",
                                icon_color=ft.Colors.BLUE_600
                            ),
                            
                            ft.Container(height=10),
                            
                            lbl_modo,
                            ft.Row([
                                lbl_res,
                                ft.IconButton(ft.Icons.CONTENT_COPY, on_click=copy_resultado, tooltip="Copiar", icon_color=ft.Colors.GREEN_600)
                            ], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                            
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=30, 
                        bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.BLUE_GREY), 
                        border_radius=30, 
                        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                        shadow=ft.BoxShadow(
                            spread_radius=1,
                            blur_radius=15,
                            color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
                            offset=ft.Offset(0, 5),
                        )
                    )
                ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            )
        )
    )
    actualizar_datos()
    logging.info("Interfaz lista")

if __name__ == "__main__":
    try:
        ft.app(target=main)
    except Exception as e:
        logging.critical(f"Error crítico al iniciar la app: {str(e)}")

#/////I Love Tefi//////