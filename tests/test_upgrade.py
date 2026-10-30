"""La actualización conserva datos y nunca copia un perfil abierto."""
import json
import pytest
from app.core import upgrade


def test_upgrade_copies_settings_and_closed_profile_without_changing_previous(tmp_path):
	previous = tmp_path / "previous"
	current = tmp_path / "current"
	(previous / "config").mkdir(parents=True)
	(previous / "sessions/webview2").mkdir(parents=True)
	(previous / "sessions/webview2/profile-test").write_text("test data", encoding="utf-8")
	(previous / "config/config.json").write_text('{"sounds":{"volume":15}}', encoding="utf-8")
	upgrade.copy_previous_data(previous, current)
	assert (current / "sessions/webview2/profile-test").read_text() == "test data"
	assert (previous / "sessions/webview2/profile-test").exists()
	assert json.loads((current / "config/config.json").read_text())["sounds"]["volume"] == 15
	(current / "config/config.json").write_text("new settings")
	upgrade.copy_previous_data(previous, current)
	assert (current / "config/config.json").read_text() == "new settings"


def test_upgrade_refuses_live_profile(tmp_path, monkeypatch):
	previous, current = tmp_path / "previous", tmp_path / "current"
	(previous / "sessions").mkdir(parents=True)
	(previous / "temp/instancia").mkdir(parents=True)
	(previous / "temp/instancia/instancia.json").write_text('{"pid":123}')
	monkeypatch.setattr(upgrade, "process_alive", lambda pid: True)
	with pytest.raises(RuntimeError, match="cierre"):
		upgrade.copy_previous_data(previous, current)
	assert not (current / "sessions").exists()


def test_import_chooses_the_latest_older_version_and_ignores_newer_versions(tmp_path, monkeypatch):
	current = tmp_path / "VixClient-1.2.2"
	current.mkdir()
	for name in ["VixClient-1.1.0", "VixClient-1.2.0", "VixClient-1.2.1", "VixClient-9.0.0"]:
		folder = tmp_path / name / "data/config"
		folder.mkdir(parents=True)
		(folder / "config.json").write_text('{}')
	chosen = []
	monkeypatch.setattr(upgrade.paths, "CONGELADA", True)
	monkeypatch.delenv(upgrade.paths.VARIABLE_DATA, raising=False)
	monkeypatch.setattr(upgrade.paths, "ruta_base", lambda: current)
	monkeypatch.setattr(upgrade.paths, "ruta_datos", lambda: current / "data")
	monkeypatch.setattr(upgrade, "copy_previous_data", lambda previous, destination: chosen.append(previous))
	upgrade.import_previous_version()
	assert chosen == [tmp_path / "VixClient-1.2.1/data"]
