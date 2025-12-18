'''
PROYECTO AISLADO PARA EMPRESA
BY YUISTARLOD
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
    page.theme_mode = "light"
    page.horizontal_alignment = "center"
    page.padding = 20

    # Variables de estado
    datos = {"usd": 0.0, "eur": 0.0, "tasa_actual": 0.0, "modo_inverso": False}

    # UI Components
    lbl_tasa = ft.Text("Cargando...", size=16, weight="bold", color="blue")
    lbl_status = ft.Text("", size=11, color="grey")
    
    txt_monto = ft.TextField(
        label="Monto en divisa", 
        prefix_text="$ ", 
        keyboard_type="number", 
        on_change=lambda e: calcular()
    )
    
    lbl_res = ft.Text("0,00 Bs.", size=42, weight="bold", color="green700")
    lbl_modo = ft.Text("Divisa ➔ Bolívares", size=12, italic=True)

    def calcular():
        try:
            val = float(txt_monto.value.replace(",", ".")) if txt_monto.value else 0.0
            if not datos["modo_inverso"]:
                # Divisa a Bs
                total = val * datos["tasa_actual"]
                lbl_res.value = f"{total:,.2f} Bs.".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                # Bs a Divisa
                total = val / datos["tasa_actual"] if datos["tasa_actual"] > 0 else 0
                simbolo = "$" if tabs.selected_index == 0 else "€"
                lbl_res.value = f"{total:,.2f} {simbolo}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
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
            setattr(datos, "tasa_actual", datos["usd"] if e.control.selected_index == 0 else datos["eur"]),
            # reset
            setattr(txt_monto, "label", f"Monto en {'Dólares' if e.control.selected_index == 0 else 'Euros'}" if not datos["modo_inverso"] else "Monto en Bolívares"),
            setattr(txt_monto, "prefix_text", ("$ " if e.control.selected_index == 0 else "€ ") if not datos["modo_inverso"] else "Bs "),
            actualizar_datos()
        ),
        tabs=[ft.Tab(text="USD", icon="monetization_on"), ft.Tab(text="EUR", icon="euro")]
    )

    page.add(
        ft.Row([ft.Text("Calculadora BCV", size=24, weight="bold"), ft.IconButton("refresh", on_click=lambda _: actualizar_datos())], alignment="spaceBetween"),
        tabs,
        ft.Container(
            content=ft.Column([
                lbl_modo,
                lbl_tasa,
                lbl_status,
                ft.Divider(),
                txt_monto,
                ft.IconButton(icon="swap_vert", icon_size=30, on_click=invertir_sentido, tooltip="Cambiar sentido"),
                ft.Text("Resultado:"),
                lbl_res,
            ], horizontal_alignment="center"),
            padding=20, bgcolor="#f8f9fa", border_radius=20, border=ft.border.all(1, "#dee2e6")
        )
    )
    actualizar_datos()

ft.app(target=main)

#/////I❤️Tefi//////