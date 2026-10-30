"""Contrato del HTML público y límites de los enlaces."""
import json
import pytest
from app.services.catalogue import CatalogueError, Title, filter_titles, parse_page, safe_url

def page(state):
	return '<script type="application/json" id="__NEXT_DATA__">' + json.dumps({"props": {"apolloState": state}}) + '</script>'

def test_catalogue_resolves_genres_and_deduplicates():
	video = {"__typename": "VideoContent", "id": "series:mcp:42", "title": "Corazón", "videoType": "SERIES", "genresV2": [{"__ref": "genre"}], "description": "Descripción íntegra"}
	items = parse_page(page({"one": video, "duplicate": video, "genre": {"name": "Drama"}}))
	assert len(items) == 1
	assert items[0].url == "https://vix.com/detail/series-42"
	assert items[0].genres == "Drama"
	assert "Descripción íntegra" in items[0].details()

def test_live_channel_destination():
	channel = {"__typename": "EpgChannel", "title": "Noticias", "id": "channel:1", "channelNumber": 100, "pageAnalyticsMetadata": {"keyValues": [{"key": "screen_id", "value": "/canales/channel-callsign-test"}]}}
	items = parse_page(page({"channel": channel}), channels_only=True)
	assert items[0].kind == "Canal 100"
	assert items[0].url.endswith("/canales/channel-callsign-test")

@pytest.mark.parametrize("html", ["<html>Access denied</html>", '<script id="__NEXT_DATA__">bad json</script>', page({})])
def test_page_changes_fail_with_actionable_message(html):
	with pytest.raises(CatalogueError, match="Ctrl\\+B"):
		parse_page(html)

@pytest.mark.parametrize("url", ["https://vix.com.evil.test", "javascript:alert(1)", "https://vix.com@evil.test", "//evil.test", "http://vix.com", "https://vix.com:443/"])
def test_rejects_foreign_or_non_https_links(url):
	with pytest.raises(ValueError):
		safe_url(url)

def test_filter_ignores_accents_and_case():
	title = Title("1", "Corazón", "Serie", "https://vix.com", genres="Comedia")
	assert filter_titles([title], "CORAZON comedia") == [title]
	assert filter_titles([title], "inexistente") == []
