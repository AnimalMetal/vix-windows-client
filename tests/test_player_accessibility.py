"""Recorridos del reproductor nativo y del puente de salida del sitio."""
from types import SimpleNamespace
import wx
import pytest

from app.core.config import Configuracion
from app.services.catalogue import Title
from app.services.media import media_summary, session_summary, value_script
from app.ui.vix_window import VentanaPrincipal
from .conftest import procesar_eventos


@pytest.fixture
def frame(app_wx):
	window = VentanaPrincipal(Configuracion())
	window.titles = [Title("1", "Episodio uno", "Episodio", "https://vix.com/video/video-1")]
	window._filter(None)
	yield window
	window.salir()
	procesar_eventos(lambda: not window)


def test_playback_keeps_catalogue_and_web_bridge_returns(frame, monkeypatch):
	opened = []
	monkeypatch.setattr(frame.live, "navigate", lambda url: opened.append(url))
	frame._play_selected(None)
	assert frame.notebook.GetSelection() == 1
	assert frame.lista.GetItemText(0) == "Episodio uno"
	frame.live._message(SimpleNamespace(GetString=lambda: '{"command":"catalogue"}'))
	assert frame.notebook.GetSelection() == 0
	assert frame.lista.GetFocusedItem() == 0
	assert frame.lista.GetFirstSelected() == 0
	assert opened == ["https://vix.com/video/video-1"]


def test_native_player_labels_and_enabled_controls(frame):
	player = frame.player
	children = list(player.GetChildren())
	for control in [player.title, player.status, player.seek, player.audio, player.subtitles]:
		assert isinstance(children[children.index(control) - 1], wx.StaticText)
		assert control.GetHelpText()
	assert not player.play_button.IsEnabled()
	player.update({"paused": False, "time": 65, "duration": 3600, "volume": .5, "audio": [{"language": "es", "enabled": True}], "subtitles": [{"label": "Español", "mode": "showing"}]}, "Prueba")
	assert player.play_button.IsEnabled()
	assert "00:01:05" in player.status.GetValue()
	assert player.audio.GetStringSelection() == "es"
	assert player.subtitles.GetStringSelection() == "Español"


def test_session_preserves_last_confirmation_during_page_loading(frame):
	frame._live_snapshot({"url": "https://vix.com/account/mi-cuenta", "identity": {"signedIn": True, "profile": "Perfil de prueba"}})
	assert "Perfil de prueba" in frame.account_status.GetValue()
	frame._live_snapshot({"url": "https://vix.com/account/mi-cuenta", "identity": {"signedIn": None, "profile": ""}})
	assert "Perfil de prueba" in frame.account_status.GetValue()
	frame._live_snapshot({"url": "https://vix.com/iniciar-sesion", "identity": {"signedIn": False, "profile": ""}})
	assert frame.account_status.GetValue() == "Sin sesión iniciada en ViX."


def test_only_native_tabs_and_no_generic_browser_actions(frame):
	assert frame.notebook.GetPageCount() == 2
	assert frame.notebook.GetPage(0) is frame.panel
	assert frame.notebook.GetPage(1) is frame.player
	assert "sitio" not in frame.elementos_menu
	assert not frame.account_dialog.IsShown()
	assert frame.live.GetParent() is frame.account_dialog
	labels = [c.GetLabel().casefold() for c in frame.player.GetChildren() if isinstance(c, wx.Button)]
	assert not any("web" in label or "sitio" in label for label in labels)


def test_account_status_updates_silently_and_stays_static_on_tab_changes(frame, monkeypatch):
	from app.core import voz
	messages = []
	monkeypatch.setattr(voz, "hablar", lambda text, interrumpir=False: messages.append(text))
	identity = {"signedIn": True, "profile": "Perfil de prueba"}
	frame._live_snapshot({"url": "https://vix.com/account/mi-cuenta", "identity": identity})
	text = frame.account_status.GetValue()
	for tab in [1, 0, 1, 0]:
		frame.notebook.SetSelection(tab)
		frame._live_snapshot({"url": "https://vix.com/account/mi-cuenta", "identity": {"signedIn": True, "profile": ""}})
		assert frame.account_status.GetValue() == text
	frame._live_snapshot({"url": "https://vix.com/account/mi-cuenta", "identity": {"signedIn": True, "profile": "Otro perfil confirmado"}})
	assert "Otro perfil confirmado" in frame.account_status.GetValue()
	frame._live_snapshot({"url": "https://vix.com/account/mi-cuenta", "identity": {"signedIn": False, "profile": ""}})
	assert frame.account_status.GetValue() == "Sin sesión iniciada en ViX."
	assert messages == []


@pytest.mark.parametrize("previous_tab", [0, 1])
def test_account_workflow_is_explicit_and_returns_to_native_view(frame, monkeypatch, previous_tab):
	opened, dialogs = [], []
	frame.notebook.SetSelection(previous_tab)
	monkeypatch.setattr(frame.live, "navigate", opened.append)
	monkeypatch.setattr(frame.account_dialog, "ShowModal", lambda: dialogs.append(True) or wx.ID_CANCEL)
	frame._account(None)
	assert opened[0] == "https://vix.com/es-es/account/mi-cuenta"
	assert opened[1:] == (["https://vix.com/es-es"] if previous_tab == 0 else [])
	assert dialogs == [True]
	assert frame.notebook.GetSelection() == previous_tab
	assert frame.lista.GetItemText(0) == "Episodio uno"
	assert not frame.account_dialog.IsShown()


def test_unknown_profile_is_explicit():
	assert "no confirmado" in session_summary({"signedIn": True})
	assert "Desconocida" in media_summary({"time": 0, "duration": None})
	with pytest.raises(ValueError):
		value_script("seek", float("nan"))
	assert "v.textTracks" in value_script("subtitle", -1)


def test_more_rows_do_not_rebuild_the_focused_list(frame, monkeypatch):
	monkeypatch.setattr(frame.lista, "DeleteAllItems", lambda: pytest.fail("No debe reconstruir la lista al añadir títulos"))
	frame.titles.append(Title("2", "Segundo", "Serie", "https://vix.com/detail/series-2"))
	frame._filter(None)
	assert frame.lista.GetItemCount() == 2
	assert frame.lista.GetFocusedItem() == 0
	assert frame.lista.GetFirstSelected() == 0


def test_list_boundary_sounds_are_distinct(frame, monkeypatch):
	sounds = []
	monkeypatch.setattr(frame.feedback, "play", sounds.append)
	for key in [wx.WXK_UP, wx.WXK_DOWN]:
		event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
		event.SetKeyCode(key)
		frame._column_key(event)
	assert sounds == ["top", "bottom"]
