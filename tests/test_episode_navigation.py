"""Cambios de temporada, respuestas tardías y recuperación de errores."""
from types import SimpleNamespace
import time

import pytest

from app.services.episode_navigation import selection_outcome
from app.core.config import Configuracion
from app.services.catalogue import Title
from app.ui.vix_window import VentanaPrincipal
from .conftest import procesar_eventos


def pending(**changes):
	return {"request": 2, "selector": "episodes-selector-0", "target": "Temporada 3", "before": ["https://vix.com/video/video-1"], "started": 100, **changes}


def snapshot(selected="Temporada 3", episode="2", **changes):
	return {"url": "https://vix.com/es-es/detail/series-42", "selectors": [{"id": "episodes-selector-0", "kind": "season", "selected": selected, "options": ["Temporada 1", "Temporada 2", "Temporada 3"], "discovered": True}], "episodeUrls": ["https://vix.com/video/video-" + episode], "episodeLoading": False, "items": [{"title": "Episodio " + episode, "url": "https://vix.com/video/video-" + episode}], **changes}


def test_selection_waits_for_new_episodes_and_finishes_when_ready():
	assert selection_outcome(pending(), snapshot(episode="1"), 101)[0] == "waiting"
	assert selection_outcome(pending(), snapshot(episodeLoading=True), 102)[0] == "ready"
	assert selection_outcome(pending(), snapshot(episode="1", episodeLoading=True), 102)[0] == "waiting"
	assert selection_outcome(pending(), snapshot(episodeUrls=[]), 102)[0] == "waiting"
	assert selection_outcome(pending(), snapshot(episodeUrls=[], episodeEmpty=True), 102)[0] == "ready"
	assert selection_outcome(pending(), snapshot(), 103)[0] == "ready"


def test_loading_more_old_episodes_cannot_confirm_new_season():
	data = snapshot(episodeUrls=["https://vix.com/video/video-1", "https://vix.com/video/video-2"])
	assert selection_outcome(pending(), data, 102)[0] == "waiting"


def test_rapid_requests_compare_with_episodes_at_the_actual_click():
	# Season 2 arrived while season 3 was being requested: it must not be
	# mistaken for season 3 merely because it differs from the old native rows.
	result = {"request": 2, "status": "clicked", "beforeUrls": ["https://vix.com/video/video-2"]}
	assert selection_outcome(pending(), snapshot(episode="2", selectionResult=result), 102)[0] == "waiting"
	assert selection_outcome(pending(), snapshot(episode="3", selectionResult=result), 102)[0] == "ready"
	assert selection_outcome(pending(), snapshot(episode="3", selectionResult={**result, "request": 1}), 102)[0] == "waiting"


def test_loaded_episodes_do_not_wait_for_load_more_spinner(frame):
	frame._selector_pending = pending(started=time.monotonic())
	frame.live.begin_episode_selection()
	frame._live_snapshot(snapshot(episodeLoading=True))
	assert frame._selector_pending is None
	assert frame.lista.GetItemText(0) == "Episodio 2"
	assert frame.live.timer.GetInterval() == 1200


def test_return_to_original_season_supersedes_pending_request(frame):
	frame.live.view = SimpleNamespace(RunScriptAsync=lambda script: None, Stop=lambda: None)
	frame.season_choice.SetStringSelection("Temporada 3")
	frame._select_episode_content("season")
	assert frame.live.timer.GetInterval() == 200
	frame.season_choice.SetStringSelection("Temporada 1")
	frame._select_episode_content("season")
	assert frame._selector_pending["request"] == 2
	frame._live_snapshot(snapshot(selected="Temporada 1", episode="1", selectionResult={"request": 2, "status": "clicked"}))
	assert frame._selector_pending is None
	assert frame.lista.GetItemText(0) == "Episodio 1"


def test_failure_and_timeout_do_not_leave_loading_stuck():
	assert selection_outcome(pending(), snapshot(selectionResult={"request": 2, "status": "failed", "message": "No disponible"}), 101) == ("failed", "No disponible")
	assert selection_outcome(pending(), snapshot(selected="Temporada 1", episode="1"), 116)[0] == "failed"
	assert selection_outcome(pending(), snapshot(selected="Temporada 1", episode="1", selectionResult={"request": 1, "status": "failed"}), 101)[0] == "waiting"


@pytest.fixture
def frame(app_wx):
	window = VentanaPrincipal(Configuracion())
	window._live_snapshot(snapshot(selected="Temporada 1", episode="1"))
	yield window
	window.salir()
	procesar_eventos(lambda: not window)


def test_current_season_does_not_reset_to_first_option(frame):
	frame._live_snapshot(snapshot())
	assert frame.season_choice.GetStrings() == ["Temporada 1", "Temporada 2", "Temporada 3"]
	assert frame.season_choice.GetStringSelection() == "Temporada 3"
	assert not frame.episode_group.IsEnabled()


def test_new_season_replaces_old_rows_and_clears_local_filter(frame):
	frame.query.SetValue("Episodio 1")
	frame._selector_pending = pending(started=time.monotonic())
	frame._live_snapshot(snapshot())
	assert frame._selector_pending is None
	assert frame.query.GetValue() == ""
	assert frame.lista.GetItemCount() == 1
	assert frame.lista.GetItemText(0) == "Episodio 2"
	assert frame.live.loading_all


def test_failed_selection_restores_native_choice_and_keeps_usable_rows(frame):
	frame.season_choice.SetStringSelection("Temporada 3")
	frame._selector_pending = pending(started=time.monotonic())
	frame._live_snapshot(snapshot(selected="Temporada 1", episode="1", selectionResult={"request": 2, "status": "failed", "message": "No disponible"}))
	assert frame._selector_pending is None
	assert frame.season_choice.GetStringSelection() == "Temporada 1"
	assert frame.lista.GetItemCount() == 1
	assert frame.GetStatusBar().GetStatusText() == "No disponible"


def test_rapid_selection_keeps_only_latest_request(frame):
	scripts = []
	frame.live.view = SimpleNamespace(RunScriptAsync=scripts.append, Stop=lambda: None)
	for target in ["Temporada 2", "Temporada 3"]:
		frame.season_choice.SetStringSelection(target)
		frame._select_episode_content("season")
	assert len(scripts) == 2
	assert frame._selector_pending["request"] == 2
	assert frame._selector_pending["target"] == "Temporada 3"
	assert frame.lista.GetItemText(0) == "Episodio 1", "Las filas anteriores siguen disponibles mientras se confirma la carga."


def test_favorites_cancel_season_loading_and_disable_its_controls(frame):
	frame.live.loading_all = True
	frame._selector_pending = pending(started=time.monotonic())
	frame.section.SetStringSelection("Favoritos")
	frame._al_actualizar(None)
	assert not frame.live.loading_all
	assert frame._selector_pending is None
	assert not frame.season_choice.IsEnabled()
	assert not frame.episode_group.IsEnabled()


def test_collection_play_opens_the_collection_instead_of_empty_player(frame, monkeypatch):
	frame.titles = [Title("c", "Comedias", "Colección", "https://vix.com/ondemand/comedia")]
	frame._filter(None)
	opened = []
	monkeypatch.setattr(frame, "_navigate", opened.append)
	monkeypatch.setattr(frame, "_start_player", lambda *a: pytest.fail("Una colección no es un vídeo"))
	frame._play_selected(None)
	assert opened == ["https://vix.com/ondemand/comedia"]


def test_background_catalogue_does_not_overwrite_player_title(frame):
	frame.player.title.ChangeValue("Mi episodio")
	frame._live_snapshot(snapshot(title="Página de otra serie"))
	assert frame.player.title.GetValue() == "Mi episodio"
