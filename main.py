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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def obtener_datos_bcv():
    try:
        url = 'https://www.bcv.org.ve/'
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, verify=False, timeout=8)
        soup = BeautifulSoup(response.content, 'html.parser')
        usd = float(soup.find('div', id='dolar').find('strong').text.strip().replace(',', '.'))
        eur = float(soup.find('div', id='euro').find('strong').text.strip().replace(',', '.'))
        return usd, eur
    except:
        return 0.0, 0.0

def main(page: ft.Page):
    page.title = "Calculadora BCV"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.padding = 15
    
    # Responsividad: Ajuste automático
    page.window_min_width = 350
    page.window_min_height = 600

    # Variables de estado
    datos = {"usd": 0.0, "eur": 0.0, "tasa_actual": 0.0, "modo_inverso": False}

    # UI Components
    lbl_tasa = ft.Text("Cargando...", size=18, weight="bold", color=ft.colors.BLUE)
    lbl_status = ft.Text("", size=12, color=ft.colors.GREY_500)
    
    txt_monto = ft.TextField(
        label="Monto en divisa", 
        prefix_text="$ ", 
        keyboard_type=ft.KeyboardType.NUMBER, 
        on_change=lambda e: calcular(),
        border_radius=12,
        text_size=18,
        expand=True
    )
    
    lbl_res = ft.Text("0,00 Bs.", size=36, weight="bold", color=ft.colors.GREEN_700, text_align="center")
    lbl_modo = ft.Text("Divisa ➔ Bolívares", size=14, italic=True, color=ft.colors.GREY_700)

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
            lbl_res.value = "Error de formato"
        except Exception:
            lbl_res.value = "0,00"
        page.update()

    def invertir_sentido(e):
        datos["modo_inverso"] = not datos["modo_inverso"]
        if datos["modo_inverso"]:
            txt_monto.label = "Monto en Bolívares"
            txt_monto.prefix_text = "Bs "
            lbl_modo.value = "Bolívares ➔ Divisa"
        else:
            es_dolar = tabs.selected_index == 0
            txt_monto.label = f"Monto en {'Dólares' if es_dolar else 'Euros'}"
            txt_monto.prefix_text = "$ " if es_dolar else "€ "
            lbl_modo.value = "Divisa ➔ Bolívares"
        
        calcular()
        page.update()

    def actualizar_datos():
        lbl_status.value = "Sincronizando..."
        page.update()
        u, e = obtener_datos_bcv()
        datos["usd"], datos["eur"] = u, e
        datos["tasa_actual"] = u if tabs.selected_index == 0 else e
        lbl_tasa.value = f"Tasa: {datos['tasa_actual']:.2f} Bs."
        lbl_status.value = f"Última Ref: {time.strftime('%H:%M')}"
        calcular()
        page.update()

    # refresh
    page.on_app_lifecycle_state_change = lambda e: actualizar_datos() if e.data == "resume" else None

    tabs = ft.Tabs(
        selected_index=0,
        on_change=lambda e: (
            datos.update({"tasa_actual": datos["usd"] if e.control.selected_index == 0 else datos["eur"]}),
            setattr(txt_monto, "label", f"Monto en {'Dólares' if e.control.selected_index == 0 else 'Euros'}" if not datos["modo_inverso"] else "Monto en Bolívares"),
            setattr(txt_monto, "prefix_text", ("$ " if e.control.selected_index == 0 else "€ ") if not datos["modo_inverso"] else "Bs "),
            actualizar_datos()
        ),
        tabs=[
            ft.Tab(text="USD", icon=ft.icons.MONETIZATION_ON), 
            ft.Tab(text="EUR", icon=ft.icons.EURO)
        ],
        alignment=ft.MainAxisAlignment.CENTER
    )

    page.add(
        ft.SafeArea(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("Calculadora BCV", size=26, weight="bold"), 
                        ft.IconButton(ft.icons.REFRESH, on_click=lambda _: actualizar_datos())
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    tabs,
                    ft.Container(
                        content=ft.Column([
                            lbl_modo,
                            lbl_tasa,
                            lbl_status,
                            ft.Divider(height=30, thickness=1),
                            ft.Row([txt_monto], alignment=ft.MainAxisAlignment.CENTER),
                            ft.IconButton(
                                icon=ft.icons.SWAP_VERT_CIRCLE, 
                                icon_size=45, 
                                on_click=invertir_sentido, 
                                tooltip="Cambiar sentido",
                                icon_color=ft.colors.BLUE_ACCENT
                            ),
                            ft.Text("Resultado:", size=16, weight="w500"),
                            lbl_res,
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=25, 
                        bgcolor=ft.colors.with_opacity(0.05, ft.colors.ON_SURFACE), 
                        border_radius=25, 
                        border=ft.border.all(1, ft.colors.OUTLINE_VARIANT)
                    )
                ], spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                max_width=500,
                alignment=ft.alignment.top_center
            )
        )
    )
    actualizar_datos()

if __name__ == "__main__":
    ft.app(target=main)

#/////I Love Tefi//////