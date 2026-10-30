"""Horarios, cambios de emisión y navegación de la guía nativa."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.live_guide import guide_titles, local_range
from app.services.catalogue import filter_titles
from app.services.media import media_summary
from app.core.config import Configuracion
from app.ui.vix_window import VentanaPrincipal
from .conftest import procesar_eventos


def channel(number="330", name="Vecinos", now=None, **changes):
	now = now or datetime.now(timezone.utc)
	return {"id": "channel:" + number, "title": name, "number": int(number), "url": "https://vix.com/canales/channel-callsign-test" + number, "groups": ["Top", "Humor"], "schedule": [
		{"title": "Programa pasado", "start": (now-timedelta(hours=2)).isoformat(), "end": (now-timedelta(hours=1)).isoformat()},
		{"title": "Vecinos: el estreno", "start": (now-timedelta(minutes=5)).isoformat(), "end": (now+timedelta(minutes=15)).isoformat()},
		{"title": "Siguiente episodio", "start": (now+timedelta(minutes=15)).isoformat(), "end": (now+timedelta(minutes=45)).isoformat()},
	], **changes}


def test_current_and_next_use_actual_intervals_not_first_schedule_item():
	now = datetime(2026, 10, 30, 15, 0, tzinfo=timezone.utc)
	title = guide_titles([channel(now=now)], now)[0]
	assert title.now_playing == "Vecinos: el estreno"
	assert title.next_programme == "Siguiente episodio"
	assert "Programa pasado" not in title.description
	assert "Horario no disponible" not in title.programme_time
	assert filter_titles([title], "330") == [title]
	assert filter_titles([title], "estreno") == [title]


def test_expired_or_invalid_schedules_are_explicit():
	now = datetime(2026, 10, 30, 15, 0, tzinfo=timezone.utc)
	title = guide_titles([channel(now=now)], now + timedelta(days=1))[0]
	assert title.now_playing == "Programación actual no disponible"
	assert title.next_programme == "Próximo programa no disponible"
	assert local_range({"start": "bad", "end": None}) == "Horario no disponible"
	assert guide_titles([channel(url="https://evil.test/channel")]) == []


def test_channels_sort_numerically_and_blocked_status_is_visible():
	items = guide_titles([channel("330"), channel("20", "Canal dos", blocked=True)])
	assert [item.channel_number for item in items] == ["20", "330"]
	assert "restricciones" in items[0].description


@pytest.fixture
def frame(app_wx):
	window = VentanaPrincipal(Configuracion())
	window._live_mode = True
	window.section.SetStringSelection("En vivo")
	window._live_snapshot({"url": "https://vix.com/es-es/canales", "guide": [channel()], "liveCategories": ["Top", "Humor"]})
	yield window
	window.salir()
	procesar_eventos(lambda: not window)


def test_native_columns_category_filter_and_stable_selection(frame):
	assert [frame.lista.GetColumn(i).GetText() for i in range(frame.lista.GetColumnCount())] == ["Número", "Canal", "Ahora", "Horario local", "A continuación", "Categorías", "Favorito"]
	frame.home_group.SetStringSelection("Humor")
	frame._group_changed(None)
	frame.query.SetValue("330")
	assert frame.lista.GetItemCount() == 1
	assert frame.lista.GetItemText(0, 1) == "Vecinos"
	frame._live_snapshot({"url": "https://vix.com/es-es/canales", "guide": [channel(), channel("100", "Noticias")], "liveCategories": ["Top", "Humor"]})
	assert frame._selected().channel_number == "330"
	assert frame.home_group.GetStringSelection() == "Humor"
	assert frame.lista.GetFocusedItem() == 0


def test_live_player_does_not_show_epoch_time_or_absolute_seek(frame):
	media = {"isLive": True, "paused": False, "time": 1793373000, "duration": None, "volume": .5, "liveDelay": 2, "canSeek": True}
	text = media_summary(media)
	assert "En directo" in text and "Desconocida" not in text
	assert "1793373000" not in text
	frame.player.update(media, "Canal de prueba")
	assert not frame.player.seek.IsEnabled()
	assert frame.player.live_edge.IsEnabled()
	assert frame.player.live_edge.IsShown()
	assert "00:00:30" in media_summary({**media, "liveDelay": 30})


def test_refresh_while_playing_does_not_navigate_or_interrupt(frame, monkeypatch):
	frame._player_mode = True
	frame.live.view = SimpleNamespace(Stop=lambda: None)
	opened = []
	monkeypatch.setattr(frame.live, "navigate", opened.append)
	frame._al_actualizar(None)
	assert opened == []
	assert "conserva" in frame.GetStatusBar().GetStatusText()


def test_saved_channels_do_not_present_old_schedule_as_current(frame):
	frame._favorite(None)
	saved = frame._favorites()[0]
	assert saved.title == "Vecinos"
	assert saved.now_playing == ""
	assert "programación actual" in saved.description
