"""Los recursos son breves, suaves y las preferencias se guardan completas."""
from array import array
from pathlib import Path
import wave

from app.core.config import Configuracion
from app.ui.dialogo_opciones import DialogoOpciones


def test_sound_assets_are_short_and_do_not_clip():
	assets = list((Path(__file__).resolve().parents[1] / "data/sounds").glob("*.wav"))
	assert len(assets) == 7
	for asset in assets:
		with wave.open(str(asset), "rb") as source:
			assert source.getnchannels() == 1
			assert source.getsampwidth() == 2
			assert .1 < source.getnframes() / source.getframerate() < 1
			values = array("h", source.readframes(source.getnframes()))
			assert max(abs(value) for value in values) < 16000


def test_sound_preferences_save_and_cancel_leaves_previous_values(app_wx):
	config = Configuracion()
	dialog = DialogoOpciones(None, config)
	try:
		dialog.casillas["sounds.enabled"].SetValue(False)
		dialog.sound_volume.SetValue(12)
		dialog.aplicar()
	finally:
		dialog.Destroy()
	assert Configuracion().obtener("sounds.enabled") is False
	assert Configuracion().obtener("sounds.volume") == 12
	dialog = DialogoOpciones(None, config)
	try:
		dialog.sound_volume.SetValue(90)
	finally:
		dialog.Destroy()
	assert Configuracion().obtener("sounds.volume") == 12
