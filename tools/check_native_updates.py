"""Prueba real de filas de Inicio, reproductor nativo y salida desde Chromium."""
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["APP_DATA_DIR"] = str(ROOT / "data/temp/native-update-check")

import wx
from app.core.config import Configuracion
from app.core import voz
from app.core.feedback import Feedback
from app.ui.vix_window import VentanaPrincipal

voz.hablar = lambda *a, **k: False
Feedback.play = lambda *a, **k: None
app = wx.App(False)
wx.HelpProvider.Set(wx.SimpleHelpProvider())
frame = VentanaPrincipal(Configuracion())
frame.SetSize((1100, 900))
frame.Layout()


def pump(seconds):
	loop = wx.GUIEventLoop()
	active = wx.EventLoopActivator(loop)
	end = time.monotonic() + seconds
	while time.monotonic() < end:
		while loop.Pending():
			loop.Dispatch()
		app.ProcessPendingEvents()
		loop.ProcessIdle()
		time.sleep(.02)
	del active


try:
	frame._navigate("/es-es")
	pump(13)
	print("HOME GROUPS", ascii(frame.home_group.GetStrings()), flush=True)
	assert len(frame.home_group.GetStrings()) > 2
	before = [t.url for t in frame.titles]
	selected = frame._selected().url if frame._selected() else None
	frame._start_player("https://vix.com/es-es/video/video-2959119", "Episodio de prueba")
	pump(14)
	assert frame.notebook.GetSelection() == 1
	assert frame.player.media
	print("NATIVE PLAYER", ascii(frame.player.status.GetValue()), flush=True)
	assert frame.player.media.get("time", 0) > 0
	frame.live.control("toggle")
	pump(2)
	assert frame.player.media["paused"]
	frame.player.change("volume", .3)
	pump(2)
	assert abs(frame.player.media["volume"] - .3) < .01
	frame.notebook.SetSelection(1)
	frame.live.view.RunScriptAsync("document.dispatchEvent(new KeyboardEvent('keydown',{key:'F6',bubbles:true,cancelable:true})); 'keyboard bridge exercised'")
	pump(2)
	assert frame.notebook.GetSelection() == 0
	assert [t.url for t in frame.titles] == before
	assert (frame._selected().url if frame._selected() else None) == selected
	print("BROWSER RETURN BRIDGE AND CATALOGUE RESTORATION OK", flush=True)
	print("GUEST SESSION STATE", frame._identity.get("signedIn"), flush=True)
finally:
	frame.salir()
	pump(.5)
