"""Explica las filas de Inicio con texto consultable, independiente de la voz."""
import unicodedata


def section_help(name):
	key = "".join(c for c in unicodedata.normalize("NFD", name.casefold()) if not unicodedata.combining(c))
	if name == "Todas las secciones":
		return "Reúne las filas de esta página. Elija una sección para recorrer solo sus títulos. La columna Secciones indica dónde aparece cada título."
	if any(word in key for word in ["continu", "seguir viendo", "sigue viendo"]):
		return "Títulos empezados con el perfil actual que ViX ofrece para retomar. Esta fila depende de su sesión y perfil; es distinta de las recomendaciones."
	if "recomend" in key or "para ti" in key:
		return "Sugerencias de ViX para su sesión o perfil. No significa que haya empezado a ver esos títulos."
	if "mi lista" in key or "tu lista" in key:
		return "Lista guardada de su cuenta de ViX. Es distinta de los Favoritos locales del cliente."
	if "destacad" in key:
		return "Contenidos destacados en la cabecera de la página. ViX puede usarlos para mostrar novedades o promociones."
	if any(word in key for word in ["top", "popular", "mas buscad", "mas vist"]):
		return "Fila de popularidad con el nombre y el orden que publica ViX. Puede variar por región y fecha."
	return f"Fila de ViX: {name}. La lista contiene solo los títulos cargados de esta fila. Ctrl+M permite continuar la carga de la página."
