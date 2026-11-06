# ScrapBCV

Aplicación de escritorio y móvil desarrollada en **Flet 1.x (Python)** para consultar las tasas de cambio oficiales del Banco Central de Venezuela (BCV). Diseñada para ofrecer una experiencia de usuario fluida, rápida y estéticamente agradable.

## Características Principales

*   **Consulta en Tiempo Real**: Obtención automática de las tasas del Dólar y Euro desde el sitio oficial del BCV (parser tolerante a montos de cuatro cifras y separadores es-VE).
*   **Sistema de Caché Inteligente**: Almacena localmente las últimas tasas obtenidas (SharedPreferences) para permitir consultas **Offline** cuando no hay conexión, con reintentos automáticos.
*   **Conversión Inteligente**: Calculadora integrada para conversiones bidireccionales (Divisa <-> Bolívares) con máscara de entrada en formato es-VE (`1.234,56`) y cursor siempre al final.
*   **Compartir Tasa (Imagen)**: Genera una tarjeta con la tasa del día (renderizada con el control `Screenshot` de Flet) y la comparte como imagen PNG por cualquier app (WhatsApp, Telegram, etc.) mediante el servicio `Share`.
*   **Compartir Cálculo**: Comparte el resultado de la conversión como texto formateado (monto, tasa y fecha).
*   **Interfaz Moderna**: Material 3 con modo claro/oscuro automático, tarjeta de gradiente, selector de moneda con píldora deslizante animada y transiciones animadas en tasas y resultados.
*   **Multiplataforma**: Disponible para Windows, Linux, MacOS y Android.

## Instalación y Ejecución

### Requisitos Previos

*   Python 3.11 o superior
*   Git

### Pasos

1.  Clonar el repositorio:
    ```bash
    git clone https://github.com/YuiStarLord/app-bcv.git
    cd app-bcv
    ```

2.  Crear y activar un entorno virtual:
    ```bash
    python -m venv venv
    # En Windows:
    .\venv\Scripts\activate
    # En Linux/Mac:
    source venv/bin/activate
    ```

3.  Instalar dependencias:
    ```bash
    pip install -r requirements.txt
    ```

4.  Ejecutar la aplicación:
    ```bash
    python main.py
    ```

## Compilación

Para generar ejecutables independientes, utilice los siguientes comandos según su plataforma:

**Windows (Portable):**
```bash
flet build windows --product "ScrapBCV"
```

**Android (APK):**
```bash
flet build apk --product "ScrapBCV"
```

**Linux (AppImage/Tarball):**
```bash
flet build linux --product "ScrapBCV"
```

**MacOS (App/DMG):**
```bash
flet build macos --product "ScrapBCV"
```

## Créditos y Autoría

Este proyecto es mantenido y desarrollado por:

*   **[HakkaYoro](https://github.com/HakkaYoro)** - Desarrollador Principal
*   **[YuiStarLord](https://github.com/YuiStarLord)** - Autor Original

---
Desarrollado con Flet y Python.
