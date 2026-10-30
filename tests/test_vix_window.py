"""Recorridos del cliente real con wx nativo, sin abrir el navegador."""
import wx
import pytest
from app.core.config import Configuracion
from app.services.catalogue import Title
from app.ui import vix_window
from .conftest import procesar_eventos

@pytest.fixture
def window(app_wx):
	frame = vix_window.VentanaPrincipal(Configuracion())
	frame.titles = [Title("1", "Corazón", "Serie", "https://vix.com/detail/series-1", "Historia completa", "2020", "Drama"), Title("2", "Otro", "Película", "https://vix.com/detail/video-2")]
	frame._filter(None)
	yield frame
	frame.salir()
	procesar_eventos(lambda: not frame)

def test_native_labels_and_details(window):
	children = list(window.panel.GetChildren())
	for control in [window.section, window.query, window.lista, window.details]:
		assert isinstance(children[children.index(control) - 1], wx.StaticText)
		assert control.GetHelpText()
	assert window.lista.GetFocusedItem() == 0
	assert window.lista.GetFirstSelected() == 0
	assert "Historia completa" in window.details.GetValue()

def test_real_client_menu_access_keys_are_unique(window):
	bar = window.GetMenuBar()
	for i in range(bar.GetMenuCount()):
		keys = []
		for item in bar.GetMenu(i).GetMenuItems():
			if item.IsSeparator():
				continue
			label = item.GetItemLabel()
			keys.append(label[label.index("&") + 1].casefold())
		assert len(keys) == len(set(keys))

def test_filter_and_open_exact_title(window, monkeypatch):
	opened = []
	monkeypatch.setattr(window, "_navigate", lambda url, show_site=False: opened.append((url, show_site)))
	window.query.SetValue("corazon")
	assert window.lista.GetItemCount() == 1
	window._open_selected(None)
	assert opened == [("https://vix.com/detail/series-1", False)]

def test_favorites_persist_and_remove(window):
	window._favorite(None)
	assert len(Configuracion().obtener("vix.favorites")) == 1
	window.section.SetStringSelection("Favoritos")
	window._al_actualizar(None)
	assert window.lista.GetItemCount() == 1
	window._favorite(None)
	assert window.lista.GetItemCount() == 0
	assert Configuracion().obtener("vix.favorites") == []

def test_stale_network_result_does_not_replace_new_section(window, monkeypatch):
	window.section.SetStringSelection("Favoritos")
	window._al_actualizar(None)
	window._live_snapshot({"url": "https://vix.com/es-es", "items": [{"url": "https://vix.com/detail/series-1", "title": "Viejo"}]})
	assert window.lista.GetItemCount() == 0

def test_column_preferences_apply_without_reopening(window, monkeypatch):
	messages = []
	monkeypatch.setattr(vix_window.voz, "hablar", lambda text, interrumpir=False: messages.append(text))
	for key in ["row_number", "column_name", "column_content"]:
		window._config.establecer("vix." + key, False)
	event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
	event.SetKeyCode(ord("1"))
	event.SetControlDown(True)
	window._column_key(event)
	assert messages == ["Corazón"]
