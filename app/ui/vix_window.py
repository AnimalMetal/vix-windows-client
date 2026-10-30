"""Navegación nativa del catálogo con reproducción en el sitio oficial."""

from __future__ import annotations

import logging
import time
import re
from datetime import datetime
from dataclasses import replace

import wx

from app.core import voz
from app.core.feedback import Feedback
from app.services.media import session_summary
from app.services.sections import section_help
from app.services.episode_navigation import discover_script, selection_script, selection_outcome
from app.services.live_guide import guide_titles
from app.ui.player_panel import PlayerPanel
from app.services.catalogue import SECTIONS, Title, filter_titles, safe_url
from app.services.live_site import catalogue_location, search_url, snapshot_titles
from app.ui.dialogo_texto import DialogoTexto, mostrar_error, mostrar_mensaje
from app.ui.site_panel import SitePanel
from app.ui.ventana_principal import VentanaPrincipal as BaseWindow

log = logging.getLogger(__name__)


class VentanaPrincipal(BaseWindow):
	"""Conserva registro, instancia única, ayuda y cierre del esqueleto."""

	def __init__(self, configuracion, instancia=None):
		self.titles = []
		self.visible_titles = []
		self._generation = 0
		self._loaded = False
		self._column = 0
		self._path = SECTIONS["Inicio"]
		self._browser_page = ""
		self._browser_titles = {}
		self._page_text = ""
		self._page_title = "Información de ViX"
		self._selectors = {}
		self._selector_pending = None
		self._selector_request = 0
		self._episode_urls = []
		self._identity = {"signedIn": None, "profile": ""}
		self._play_request = False
		self._play_started = 0
		self._player_mode = False
		self._updating_list = False
		self._ready_sound = False
		self._page_groups = []
		self._live_mode = False
		self._live_channels = {}
		self._playing_title = ""
		self._guide_updated = ""
		self.feedback = Feedback(configuracion)
		super().__init__(configuracion, instancia)
		self.Bind(wx.EVT_CHAR_HOOK, self._global_key)
		self.SetStatusText("Elija una sección o busque en todo ViX. F6 vuelve al catálogo; F8 abre el reproductor nativo.")
		from app.ui.dialogo_actualizacion import ControlActualizaciones
		self.actualizaciones = ControlActualizaciones(self, configuracion)

	def _crear_menus(self):
		super()._crear_menus()
		file_menu = self.GetMenuBar().GetMenu(0)
		file_menu.Delete(self.elementos_menu.pop("abrir").GetId())
		edit_menu = self.GetMenuBar().GetMenu(1)
		edit_menu.Delete(self.elementos_menu.pop("quitar").GetId())
		for name, label, help_text, handler in [
			("favorito", "Guardar o quitar &favorito\tCtrl+D", "Cambia el favorito local del título seleccionado.", self._favorite),
			("buscar", "&Buscar en todo ViX\tCtrl+F", "Lleva a la búsqueda completa de ViX.", lambda e: self.search.SetFocus()),
		]:
			menu = edit_menu
			item = menu.Append(wx.ID_ANY, label, help_text)
			self.elementos_menu[name] = item
			self.Bind(wx.EVT_MENU, handler, item)
		for name, label, help_text, handler in [
			("cuenta", "Mi &cuenta...", "Iniciar sesión y gestionar la cuenta de ViX.", self._account),
			("informacion", "&Información completa\tF4", "Lee la información de la página y sus episodios.", self._show_page_info),
			("vista", "Volver al &catálogo\tF6", "Vuelve al catálogo desde cualquier pantalla.", lambda e: self._return_catalogue()),
			("reproductor", "Reproductor &nativo\tF8", "Abre los controles nativos de reproducción.", lambda e: self._show_player()),
			("sesion", "Estado de &sesión\tF9", "Muestra si ha iniciado sesión y el perfil confirmado.", self._session_status),
			("cargar", "Cargar &más contenido\tCtrl+M", "Recorre la carga dinámica de la página actual; repita para detener.", self._load_all),
		]:
			menu = file_menu if name == "cuenta" else self.GetMenuBar().GetMenu(2)
			item = menu.Append(wx.ID_ANY, label, help_text)
			self.elementos_menu[name] = item
			self.Bind(wx.EVT_MENU, handler, item)

	def _crear_contenido(self):
		self.shell = wx.Panel(self)
		shell_layout = wx.BoxSizer(wx.VERTICAL)
		label = wx.StaticText(self.shell, label="&Cuenta y perfil de ViX:")
		self.account_status = wx.TextCtrl(self.shell, value=session_summary(self._identity), style=wx.TE_READONLY)
		self.account_status.SetHelpText("Estado de sesión y perfil confirmado por ViX. Permanece visible y se actualiza en silencio, sin anuncios al cambiar de pestaña. F9 permite consultarlo a petición. Conserva la última confirmación mientras se carga otra pantalla.")
		shell_layout.Add(label, 0, wx.LEFT | wx.TOP, self.FromDIP(6))
		shell_layout.Add(self.account_status, 0, wx.EXPAND | wx.ALL, self.FromDIP(6))
		self.notebook = wx.Notebook(self.shell)
		self.panel = wx.ScrolledWindow(self.notebook, style=wx.VSCROLL)
		self.panel.SetScrollRate(0, self.FromDIP(16))
		self.notebook.AddPage(self.panel, "Catálogo accesible")
		# El motor no es una pestaña ni entra en el recorrido de teclado normal.
		self.account_dialog = wx.Dialog(self, title="Mi cuenta", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		self.account_dialog.SetSize(self.FromDIP((900, 700)))
		account_layout = wx.BoxSizer(wx.VERTICAL)
		self.live = SitePanel(self.account_dialog, self._live_snapshot, self._site_status)
		self.live.on_command = self._site_command
		account_layout.Add(self.live, 1, wx.EXPAND)
		close_account = wx.Button(self.account_dialog, wx.ID_CANCEL, label="&Volver al cliente (F6)")
		close_account.SetHelpText("Cierra la gestión de cuenta y vuelve a los controles nativos conservando su sesión.")
		account_layout.Add(close_account, 0, wx.ALIGN_RIGHT | wx.ALL, self.FromDIP(8))
		self.account_dialog.SetEscapeId(wx.ID_CANCEL)
		self.account_dialog.SetSizer(account_layout)
		self.account_dialog.Layout()
		self.player = PlayerPanel(self.notebook, self.live, self._return_catalogue)
		self.notebook.AddPage(self.player, "Reproductor accesible")
		shell_layout.Add(self.notebook, 1, wx.EXPAND)
		self.shell.SetSizer(shell_layout)
		root = wx.BoxSizer(wx.VERTICAL)
		root.Add(self.shell, 1, wx.EXPAND)
		self.SetSizer(root)
		sizer = wx.BoxSizer(wx.VERTICAL)
		label = wx.StaticText(self.panel, label="&Sección:")
		self.section = wx.Choice(self.panel, choices=[*SECTIONS, "Favoritos"])
		self.section.SetSelection(0)
		self.section.SetHelpText("Seleccione una categoría para cargar sus títulos públicos. Favoritos se guarda en este equipo.")
		sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, self.FromDIP(8))
		sizer.Add(self.section, 0, wx.EXPAND | wx.ALL, self.FromDIP(8))
		label = wx.StaticText(self.panel, label="Gru&po de contenido:")
		self.group_label = label
		self.home_group = wx.Choice(self.panel, choices=["Todas las secciones"])
		self.home_group.SetSelection(0)
		self.home_group.SetHelpText("Separa las filas de Inicio, por ejemplo Seguir viendo, Recomendado para ti o Mi lista. Solo aparecen las filas que ViX ofrece en la categoría y sesión actuales. Elija una y luego vaya a Títulos.")
		self.home_group.Bind(wx.EVT_CHOICE, self._group_changed)
		sizer.Add(label, 0, wx.LEFT | wx.RIGHT, self.FromDIP(8))
		sizer.Add(self.home_group, 0, wx.EXPAND | wx.ALL, self.FromDIP(8))
		label = wx.StaticText(self.panel, label="Qué contiene esta sección:")
		self.group_description = wx.TextCtrl(self.panel, value=section_help("Todas las secciones"), style=wx.TE_READONLY | wx.TE_MULTILINE)
		self.group_description.SetHelpText("Explica la diferencia entre la fila seleccionada, las recomendaciones y el historial. El texto se puede copiar.")
		sizer.Add(label, 0, wx.LEFT | wx.RIGHT, self.FromDIP(8))
		sizer.Add(self.group_description, 0, wx.EXPAND | wx.ALL, self.FromDIP(8))
		label = wx.StaticText(self.panel, label="&Buscar en todo ViX:")
		self.search = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
		self.search.SetHelpText("Escriba un título, actor o tema y pulse Intro. Usa el buscador de ViX con la sesión del cliente; no se limita a los títulos cargados.")
		sizer.Add(label, 0, wx.LEFT | wx.RIGHT, self.FromDIP(8))
		sizer.Add(self.search, 0, wx.EXPAND | wx.ALL, self.FromDIP(8))
		self.search.Bind(wx.EVT_TEXT_ENTER, self._search_all)
		search_button = wx.Button(self.panel, label="Buscar en &ViX")
		search_button.SetHelpText("Ejecuta la búsqueda completa de ViX con el texto escrito arriba.")
		search_button.Bind(wx.EVT_BUTTON, self._search_all)
		sizer.Add(search_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, self.FromDIP(8))
		label = wx.StaticText(self.panel, label="&Temporada:")
		self.season_choice = wx.Choice(self.panel)
		self.season_choice.SetHelpText("Temporadas disponibles del título. Elija una con las flechas y sus episodios se cargarán sin perder las otras temporadas. Se consulta automáticamente al abrir una serie.")
		self.season_choice.Enable(False)
		self.season_choice.Bind(wx.EVT_CHOICE, lambda e: self._select_episode_content("season"))
		sizer.Add(label, 0, wx.LEFT | wx.RIGHT, self.FromDIP(8))
		sizer.Add(self.season_choice, 0, wx.EXPAND | wx.ALL, self.FromDIP(8))
		label = wx.StaticText(self.panel, label="&Grupo de episodios:")
		self.episode_group = wx.Choice(self.panel)
		self.episode_group.SetHelpText("Grupos de episodios de la temporada o título actual, cuando ViX divide la lista en rangos. Las temporadas se eligen en el control anterior.")
		self.episode_group.Enable(False)
		self.episode_group.Bind(wx.EVT_CHOICE, self._select_range)
		sizer.Add(label, 0, wx.LEFT | wx.RIGHT, self.FromDIP(8))
		sizer.Add(self.episode_group, 0, wx.EXPAND | wx.ALL, self.FromDIP(8))
		label = wx.StaticText(self.panel, label="&Filtrar títulos cargados:")
		self.query_label = label
		self.query = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
		self.query.SetHelpText("Filtra los títulos de esta sección por nombre, género o descripción; no busca en todo ViX. Intro lleva a los resultados.")
		sizer.Add(label, 0, wx.LEFT | wx.RIGHT, self.FromDIP(8))
		sizer.Add(self.query, 0, wx.EXPAND | wx.ALL, self.FromDIP(8))
		label = wx.StaticText(self.panel, label="Títu&los:")
		self.list_label = label
		self.lista = wx.ListCtrl(self.panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
		for i, (name, width) in enumerate([("Título", 330), ("Tipo", 110), ("Año", 65), ("Géneros", 220), ("Favorito", 80), ("Secciones", 230)]):
			self.lista.InsertColumn(i, name, width=self.FromDIP(width))
		self.lista.SetHelpText("Arriba y abajo seleccionan un título. Intro carga detalles y episodios. Los episodios abren el reproductor nativo. Ctrl+D cambia el favorito local. F4 lee la página completa; F6 vuelve al catálogo y F8 al reproductor. Izquierda, derecha y Ctrl+1 a Ctrl+6 leen columnas; la sexta indica sus secciones de Inicio.")
		self.lista.SetMinSize((-1, self.FromDIP(120)))
		self._list_mode = "catalogue"
		sizer.Add(label, 0, wx.LEFT | wx.RIGHT, self.FromDIP(8))
		sizer.Add(self.lista, 1, wx.EXPAND | wx.ALL, self.FromDIP(8))
		label = wx.StaticText(self.panel, label="&Descripción:")
		self.details = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
		self.details.SetHelpText("Descripción completa del título seleccionado. Se puede seleccionar y copiar.")
		self.details.SetMinSize((-1, self.FromDIP(80)))
		sizer.Add(label, 0, wx.LEFT | wx.RIGHT, self.FromDIP(8))
		sizer.Add(self.details, 1, wx.EXPAND | wx.ALL, self.FromDIP(8))
		buttons = wx.WrapSizer(wx.HORIZONTAL)
		for label, handler in [("&Abrir título / episodio", self._open_selected), ("&Reproducir", self._play_selected), ("&Información completa", self._show_page_info), ("Cargar &más / detener", self._load_all), ("Actualizar temporadas y gr&upos", self._ranges), ("Mi &cuenta", self._account), ("Guardar o &quitar favorito", self._favorite), ("Actuali&zar", self._al_actualizar)]:
			button = wx.Button(self.panel, label=label)
			button.SetHelpText(label.replace("&", "") + ". Se realiza dentro del cliente. Los favoritos son locales.")
			button.Bind(wx.EVT_BUTTON, handler)
			buttons.Add(button, 0, wx.ALL, self.FromDIP(4))
		sizer.Add(buttons, 0, wx.ALL, self.FromDIP(4))
		self.panel.SetSizer(sizer)
		self.section.Bind(wx.EVT_CHOICE, self._al_actualizar)
		self.query.Bind(wx.EVT_TEXT, self._filter)
		self.query.Bind(wx.EVT_TEXT_ENTER, lambda e: self._enfocar_lista())
		self.lista.Bind(wx.EVT_LIST_ITEM_SELECTED, self._selection)
		self.lista.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._open_selected)
		self.lista.Bind(wx.EVT_CONTEXT_MENU, self._al_menu_contextual)
		self.lista.Bind(wx.EVT_KEY_DOWN, self._column_key)

	def _column_key(self, event):
		key, modifiers = event.GetKeyCode(), event.GetModifiers()
		if modifiers == wx.MOD_NONE:
			row = self.lista.GetFirstSelected()
			if row == 0 and key == wx.WXK_UP:
				self.feedback.play("top")
			elif row >= 0 and row == self.lista.GetItemCount() - 1 and key == wx.WXK_DOWN:
				self.feedback.play("bottom")
		if modifiers == wx.MOD_CONTROL and ord("1") <= key <= ord("7"):
			self._column = key - ord("1")
		elif modifiers == wx.MOD_NONE and key in (wx.WXK_LEFT, wx.WXK_RIGHT):
			self._column = max(0, min(self.lista.GetColumnCount() - 1, self._column + (1 if key == wx.WXK_RIGHT else -1)))
		else:
			event.Skip()
			return
		title = self._selected()
		if not title:
			return
		row = self.lista.GetFirstSelected()
		values = self._row_values(title)
		if self._column >= len(values):
			self._column = len(values) - 1
			self.SetStatusText("Esta lista tiene " + str(len(values)) + " columnas.")
			return
		parts = []
		if self._config.obtener("vix.row_number", True):
			parts.append(f"Fila {row + 1}")
		if self._config.obtener("vix.column_name", True):
			parts.append(self.lista.GetColumn(self._column).GetText())
		if self._config.obtener("vix.column_content", True) or not parts:
			parts.append(values[self._column] or "Sin datos")
		message = ", ".join(parts)
		self.SetStatusText(message)
		voz.hablar(message, interrumpir=True)

	def mostrar(self):
		super().mostrar()
		if not self._loaded:
			self._loaded = True
			self.feedback.play("startup")
			self._al_actualizar(None)

	def _favorites(self):
		result = []
		for item in self._config.obtener("vix.favorites", []):
			try:
				title = Title(**item)
				safe_url(title.url)
				if title.kind == "Canal" and title.channel_number:
					title = replace(title, description="Canal guardado. Abra En vivo para consultar la programación actual.", now_playing="", next_programme="", programme_time="")
				result.append(title)
			except (TypeError, ValueError):
				log.warning("Se omitió un favorito no válido.")
		return result

	def _al_actualizar(self, event):
		self._generation += 1
		section = self.section.GetStringSelection()
		if section == "En vivo" and self._live_mode and self.live.view:
			if self._player_mode:
				self.SetStatusText("Se conserva la emisión. La guía utiliza la programación más reciente recibida de ViX.")
			else:
				self.live.allow_playback = False
				self.live.navigate(safe_url(SECTIONS["En vivo"]))
				self.live.restart_loading()
				self.SetStatusText("Actualizando la guía sin cambiar la categoría ni la selección.")
			return
		if section == "Favoritos":
			self._live_mode = False
			self.live.loading_all = False
			self._selector_pending = None
			self._sync_episode_controls([])
			self._page_groups = []
			self.home_group.SetSelection(0)
			self.titles = self._favorites()
			self._filter(None)
			return
		self._path = SECTIONS[section]
		self._navigate(self._path)

	def _filter(self, event):
		selected = self._selected()
		self._configure_list()
		self._sync_groups()
		group = self.home_group.GetStringSelection()
		group_titles = self.titles if group == self._all_groups_label() else [t for t in self.titles if group in t.groups]
		self.visible_titles = filter_titles(group_titles, self.query.GetValue())
		self._updating_list = True
		self.lista.Freeze()
		try:
			for i, title in enumerate(self.visible_titles):
				values = self._row_values(title)
				if i >= self.lista.GetItemCount():
					self.lista.InsertItem(i, values[0])
				elif self.lista.GetItemText(i) != values[0]:
					self.lista.SetItem(i, 0, values[0])
				for column, text in enumerate(values[1:], 1):
					if self.lista.GetItemText(i, column) != text:
						self.lista.SetItem(i, column, text)
			while self.lista.GetItemCount() > len(self.visible_titles):
				self.lista.DeleteItem(self.lista.GetItemCount() - 1)
			if self.visible_titles:
				i = next((i for i, t in enumerate(self.visible_titles) if selected and t.url == selected.url), 0)
				if self.lista.GetFocusedItem() != i:
					self.lista.Focus(i)
				if not self.lista.IsSelected(i):
					self.lista.Select(i)
		finally:
			self.lista.Thaw()
			self._updating_list = False
		self._selection(None)
		self.SetStatusText(f"{len(self.visible_titles)} títulos cargados. Ctrl+F busca en todo ViX. Ctrl+M continúa la carga. F6 vuelve al catálogo; F8 abre el reproductor.")

	def _configure_list(self):
		mode = "live" if self._live_mode else "catalogue"
		if mode == self._list_mode:
			return
		self.lista.ClearAll()
		self.group_label.SetLabel("Gru&po de canales:" if self._live_mode else "Gru&po de contenido:")
		self.query_label.SetLabel("&Filtrar canales o programas:" if self._live_mode else "&Filtrar títulos cargados:")
		self.list_label.SetLabel("Cana&les:" if self._live_mode else "Títu&los:")
		self.query.SetHelpText("Filtra por número, nombre del canal o programa actual y siguiente. El filtro se limita a los canales cargados y la categoría elegida." if self._live_mode else "Filtra los títulos cargados por nombre, género o descripción; no busca en todo ViX.")
		self.lista.SetHelpText("Canales en vivo. Intro reproduce el canal. Ctrl+1 lee número; Ctrl+2 canal; Ctrl+3 programa actual; Ctrl+4 horario local; Ctrl+5 próximo programa; Ctrl+6 categorías; Ctrl+7 favorito. F4 muestra la programación completa y Ctrl+D guarda o quita el favorito." if self._live_mode else "Lista de títulos. Intro abre el título o episodio. Ctrl+1 a Ctrl+6 lee columnas. F4 muestra información completa y Ctrl+D cambia el favorito.")
		columns = [("Número", 75), ("Canal", 220), ("Ahora", 260), ("Horario local", 180), ("A continuación", 260), ("Categorías", 160), ("Favorito", 80)] if self._live_mode else [("Título", 330), ("Tipo", 110), ("Año", 65), ("Géneros", 220), ("Favorito", 80), ("Secciones", 230)]
		for index, (name, width) in enumerate(columns):
			self.lista.InsertColumn(index, name, width=self.FromDIP(width))
		self._column = 0
		self._list_mode = mode

	def _row_values(self, title):
		favorite = "Sí" if any(t.url == title.url for t in self._favorites()) else "No"
		if self._live_mode:
			return [title.channel_number, title.title, title.now_playing, title.programme_time, title.next_programme, ", ".join(title.groups), favorite]
		return [title.title, title.kind, title.year, title.genres, favorite, ", ".join(title.groups)]

	def _sync_groups(self):
		selected = self.home_group.GetStringSelection()
		all_groups = self._all_groups_label()
		if selected in {"Todas las secciones", "Todos los canales"}:
			selected = all_groups
		groups = list(dict.fromkeys([all_groups, *self._page_groups, *(g for t in self.titles for g in t.groups)]))
		if self.home_group.GetStrings() != groups:
			self.home_group.Set(groups)
			self.home_group.SetStringSelection(selected if selected in groups else all_groups)
		self.group_description.ChangeValue("Categoría de canales: " + self.home_group.GetStringSelection() + ". Filtre por canal, número o programa. Horarios en la zona local del equipo. " + self._guide_updated + " F4 consulta la programación disponible." if self._live_mode else section_help(self.home_group.GetStringSelection()))

	def _all_groups_label(self):
		return "Todos los canales" if self._live_mode else "Todas las secciones"

	def _group_changed(self, event):
		self._filter(None)
		self.feedback.play("open")

	def _selected(self):
		i = self.lista.GetFirstSelected() if hasattr(self, "lista") else -1
		return self.visible_titles[i] if 0 <= i < len(self.visible_titles) else None

	def _selection(self, event):
		title = self._selected()
		text = title.details() if title else "No hay títulos seleccionados."
		if self.details.GetValue() != text:
			self.details.ChangeValue(text)
		if event is not None and not self._updating_list:
			row = self.lista.GetFirstSelected()
			if row == 0:
				self.feedback.play("top")
			elif row >= 0 and row == self.lista.GetItemCount() - 1:
				self.feedback.play("bottom")

	def _texto_fila(self, indice):
		# Conserva el texto íntegro aunque Windows recorte una celda larga.
		if 0 <= indice < len(self.visible_titles):
			title = self.visible_titles[indice]
			return "\t".join([*self._row_values(title), title.url])
		return ""

	def _open_selected(self, event):
		title = self._selected()
		if title:
			if self.section.GetStringSelection() == "Favoritos":
				self.section.SetSelection(0)
			self.query.ChangeValue("")
			if "/video/" in title.url or "/canales/" in title.url:
				self._start_player(title.url, title.title)
			else:
				self._navigate(title.url)

	def _site_status(self, text):
		if self and not self._saliendo:
			self.SetStatusText(text)
			if text.startswith("No se pudo"):
				self.feedback.play("error")

	def _navigate(self, url):
		try:
			self._player_mode = False
			self._play_request = False
			self._ready_sound = False
			self.feedback.play("open")
			url = safe_url(url)
			self._live_mode = "/canales" in url
			self._live_channels = {}
			self._path = url
			self._browser_page = ""
			self._browser_titles = {}
			self._page_text = ""
			self._page_title = "Información de ViX"
			self._page_groups = []
			self.home_group.SetSelection(0)
			self._selectors = {}
			self._selector_pending = None
			self._episode_urls = []
			self.season_choice.Clear()
			self.season_choice.Enable(False)
			self.episode_group.Clear()
			self.episode_group.Enable(False)
			self.titles = []
			self._filter(None)
			self.live.allow_playback = False
			self.live.navigate(url)
			self.live.loading_all = catalogue_location(url)
			self.notebook.SetSelection(0)
			self.SetStatusText("Cargando ViX…")
		except (RuntimeError, ValueError) as error:
			mostrar_error(self, str(error), "ViX integrado")

	def _live_snapshot(self, data):
		url = data.get("url", "")
		identity = data.get("identity")
		if identity and identity.get("signedIn") is not None:
			if identity.get("signedIn") and not identity.get("profile") and self._identity.get("signedIn"):
				identity = {**identity, "profile": self._identity.get("profile", "")}
			if identity != self._identity:
				self._identity = identity
				text = session_summary(identity)
				self.account_status.ChangeValue(text)
		media = data.get("media") if self.live.allow_playback else None
		self.player.update(media, self._playing_title if media and media.get("isLive") else data.get("title", "") if media or self._player_mode else "")
		if self._play_request and not media and re.search(r"Ver ahora|Reproducir|Continuar viendo", data.get("text", ""), re.IGNORECASE):
			self._play_request = False
			self.live.view.RunScriptAsync("(() => {const b=[...document.querySelectorAll('button,a')].find(e=>e.getClientRects().length&&/^(ver ahora|reproducir|continuar viendo)$/i.test(e.innerText.trim()));if(b){b.click();return 'Iniciando reproducción'}return 'ViX no puede iniciar este título. Compruebe su acceso en Mi cuenta.';})()")
		if self._player_mode and not media and time.monotonic() - self._play_started > 30:
			self.player.status.ChangeValue("ViX no ha iniciado el vídeo. Compruebe su acceso en Mi cuenta o elija otro título. F6 vuelve al catálogo.")
		if self._live_mode and "/canales" in url:
			self._sync_episode_controls([])
			for channel in data.get("guide", []):
				self._live_channels[channel["id"]] = channel
			self._page_groups = data.get("liveCategories", [])
			if data.get("guideUpdated"):
				self._guide_updated = "Guía recibida a las " + datetime.fromtimestamp(data["guideUpdated"] / 1000).astimezone().strftime("%H:%M") + "."
			new_titles = guide_titles(list(self._live_channels.values()))
			if new_titles != self.titles:
				self.titles = new_titles
				self._filter(None)
				if self.titles and not self._ready_sound:
					self._ready_sound = True
					self.feedback.play("ready")
			self._page_text = "Guía de canales. Seleccione un canal y pulse F4 para consultar su programación en hora local."
			self._page_title = "Guía de canales"
			return
		if self._player_mode:
			return
		if not catalogue_location(url) or self.section.GetStringSelection() == "Favoritos":
			return
		selection_error = ""
		if self._selector_pending:
			outcome, selection_error = selection_outcome(self._selector_pending, data, time.monotonic())
			if outcome == "waiting":
				return
			self._selector_pending = None
			if outcome == "ready":
				self._browser_titles = {}
				self._page_groups = []
				self.home_group.SetSelection(0)
				self.query.ChangeValue("")
				self.live.restart_loading()
		if self._browser_page != url:
			self._browser_page = url
			self._browser_titles = {}
			self._page_groups = []
			self.home_group.SetSelection(0)
			self.titles = []
			self._path = url
		self._page_text = data.get("text", "")
		self._page_title = data.get("title", "Información de ViX")
		groups = list(dict.fromkeys([*self._page_groups, *data.get("groups", [])]))
		groups_changed = groups != self._page_groups
		self._page_groups = groups
		self._sync_episode_controls(data.get("selectors", []))
		self._episode_urls = data.get("episodeUrls", [])
		before = list(self._browser_titles.values())
		for title in snapshot_titles(data):
			previous = self._browser_titles.get(title.url)
			if previous:
				title = replace(title, groups=list(dict.fromkeys([*previous.groups, *title.groups])))
			self._browser_titles[title.url] = title
		if before != list(self._browser_titles.values()) or groups_changed:
			self.titles = list(self._browser_titles.values())
			self._filter(None)
			if not self._ready_sound and self.titles:
				self._ready_sound = True
				self.feedback.play("ready")
		if self._page_text and not self.visible_titles:
			self.details.ChangeValue(self._page_text)
		if selection_error:
			self.SetStatusText(selection_error)
			self.feedback.play("error")

	def _sync_episode_controls(self, selectors):
		self._selectors = {s["kind"]: s for s in selectors if s.get("kind") in {"season", "episodes"}}
		for kind, control in [("season", self.season_choice), ("episodes", self.episode_group)]:
			selector = self._selectors.get(kind)
			if not selector:
				control.Clear()
				control.Enable(False)
				continue
			options = list(dict.fromkeys(selector.get("options", []) or [selector["selected"]]))
			if control.GetStrings() != options:
				control.Set(options)
			if control.GetStringSelection() != selector.get("selected"):
				control.SetStringSelection(selector.get("selected", ""))
			control.Enable(True)

	def _search_all(self, event):
		query = self.search.GetValue().strip()
		if not query:
			self.SetStatusText("Escriba algo para buscar en ViX.")
			return
		if self.section.GetStringSelection() == "Favoritos":
			self.section.SetSelection(0)
		self.query.ChangeValue("")
		self._navigate(search_url(query))

	def _account(self, event):
		try:
			browse_path = self._path
			self._player_mode = False
			self._play_request = False
			self.live.allow_playback = False
			self._selector_pending = None
			self._sync_episode_controls([])
			self.live.navigate(safe_url("/es-es/account/mi-cuenta"))
			self.feedback.play("open")
			self.account_dialog.CentreOnParent()
			wx.CallAfter(self._focus_account)
			self.account_dialog.ShowModal()
			self.account_dialog.Hide()
			if self.notebook.GetSelection() == 1:
				self._show_player()
			else:
				self._browser_page = ""
				self._browser_titles = {}
				self.live.navigate(safe_url(browse_path))
				self.live.restart_loading()
				self._return_catalogue()
		except RuntimeError as error:
			mostrar_error(self, str(error), "Mi cuenta")

	def _focus_account(self):
		if self.account_dialog and self.account_dialog.IsShown() and self.live.view:
			self.live.view.SetFocus()

	def _close_account(self):
		if self.account_dialog.IsModal():
			self.account_dialog.EndModal(wx.ID_CANCEL)
		self.account_dialog.Hide()

	def _return_catalogue(self):
		self._close_account()
		if self.IsFullScreen():
			self.ShowFullScreen(False)
		self.notebook.SetSelection(0)
		self._enfocar_lista()
		self.feedback.play("back")
		self.SetStatusText("Catálogo. F8 vuelve al reproductor; el vídeo conserva su estado.")

	def _show_player(self):
		self._close_account()
		self.notebook.SetSelection(1)
		(self.player.play_button if self.player.play_button.IsEnabled() else self.player.return_button).SetFocus()

	def _site_command(self, command):
		if command == "catalogue":
			self._return_catalogue()
		elif command == "player":
			self._show_player()

	def _global_key(self, event):
		if not event.HasAnyModifiers() and event.GetKeyCode() == wx.WXK_F6:
			self._return_catalogue()
		elif not event.HasAnyModifiers() and event.GetKeyCode() == wx.WXK_F8:
			self._show_player()
		elif not event.HasAnyModifiers() and event.GetKeyCode() == wx.WXK_ESCAPE and self.notebook.GetSelection() == 1:
			self._return_catalogue()
		else:
			event.Skip()

	def _session_status(self, event=None):
		text = session_summary(self._identity)
		voz.hablar(text, interrumpir=True)
		mostrar_mensaje(self, text, "Cuenta y perfil de ViX")

	def _start_player(self, url, title=""):
		try:
			self._player_mode = True
			self._playing_title = title
			self._play_started = time.monotonic()
			self._play_request = "/detail/" in url
			self.player.update(None, title)
			self.live.allow_playback = True
			self.live.navigate(safe_url(url))
			self._show_player()
			self.feedback.play("open")
		except (RuntimeError, ValueError) as error:
			self._player_mode = False
			mostrar_error(self, str(error), "Reproductor")

	def _show_page_info(self, event):
		selected = self._selected()
		text = selected.details() if selected and selected.kind == "Canal" else self._page_text or (selected.details() if selected else "Abra un título o una sección para leer su información completa.")
		title = selected.title + " · Programación" if selected and selected.kind == "Canal" else self._page_title
		with DialogoTexto(self, title, "&Información:", text, copiable=True) as dialog:
			dialog.ShowModal()

	def _load_all(self, event):
		self.live.load_all(event)

	def _ranges(self, event):
		if self.live.view:
			self.live.view.RunScriptAsync(discover_script(force=True))
			self.SetStatusText("Actualizando las temporadas y los grupos de episodios disponibles.")

	def _select_range(self, event):
		self._select_episode_content("episodes")

	def _select_episode_content(self, kind):
		control = self.season_choice if kind == "season" else self.episode_group
		target = control.GetStringSelection()
		selector = self._selectors.get(kind)
		if not selector or not target or not self.live.view or target == selector.get("selected"):
			return
		self.live.loading_all = False
		self._selector_request += 1
		self._selector_pending = {"request": self._selector_request, "selector": selector["id"], "target": target, "before": list(self._episode_urls), "started": time.monotonic()}
		self.live.view.RunScriptAsync(selection_script(selector["id"], target, self._selector_request))
		self.SetStatusText("Cargando " + target + "…")

	def _play_selected(self, event):
		title = self._selected()
		if title:
			if title.kind == "Colección":
				self._navigate(title.url)
			else:
				self._start_player(title.url, title.title)

	def _al_cerrar(self, event):
		if not (not self._forzar_salida and event.CanVeto() and self._config.obtener("general.cerrar_a_bandeja", False)):
			self.live.stop()
			self.account_dialog.Destroy()
		super()._al_cerrar(event)

	def _favorite(self, event):
		title = self._selected()
		if not title:
			return
		favorites = self._favorites()
		found = any(t.url == title.url for t in favorites)
		favorites = [t for t in favorites if t.url != title.url] if found else [*favorites, title]
		previous = self._config.obtener("vix.favorites", [])
		self._config.establecer("vix.favorites", [t.to_dict() for t in favorites])
		if not self._config.guardar():
			self._config.establecer("vix.favorites", previous)
			mostrar_error(self, "No se pudo guardar el favorito. Compruebe que data permite escritura.", "Favoritos")
			return
		if self.section.GetStringSelection() == "Favoritos":
			self.titles = favorites
		self._filter(None)
		message = "Favorito quitado." if found else "Favorito guardado."
		self.SetStatusText(message)
		voz.hablar(message)

	def _al_menu_contextual(self, event):
		menu = wx.Menu()
		for label, handler in [("&Abrir título / episodio", self._open_selected), ("&Reproducir", self._play_selected), ("Guardar o &quitar favorito", self._favorite)]:
			item = menu.Append(wx.ID_ANY, label)
			menu.Bind(wx.EVT_MENU, handler, item)
		try:
			position = event.GetPosition()
			if position == wx.DefaultPosition:
				index = self.lista.GetFocusedItem()
				rect = self.lista.GetItemRect(index) if index >= 0 else wx.Rect(0, 0, 0, 0)
				position = wx.Point(rect.x + self.FromDIP(20), rect.y + rect.height)
			else:
				position = self.lista.ScreenToClient(position)
			self.lista.PopupMenu(menu, position)
		finally:
			menu.Destroy()

	def abrir_archivos(self, rutas):
		mostrar_mensaje(self, "Use las secciones para navegar por ViX. Este cliente no abre archivos locales.", "ViX Client")
