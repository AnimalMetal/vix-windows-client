"""Sonidos cortos asíncronos, con volumen propio y sin bloquear al lector."""
from array import array
import logging
import threading
import time
import wave

from app.core import paths

log = logging.getLogger(__name__)


class Feedback:
	def __init__(self, config):
		self.config = config
		self._last = 0.0
		self._lock = threading.Lock()

	def play(self, name):
		if name not in {"startup", "open", "back", "top", "bottom", "ready", "error"} or not self.config.obtener("sounds.enabled", True):
			return
		with self._lock:
			if time.monotonic() - self._last < .12:
				return
			self._last = time.monotonic()
		try:
			volume = max(0, min(100, int(self.config.obtener("sounds.volume", 25))))
		except (ValueError, TypeError, OverflowError):
			volume = 25
		if volume:
			threading.Thread(target=self._play, args=(name, volume), daemon=True, name="sonido-cliente").start()

	def _play(self, name, volume):
		try:
			import winsound
			original = paths.ruta_base() / "data/sounds" / (name + ".wav")
			cached = paths.subcarpeta("cache") / "sounds" / f"{name}-{volume}.wav"
			if not cached.exists():
				with wave.open(str(original), "rb") as source:
					parameters = source.getparams()
					samples = array("h", source.readframes(source.getnframes()))
				samples = array("h", (round(value * volume / 100) for value in samples))
				cached.parent.mkdir(parents=True, exist_ok=True)
				with wave.open(str(cached), "wb") as target:
					target.setparams(parameters)
					target.writeframes(samples.tobytes())
			winsound.PlaySound(str(cached), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
		except (OSError, RuntimeError, ImportError, wave.Error):
			log.debug("No se pudo reproducir un sonido de interfaz.", exc_info=True)
