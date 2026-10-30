"""Nombre y versión de la aplicación: ÚNICA fuente de verdad.

``setup_cx.py`` la lee con una expresión regular (sin importar la
aplicación) y ``pyproject.toml`` debe coincidir; una prueba lo comprueba.
Para publicar una versión nueva solo se cambia ``APP_VERSION`` aquí.
"""

# Nombre visible: título de la ventana, «Acerca de», anuncios y registros.
NOMBRE_APLICACION = "ViX Client"
# Identificador sin espacios: ejecutable, instancia única, carpeta de compilación.
ID_APLICACION = "VixClient"
APP_VERSION = "1.4.1"
