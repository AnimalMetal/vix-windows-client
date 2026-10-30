"""User choices, preferences and update lifecycle in the real native shell."""
from pathlib import Path
import threading

import pytest
import wx

from app.core.config import Configuracion
from app.services import actualizador
from app.ui import dialogo_actualizacion as ui
from app.ui.dialogo_opciones import DialogoOpciones
from app.ui.vix_window import VentanaPrincipal
from tests.conftest import procesar_eventos


@pytest.fixture
def frame(app_wx):
	window = VentanaPrincipal(Configuracion())
	yield window
	window.salir()
	procesar_eventos(lambda: not window)


def test_setting_default_save_cancel_and_reload(app_wx):
	config = Configuracion()
	assert config.obtener("updates.check_on_startup") is True
	with DialogoOpciones(None, config) as dialog:
		assert dialog.casillas["updates.check_on_startup"].GetValue()
		dialog.casillas["updates.check_on_startup"].SetValue(False)
	assert config.obtener("updates.check_on_startup") is True  # Cancel does not apply.
	with DialogoOpciones(None, config) as dialog:
		dialog.casillas["updates.check_on_startup"].SetValue(False)
		dialog.aplicar()
	assert Configuracion().obtener("updates.check_on_startup") is False


def test_startup_off_skips_network_manual_still_works(frame, monkeypatch):
	control = frame.actualizaciones
	frame._config.establecer("updates.check_on_startup", False)
	queries = []
	monkeypatch.setattr(actualizador, "comprobar", lambda *a, **k: queries.append(threading.get_ident()))
	monkeypatch.setattr(ui, "_informar_manual", lambda *a: None)
	control.comprobar()
	assert not queries
	control.comprobar(manual=True)
	assert procesar_eventos(lambda: not control._ocupado)
	assert len(queries) == 1 and queries[0] != threading.get_ident()


def test_disabled_while_checking_suppresses_prompt(frame, monkeypatch):
	control = frame.actualizaciones
	frame._config.establecer("updates.check_on_startup", False)
	shown = []
	monkeypatch.setattr(ui, "mostrar_dialogo", lambda *a: shown.append(a))
	control._resultado(False, object(), None)
	assert not shown


def test_no_choice_does_not_download_or_close(frame, monkeypatch):
	downloads = []
	monkeypatch.setattr(actualizador, "descargar_y_preparar", lambda *a, **k: downloads.append(1))
	info = actualizador.InfoActualizacion("2.0.0", "new.zip", "https://example.test/new.zip", "0" * 64, 1)
	with ui.DialogoActualizacion(frame, frame.actualizaciones.config, info) as dialog:
		dialog._al_mas_tarde(None)
		assert dialog.resultado == dialog.RESULTADO_MAS_TARDE
	assert not downloads and frame


def test_cancel_after_preparation_never_launches_installer(frame, monkeypatch):
	launched = []
	monkeypatch.setattr(actualizador, "lanzar_sustitucion", launched.append)
	info = actualizador.InfoActualizacion("2.0.0", "new.zip", "https://example.test/new.zip", "0" * 64, 1)
	with ui.DialogoActualizacion(frame, frame.actualizaciones.config, info) as dialog:
		dialog._cancelar.set()
		dialog._al_preparada(Path("unused.bat"))
	assert not launched


def test_installation_exits_even_with_close_to_tray(frame, monkeypatch):
	frame._config.establecer("general.cerrar_a_bandeja", True)
	calls = []
	monkeypatch.setattr(wx.GetApp(), "GetTopWindow", lambda: frame)
	monkeypatch.setattr(frame, "salir", lambda: calls.append("exit"))
	ui._cerrar_aplicacion()
	assert calls == ["exit"]


def test_extraction_refuses_to_clear_arbitrary_directory(tmp_path):
	config = actualizador.Configuracion("1.0", tmp_path / "app")
	outside = tmp_path / "user-files"
	outside.mkdir()
	(outside / "keep.txt").write_text("important")
	with pytest.raises(actualizador.ErrorPaquete):
		actualizador.extraer_seguro(tmp_path / "fake.zip", outside, config)
	assert (outside / "keep.txt").read_text() == "important"
