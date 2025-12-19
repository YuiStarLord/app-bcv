# ScrapBCV

Aplicación de escritorio y móvil desarrollada en **Flet** para consultar las tasas de cambio oficiales del Banco Central de Venezuela (BCV). Diseñada para ofrecer una experiencia de usuario fluida, rápida y estéticamente agradable.

## Características Principales

*   **Consulta en Tiempo Real**: Obtención automática de las tasas del Dólar y Euro desde el sitio oficial del BCV.
*   **Conversión Inteligente**: Calculadora integrada para conversiones bidireccionales (Divisa <-> Bolívares).
*   **Portapapeles Inteligente**: Detección automática de formatos numéricos (US/EU) al pegar montos.
*   **Interfaz Moderna**: Diseño limpio y adaptativo que soporta modo claro y oscuro.
*   **Multiplataforma**: Disponible para Windows, Linux y Android.

## Instalación y Ejecución

### Requisitos Previos

*   Python 3.11 o superior
*   Git

### Pasos

1.  Clonar el repositorio:
    ```bash
    git clone https://github.com/HakkaYoro/app-bcv.git
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

## Créditos y Autoría

Este proyecto es mantenido y desarrollado por:

*   **[HakkaYoro](https://github.com/HakkaYoro)** - Desarrollador Principal
*   **[YuiStarLord](https://github.com/YuiStarLord)** - Autor Original

---
Desarrollado con Flet y Python.
