"""Inicio conserva el significado de sus encabezados y sus títulos compartidos."""
from app.services.live_site import snapshot_titles
from app.services.sections import section_help


def test_same_title_can_belong_to_continue_watching_and_recommendations():
	data = {"url": "https://vix.com/es-es", "items": [{"url": "https://vix.com/detail/series-1", "title": "Uno", "group": "Continuar viendo"}, {"url": "https://vix.com/detail/series-1", "title": "Uno", "group": "Recomendado para ti"}]}
	titles = snapshot_titles(data)
	assert len(titles) == 1
	assert titles[0].groups == ["Continuar viendo", "Recomendado para ti"]
	assert "empezados" in section_help("Continuar viendo")
	assert "Sugerencias" in section_help("Recomendado para ti")
	assert "Favoritos locales" in section_help("Mi lista")


def test_native_heading_selector_filters_without_losing_memberships(app_wx):
	from app.core.config import Configuracion
	from app.services.catalogue import Title
	from app.ui.vix_window import VentanaPrincipal
	from .conftest import procesar_eventos
	frame = VentanaPrincipal(Configuracion())
	try:
		frame.titles = [Title("1", "Uno", "Serie", "https://vix.com/detail/series-1", groups=["Continuar viendo"]), Title("2", "Dos", "Serie", "https://vix.com/detail/series-2", groups=["Recomendado para ti"])]
		frame._filter(None)
		assert frame.home_group.GetStrings() == ["Todas las secciones", "Continuar viendo", "Recomendado para ti"]
		frame.home_group.SetStringSelection("Continuar viendo")
		frame._group_changed(None)
		assert frame.lista.GetItemCount() == 1
		assert frame.lista.GetItemText(0) == "Uno"
		assert frame.lista.GetItemText(0, 5) == "Continuar viendo"
		assert "empezados" in frame.group_description.GetValue()
	finally:
		frame.salir()
		procesar_eventos(lambda: not frame)
