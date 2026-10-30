"""Lee únicamente el catálogo incluido en las páginas públicas de ViX."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

ORIGIN = "https://vix.com"
SECTIONS = {
	"Inicio": "/es-es",
	"Novelas": "/es-es/ondemand/novelas",
	"Películas": "/es-es/ondemand/peliculas",
	"Series": "/es-es/ondemand/series",
	"En vivo": "/es-es/canales",
	"Deportes": "/es-es/deportes",
	"Noticias": "/es-es/noticias",
}


class CatalogueError(Exception):
	"""Error que se puede presentar al usuario sin datos privados."""


def safe_url(path: str) -> str:
	"""Impide que enlaces o favoritos manipulados abran otro servicio."""
	url = urljoin(ORIGIN + "/", path)
	parts = urlsplit(url)
	if parts.scheme != "https" or parts.netloc != "vix.com" or "\\" in url:
		raise ValueError("El enlace debe pertenecer a https://vix.com.")
	return url


@dataclass(frozen=True)
class Title:
	id: str
	title: str
	kind: str
	url: str
	description: str = ""
	year: str = ""
	genres: str = ""
	rating: str = ""
	groups: list[str] = field(default_factory=list)
	channel_number: str = ""
	now_playing: str = ""
	next_programme: str = ""
	programme_time: str = ""

	def details(self) -> str:
		kind = "Canal " + self.channel_number if self.channel_number else self.kind
		return "\n\n".join(filter(None, [self.title, " · ".join(filter(None, [kind, self.year, self.rating])), self.genres, self.description, self.url]))

	def to_dict(self) -> dict:
		return asdict(self)


class PageParser(HTMLParser):
	"""Extrae JSON de Next.js sin ejecutar scripts del sitio."""

	def __init__(self):
		super().__init__()
		self.in_data = False
		self.data: list[str] = []
		self.links: set[str] = set()

	def handle_starttag(self, tag, attrs):
		attrs = dict(attrs)
		if tag == "script":
			self.in_data = attrs.get("id") == "__NEXT_DATA__"
		if tag == "a" and attrs.get("href"):
			self.links.add(attrs["href"])

	def handle_endtag(self, tag):
		if tag == "script":
			self.in_data = False

	def handle_data(self, data):
		if self.in_data:
			self.data.append(data)


def parse_page(html: str, channels_only: bool = False) -> list[Title]:
	parser = PageParser()
	parser.feed(html)
	if not parser.data:
		raise CatalogueError("Esta página no incluye un catálogo legible. Puede abrirla en el navegador con Ctrl+B.")
	try:
		state = json.loads("".join(parser.data))["props"]["apolloState"]
	except (ValueError, KeyError, TypeError) as error:
		raise CatalogueError("ViX ha cambiado el formato de esta página. Abra el sitio con Ctrl+B.") from error
	if not isinstance(state, dict):
		raise CatalogueError("El catálogo recibido no es válido.")

	def resolve(value):
		return state.get(value.get("__ref"), value) if isinstance(value, dict) else {}

	channels = [v for v in state.values() if isinstance(v, dict) and v.get("__typename") == "EpgChannel"]
	result = {}
	for value in channels if channels_only else state.values():
		if not isinstance(value, dict):
			continue
		type_name = value.get("__typename")
		if type_name not in {"VideoContent", "EpgChannel", "UiPageCard"}:
			continue
		identifier = value.get("id", "")
		title = value.get("title") or value.get("name")
		if not title:
			continue
		if type_name == "EpgChannel":
			metadata = value.get("pageAnalyticsMetadata") or {}
			path = next((x.get("value") for x in metadata.get("keyValues", []) if x.get("key") == "screen_id"), None)
			kind = "Canal " + str(value.get("channelNumber", ""))
		elif type_name == "UiPageCard":
			path, kind = value.get("urlPath"), "Colección"
			identifier = path
		else:
			# Las rutas de detalle siguen el formato observado en enlaces públicos.
			short_id = identifier.replace(":mcp:", "-")
			path = next((p for p in sorted(parser.links) if urlsplit(p).path.endswith("/detail/" + short_id)), None)
			if not path and re.fullmatch(r"(?:series|video)-[0-9]+", short_id):
				path = "/detail/" + short_id
			kind = {"SERIES": "Serie", "MOVIE": "Película", "EPISODE": "Episodio"}.get(value.get("videoType"), "Vídeo")
		if not path:
			continue
		try:
			url = safe_url(path)
		except ValueError:
			continue
		genres = ", ".join(resolve(g).get("name", "") for g in value.get("genresV2", []))
		ratings = ", ".join(r.get("ratingValue", "") for r in value.get("ratings", []))
		result[url] = Title(str(identifier), str(title), kind, url, value.get("description") or "", str(value.get("copyrightYear") or ""), genres, ratings)
	if not result:
		raise CatalogueError("No se encontraron títulos enlazados en esta página. Abra ViX con Ctrl+B.")
	return list(result.values())


def fetch_page(path: str) -> list[Title]:
	url = safe_url(path)
	request = Request(url, headers={"User-Agent": "Mozilla/5.0 ViXClient/1.0", "Accept-Language": "es"})
	try:
		with urlopen(request, timeout=20) as response:
			if urlsplit(response.url).hostname != "vix.com":
				raise CatalogueError("ViX redirigió fuera del sitio. El servicio puede no estar disponible en su región.")
			body = response.read(5_000_001)
			if len(body) > 5_000_000:
				raise CatalogueError("La página supera el tamaño admitido.")
			return parse_page(body.decode("utf-8"), channels_only=urlsplit(url).path.endswith("/canales"))
	except (OSError, UnicodeError) as error:
		raise CatalogueError("No se pudo conectar con ViX. Compruebe Internet o abra el sitio con Ctrl+B.") from error


def filter_titles(titles: list[Title], query: str) -> list[Title]:
	def normalize(text):
		return "".join(c for c in unicodedata.normalize("NFD", text.casefold()) if not unicodedata.combining(c))
	words = normalize(query).split()
	return [t for t in titles if all(w in normalize(" ".join([t.title, t.genres, t.description, t.channel_number, t.now_playing, t.next_programme])) for w in words)]
