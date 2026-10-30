"""Sesión WebView2 integrada para el sitio, cuenta y reproductor oficiales."""
from __future__ import annotations

import json
import logging
import os
from urllib.parse import urlsplit

import wx
import wx.html2 as html2

from app.core import paths
from app.services.live_site import SNAPSHOT_SCRIPT, LOAD_MORE_SCRIPT, catalogue_location, player_script
from app.services.media import KEY_BRIDGE_SCRIPT, IDENTITY_OBSERVER_SCRIPT
from app.services.episode_navigation import discover_script
from app.services.live_guide import GUIDE_RUNTIME, BROWSE_MEDIA_GUARD

log = logging.getLogger(__name__)


class SitePanel(wx.Panel):
	def __init__(self, parent, on_snapshot, on_status):
		super().__init__(parent)
		self.on_snapshot = on_snapshot
		self.on_status = on_status
		self.view = None
		self.on_command = lambda command: None
		self.allow_playback = False
		self._message_handler = False
		self.loading_all = False
		self._quiet = 0
		self._known = set()
		self._url = ""
		self._requested_url = ""
		self._pending = False
		self._page_ready = False
		self._pending_since = 0
		self._selector_attempts = {}
		self._root = wx.BoxSizer(wx.VERTICAL)
		self.SetSizer(self._root)
		self.timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self._tick, self.timer)

	def ensure_view(self):
		if self.view:
			return
		if not html2.WebView.IsBackendAvailable(html2.WebViewBackendEdge):
			raise RuntimeError("Se necesita Microsoft Edge WebView2 Runtime para el sitio integrado.")
		# El perfil es propio de esta copia; no se importa el del navegador del usuario.
		os.environ["WEBVIEW2_USER_DATA_FOLDER"] = str(paths.subcarpeta("sessions") / "webview2")
		self.view = html2.WebView.New(self, backend=html2.WebViewBackendEdge)
		self.SetSize(self.GetParent().GetClientSize())
		self.view.SetMinSize(self.FromDIP((400, 250)))
		self.view.SetHelpText("Gestión de cuenta de ViX. Tab recorre los formularios. F6 vuelve al catálogo y F8 al reproductor.")
		self._root.Add(self.view, 1, wx.EXPAND)
		self.view.Bind(html2.EVT_WEBVIEW_NAVIGATING, self._navigating)
		self.view.Bind(html2.EVT_WEBVIEW_NAVIGATED, self._navigated)
		self.view.Bind(html2.EVT_WEBVIEW_LOADED, self._loaded)
		self.view.Bind(html2.EVT_WEBVIEW_ERROR, self._error)
		self.view.Bind(html2.EVT_WEBVIEW_NEWWINDOW, self._new_window)
		self.view.Bind(html2.EVT_WEBVIEW_SCRIPT_RESULT, self._script_result)
		self.view.Bind(html2.EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED, self._message)
		self.view.Bind(wx.EVT_CHAR_HOOK, self._key)
		self.Layout()
		self.timer.Start(1200)

	def navigate(self, url):
		self.ensure_view()
		self.end_episode_selection()
		if self._message_handler:
			self.view.RemoveScriptMessageHandler("vixclient")
		self.view.RemoveAllUserScripts()
		self._message_handler = self.view.AddScriptMessageHandler("vixclient")
		if not self._message_handler:
			log.warning("No se pudo instalar el puente de teclado de la cuenta.")
		self.view.AddUserScript("window.__vixClientPlaybackAllowed=" + ("true" if self.allow_playback else "false") + ";" + BROWSE_MEDIA_GUARD)
		self.view.AddUserScript(KEY_BRIDGE_SCRIPT)
		self.view.AddUserScript(GUIDE_RUNTIME)
		self.view.AddUserScript(IDENTITY_OBSERVER_SCRIPT)
		self._requested_url = url
		self.loading_all = False
		self._page_ready = False
		self._known.clear()
		self._quiet = 0
		self._selector_attempts.clear()
		self.view.LoadURL(url)

	def _navigating(self, event):
		url = event.GetURL()
		if urlsplit(url).scheme not in {"https", "about"}:
			event.Veto()
			self.on_status("El sitio intentó abrir un enlace externo que este cliente no admite.")
			return
		event.Skip()

	def _navigated(self, event):
		if event.GetURL() and event.GetURL() != self.view.GetCurrentURL():
			return
		self._url = event.GetURL()
		self._page_ready = False
		self._pending = False
		self._known.clear()
		self._quiet = 0
		self.on_status("Cargando contenido de ViX…")

	def _loaded(self, event):
		self._page_ready = True
		self.on_status("Contenido cargado. F6 vuelve al catálogo; F8 abre el reproductor.")

	def _error(self, event):
		if event.GetURL() and event.GetURL() not in {self.view.GetCurrentURL(), self._requested_url}:
			return
		self.on_status("No se pudo cargar contenido de ViX. Compruebe la conexión y actualice la categoría.")

	def _new_window(self, event):
		# Los enlaces de cuenta permanecen dentro de la sesión de la aplicación.
		url = event.GetURL()
		if urlsplit(url).scheme == "https":
			wx.CallAfter(self.navigate, url)

	def _tick(self, event):
		# ViX puede dejar recursos publicitarios pendientes aunque el catálogo ya esté listo.
		if not self.view:
			return
		import time
		if self._pending and time.monotonic() - self._pending_since < 10:
			return
		self._pending = True
		self._pending_since = time.monotonic()
		self.view.RunScriptAsync(SNAPSHOT_SCRIPT)

	def _script_result(self, event):
		try:
			data = json.loads(event.GetString())
		except (ValueError, TypeError):
			if event.GetString() and event.GetString() != "more":
				self.on_status(event.GetString())
			return
		self._pending = False
		if not isinstance(data, dict):
			return
		if data.get("type") == "player-feedback":
			self.on_status(data.get("text", ""))
			return
		if data.get("url") != self.view.GetCurrentURL():
			return
		self._url = data.get("url", "")
		self.on_snapshot(data)
		season = next((s.get("selected", "") for s in data.get("selectors", []) if s.get("kind") == "season"), "")
		missing = [s for s in data.get("selectors", []) if not s.get("discovered")]
		keys = [(s.get("id"), season) for s in missing]
		if keys and any(self._selector_attempts.get(key, 0) < 3 for key in keys):
			for key in keys:
				self._selector_attempts[key] = self._selector_attempts.get(key, 0) + 1
			self.view.RunScriptAsync(discover_script())
		if self.loading_all and catalogue_location(self._url):
			known = {item.get("url") for item in data.get("items", [])}
			new = known - self._known
			self._known.update(known)
			self._quiet = 0 if new else self._quiet + 1
			if self._quiet >= 8:
				self.loading_all = False
				self.on_status(f"La página dejó de ofrecer títulos nuevos. {len(self._known)} enlaces recorridos. Puede continuar por colecciones, temporadas o búsqueda.")
			else:
				self.view.RunScriptAsync(LOAD_MORE_SCRIPT)
				self.on_status(f"Cargando más contenido de la página… {len(self._known)} enlaces encontrados. Vuelva a pulsar Cargar más para detener.")

	def load_all(self, event=None):
		if not self.view:
			return
		if not catalogue_location(self._url):
			self.on_status("La carga de catálogo solo se usa en categorías, búsqueda y detalles; no en la cuenta o el reproductor.")
			return
		self.loading_all = not self.loading_all
		self._quiet = 0
		self.on_status("Carga continua iniciada." if self.loading_all else "Carga continua detenida.")

	def restart_loading(self):
		self._known.clear()
		self._quiet = 0
		self.loading_all = True

	def begin_episode_selection(self):
		"""Consultar pronto la primera página, sin acelerar la carga del resto del catálogo."""
		self.timer.Start(200)

	def end_episode_selection(self):
		if self.timer.IsRunning():
			self.timer.Start(1200)

	def control(self, action):
		if self.view and urlsplit(self.view.GetCurrentURL()).hostname == "vix.com":
			self.view.RunScriptAsync(player_script(action))

	def back(self, event=None):
		if self.view and self.view.CanGoBack():
			self.view.GoBack()

	def forward(self, event=None):
		if self.view and self.view.CanGoForward():
			self.view.GoForward()

	def reload(self, event=None):
		if self.view:
			self.view.Reload()

	def native(self, event=None):
		self.on_command("catalogue")

	def _message(self, event):
		try:
			command = json.loads(event.GetString()).get("command")
		except (ValueError, AttributeError):
			return
		if command in {"catalogue", "player"}:
			self.on_command(command)

	def stop(self):
		self.timer.Stop()
		if self.view:
			self.view.Stop()

	def _key(self, event):
		if event.GetKeyCode() == wx.WXK_F6 and not event.HasAnyModifiers():
			self.native()
		elif event.GetKeyCode() == wx.WXK_F8 and not event.HasAnyModifiers():
			self.on_command("player")
		else:
			event.Skip()
