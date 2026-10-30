"""Búsqueda global, lectura de enlaces y aislamiento de la cuenta."""
from app.services.live_site import catalogue_location, search_url, snapshot_titles, player_script

def test_global_search_encodes_query():
	assert search_url("  Corazón & drama  ") == "https://vix.com/es-es/search?q=Coraz%C3%B3n%20%26%20drama"

def test_account_and_login_are_never_scraped():
	for url in ["https://vix.com/es-es/account/mi-cuenta", "https://vix.com/es-es/iniciar-sesion", "https://evil.test/detail/series-1"]:
		assert not catalogue_location(url)
		assert snapshot_titles({"url": url, "items": [{"title": "Privado", "url": "https://vix.com/detail/series-1"}]}) == []

def test_episode_links_and_foreign_links():
	items = snapshot_titles({"url": "https://vix.com/es-es/detail/series-783", "items": [{"title": "Episodio completo", "url": "https://vix.com/video/video-42", "description": "EP. 1\n47 minutos"}, {"title": "Malo", "url": "https://evil.test/video/video-42"}]})
	assert len(items) == 1
	assert items[0].kind == "Episodio"
	assert "47 minutos" in items[0].description

def test_media_controls_do_not_extract_streams():
	assert "v.pause()" in player_script("toggle")
	assert "seekable" in player_script("forward")
	assert "v.muted" in player_script("mute")
