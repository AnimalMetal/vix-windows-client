"""Pantalla de reproducción exclusivamente con controles nativos accesibles."""
import wx

from app.core import voz
from app.services.media import media_summary, value_script


class PlayerPanel(wx.ScrolledWindow):
	def __init__(self, parent, engine, return_to_catalogue):
		super().__init__(parent, style=wx.VSCROLL)
		self.SetScrollRate(0, self.FromDIP(16))
		self.engine = engine
		self.media = None
		self._audio = []
		self._subtitles = []
		self._last_state = None
		layout = wx.BoxSizer(wx.VERTICAL)
		self.return_button = wx.Button(self, label="&Volver al catálogo (F6 o Escape)")
		self.return_button.SetHelpText("Vuelve al catálogo conservando la selección y la reproducción. Para detener el vídeo use Detener reproducción.")
		self.return_button.Bind(wx.EVT_BUTTON, lambda e: return_to_catalogue())
		layout.Add(self.return_button, 0, wx.ALL, self.FromDIP(8))
		label = wx.StaticText(self, label="&Título en reproducción:")
		self.title = wx.TextCtrl(self, style=wx.TE_READONLY)
		self.title.SetHelpText("Título del vídeo que se está reproduciendo.")
		layout.Add(label, 0, wx.LEFT, self.FromDIP(8))
		layout.Add(self.title, 0, wx.EXPAND | wx.ALL, self.FromDIP(8))
		label = wx.StaticText(self, label="&Estado y tiempo:")
		self.status = wx.TextCtrl(self, style=wx.TE_READONLY)
		self.status.SetHelpText("Estado, tiempo transcurrido, duración y volumen. El botón Consultar estado lo anuncia a petición.")
		layout.Add(label, 0, wx.LEFT, self.FromDIP(8))
		layout.Add(self.status, 0, wx.EXPAND | wx.ALL, self.FromDIP(8))
		buttons = wx.WrapSizer(wx.HORIZONTAL)
		self.play_button = None
		self.control_buttons = []
		for label, action in [("&Reproducir o pausar", "toggle"), ("Retroceder &10 segundos", "back"), ("Avanzar 1&0 segundos", "forward"), ("&Silenciar o activar sonido", "mute"), ("&Bajar volumen", "quieter"), ("S&ubir volumen", "louder"), ("&Detener reproducción", "stop")]:
			button = wx.Button(self, label=label)
			button.Bind(wx.EVT_BUTTON, lambda e, command=action: engine.control(command))
			button.SetHelpText(label.replace("&", "") + ". Control de reproducción.")
			buttons.Add(button, 0, wx.ALL, self.FromDIP(4))
			self.control_buttons.append(button)
			if action == "toggle":
				self.play_button = button
		layout.Add(buttons, 0, wx.EXPAND | wx.ALL, self.FromDIP(4))
		self.live_edge = wx.Button(self, label="Ir al direct&o")
		self.live_edge.SetHelpText("Vuelve al punto más reciente de una emisión en vivo, si ViX permite desplazarse dentro de ella.")
		self.live_edge.Bind(wx.EVT_BUTTON, lambda e: engine.control("live"))
		layout.Add(self.live_edge, 0, wx.ALL, self.FromDIP(8))
		self.live_edge.Hide()
		label = wx.StaticText(self, label="&Posición en segundos:")
		self.seek = wx.SpinCtrl(self, min=0, max=864000)
		self.seek.SetHelpText("Escriba el segundo al que desea ir y pulse Ir. ViX puede restringir los saltos durante anuncios o emisiones en directo.")
		layout.Add(label, 0, wx.LEFT, self.FromDIP(8))
		layout.Add(self.seek, 0, wx.ALL, self.FromDIP(8))
		button = wx.Button(self, label="&Ir")
		self.seek_button = button
		button.Bind(wx.EVT_BUTTON, lambda e: self.change("seek", self.seek.GetValue()))
		layout.Add(button, 0, wx.LEFT | wx.BOTTOM, self.FromDIP(8))
		label = wx.StaticText(self, label="&Audio:")
		self.audio = wx.Choice(self)
		self.audio.SetHelpText("Pistas de audio disponibles para este vídeo. El selector permanece desactivado si ViX no ofrece pistas al cliente.")
		self.audio.Bind(wx.EVT_CHOICE, lambda e: self.change("audio", self.audio.GetSelection()))
		layout.Add(label, 0, wx.LEFT, self.FromDIP(8))
		layout.Add(self.audio, 0, wx.EXPAND | wx.ALL, self.FromDIP(8))
		label = wx.StaticText(self, label="Subtítu&los:")
		self.subtitles = wx.Choice(self)
		self.subtitles.SetHelpText("Activa o desactiva los subtítulos disponibles para este vídeo. El selector permanece desactivado si ViX no ofrece pistas al cliente.")
		self.subtitles.Bind(wx.EVT_CHOICE, lambda e: self.change("subtitle", self.subtitles.GetSelection() - 1))
		layout.Add(label, 0, wx.LEFT, self.FromDIP(8))
		layout.Add(self.subtitles, 0, wx.EXPAND | wx.ALL, self.FromDIP(8))
		for label, handler in [("&Consultar estado", self.announce), ("&Mi cuenta", lambda e: wx.GetTopLevelParent(self)._account(e))]:
			button = wx.Button(self, label=label)
			button.Bind(wx.EVT_BUTTON, handler)
			button.SetHelpText(label.replace("&", ""))
			layout.Add(button, 0, wx.ALL, self.FromDIP(8))
		self.SetSizer(layout)
		self.update(None)

	def update(self, media, title=""):
		self.media = media
		if title and self.title.GetValue() != title:
			self.title.ChangeValue(title)
		# El lector puede estar leyendo el tiempo: no se cambia el texto bajo su foco.
		if not self.status.HasFocus():
			self.status.ChangeValue(media_summary(media))
		for button in self.control_buttons:
			button.Enable(bool(media))
		self.play_button.SetLabel("&Reproducir" if media and media.get("paused") else "Pausa&r" if media else "&Reproducir o pausar")
		is_live = bool(media and media.get("isLive"))
		self.seek.Enable(bool(media) and not is_live)
		self.seek_button.Enable(bool(media) and not is_live)
		self.live_edge.Enable(is_live and media.get("canSeek", False))
		if self.live_edge.IsShown() != is_live:
			self.live_edge.Show(is_live)
			self.Layout()
			self.FitInside()
		for key, control, current in [("audio", self.audio, self._audio), ("subtitles", self.subtitles, self._subtitles)]:
			tracks = (media or {}).get(key, [])
			labels = [t.get("label") or t.get("language") or f"Pista {i + 1}" for i, t in enumerate(tracks)]
			if labels != current:
				control.Set((["Desactivados"] if key == "subtitles" else []) + labels)
				setattr(self, "_" + key, labels)
			control.Enable(bool(labels))
			selected = next((i for i, t in enumerate(tracks) if t.get("mode") == "showing" or t.get("enabled")), -1)
			if not control.HasFocus():
				control.SetSelection(selected + 1 if key == "subtitles" else max(0, selected) if labels else wx.NOT_FOUND)
		state = None if not media else (media.get("paused"), media.get("ended"), bool(media.get("error")))
		if state != self._last_state and media and not self.play_button.HasFocus():
			voz.hablar("Error de reproducción. " + media["error"] if media.get("error") else "Reproducción finalizada." if media.get("ended") else "En pausa." if media.get("paused") else "Reproduciendo.")
		self._last_state = state

	def change(self, kind, value):
		if self.engine.view:
			self.engine.view.RunScriptAsync(value_script(kind, value))

	def announce(self, event=None):
		text = media_summary(self.media)
		self.status.ChangeValue(text)
		voz.hablar(text, interrumpir=True)
