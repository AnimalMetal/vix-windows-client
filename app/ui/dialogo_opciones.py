"""Diálogo de opciones: ejemplo mínimo de diálogo accesible con Aceptar y Cancelar.

Patrón que se repite en cualquier diálogo nuevo:

- Casillas con ``&`` en su propia etiqueta (una ``CheckBox`` ya se nombra sola).
- Para un campo de texto, lista o desplegable, la ``StaticText`` va creada
  JUSTO ANTES del control.
- ``&Aceptar`` con ``wx.ID_OK`` (Intro) y ``&Cancelar`` con ``wx.ID_CANCEL``
  (Escape), en español y colocados por ``StdDialogButtonSizer``.
- Foco inicial en el primer control útil y ayuda para Ctrl+H.
"""

from __future__ import annotations

import builtins

import wx

from app.core.config import Configuracion


def _(texto: str) -> str:
	traducir = getattr(builtins, "_", None)
	return traducir(texto) if callable(traducir) else texto


# (clave de configuración, etiqueta, ayuda de Ctrl+H)
OPCIONES = [
	("sounds.enabled", "Sonidos &suaves de la interfaz", "Activa campanitas suaves al iniciar, abrir, volver y llegar a los límites de una lista. No cambia el volumen del vídeo."),
	("vix.row_number", "Leer &número de fila", "Incluye la fila al pedir la lectura de una columna con Ctrl+1 a Ctrl+5."),
	("vix.column_name", "Leer ca&becera de columna", "Incluye el nombre de la columna al pedir su lectura."),
	("vix.column_content", "Leer con&tenido de columna", "Incluye el contenido al pedir la lectura. Si desactiva todo, se leerá el contenido."),
	(
		"general.anunciar_arranque",
		"&Anunciar el arranque por voz",
		"Dice el nombre de la aplicación al abrirla, antes de que aparezca la ventana.",
	),
	(
		"general.minimizar_a_bandeja",
		"&Minimizar a la bandeja del sistema",
		"Al minimizar, la ventana se oculta y queda un icono en la bandeja. Windows+B lleva a la bandeja.",
	),
	(
		"general.cerrar_a_bandeja",
		"&Cerrar a la bandeja del sistema",
		"Alt+F4 oculta la ventana en la bandeja en lugar de salir. Para salir de verdad, use Archivo, Salir.",
	),
	(
		"general.iniciar_en_bandeja",
		"&Iniciar oculta en la bandeja",
		"La aplicación arranca sin mostrar la ventana, solo con el icono de la bandeja.",
	),
]


class DialogoOpciones(wx.Dialog):
	"""Casillas de configuración general."""

	def __init__(self, padre: wx.Window | None, configuracion: Configuracion) -> None:
		super().__init__(padre, title=_("Opciones"))
		self._config = configuracion
		self.casillas: dict[str, wx.CheckBox] = {}

		principal = wx.BoxSizer(wx.VERTICAL)
		for clave, etiqueta, ayuda in OPCIONES:
			casilla = wx.CheckBox(self, label=_(etiqueta))
			casilla.SetValue(bool(configuracion.obtener(clave, False)))
			casilla.SetHelpText(_(ayuda))
			self.casillas[clave] = casilla
			principal.Add(casilla, 0, wx.ALL, 8)
		label = wx.StaticText(self, label="&Volumen de los sonidos (0 a 100):")
		self.sound_volume = wx.SpinCtrl(self, min=0, max=100, initial=max(0, min(100, int(configuracion.obtener("sounds.volume", 25)))))
		self.sound_volume.SetHelpText("Volumen propio de las campanitas. 25 es suave. Cero silencia solo los sonidos de la interfaz.")
		principal.Add(label, 0, wx.LEFT | wx.TOP, 8)
		principal.Add(self.sound_volume, 0, wx.ALL, 8)
		preview = wx.Button(self, label="&Probar sonido")
		preview.SetHelpText("Escucha la campanita de inicio al volumen elegido sin guardar los cambios.")
		preview.Bind(wx.EVT_BUTTON, self._preview)
		principal.Add(preview, 0, wx.ALL, 8)

		botones = wx.StdDialogButtonSizer()
		aceptar = wx.Button(self, wx.ID_OK, label=_("&Aceptar"))
		aceptar.SetDefault()
		botones.AddButton(aceptar)
		botones.AddButton(wx.Button(self, wx.ID_CANCEL, label=_("&Cancelar")))
		botones.Realize()
		principal.Add(botones, 0, wx.EXPAND | wx.ALL, 8)

		self.SetEscapeId(wx.ID_CANCEL)
		self.SetSizerAndFit(principal)
		self.CentreOnParent()
		next(iter(self.casillas.values())).SetFocus()
		self.Bind(wx.EVT_CHAR_HOOK, self._help)

	def _preview(self, event):
		from app.core.feedback import Feedback
		preview_config = Configuracion()
		preview_config.establecer("sounds.enabled", True)
		preview_config.establecer("sounds.volume", self.sound_volume.GetValue())
		self._preview_feedback = Feedback(preview_config)
		self._preview_feedback.play("startup")

	def _help(self, event):
		if event.GetKeyCode() == ord("H") and event.GetModifiers() == wx.MOD_CONTROL:
			from app.ui.dialogo_texto import mostrar_mensaje
			focus = wx.Window.FindFocus()
			mostrar_mensaje(self, focus.GetHelpText() if focus else "Cambie las opciones y pulse Aceptar para guardarlas.", "Ayuda de opciones")
		else:
			event.Skip()

	def aplicar(self) -> None:
		"""Copia el estado de las casillas a la configuración y la guarda."""
		for clave, casilla in self.casillas.items():
			self._config.establecer(clave, casilla.GetValue())
		self._config.establecer("sounds.volume", self.sound_volume.GetValue())
		self._config.guardar()
