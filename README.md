# Calculadora BCV 🇻🇪

Una aplicación sencilla y elegante construida con **Flet** para consultar las tasas oficiales del Banco Central de Venezuela (USD/EUR) y realizar conversiones rápidas. Optimizada para dispositivos móviles.

## ✨ Características
- Consulta en tiempo real de tasas BCV (Dólar y Euro).
- Conversión bidireccional (Divisa ➔ Bolívares y viceversa).
- Interfaz adaptativa (Modo claro/oscuro según el sistema).
- Diseño optimizado para teléfonos.

## 🚀 Instalación

1. Clona este repositorio:
   ```bash
   git clone https://https://github.com/YuiStarLord/app-bcv.git
   cd app-bcv
   ```

2. Crea un entorno virtual (recomendado):
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # En Windows
   ```

3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## 🛠️ Uso

Para ejecutar la aplicación en modo desarrollo:
```bash
python main.py
```

## 📦 Compilación

Para compilar la aplicación para diferentes plataformas usando Flet:

### Para Windows:
```bash
flet build windows
```

### Para Android (requiere SDK de Android):
```bash
flet build apk
```

### Para Web:
```bash
flet build web
```

---
Desarrollado por **YuiStarLord**
