"""Prueba explícita de integración con páginas públicas y un episodio gratuito."""
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["APP_DATA_DIR"] = str(ROOT / "data/temp/live-client-check")

import wx
from app.core.config import Configuracion
from app.core import voz
from app.ui.vix_window import VentanaPrincipal

voz.hablar = lambda *a, **k: False
app = wx.App(False)
wx.HelpProvider.Set(wx.SimpleHelpProvider())
frame = VentanaPrincipal(Configuracion())
frame.SetSize((1100, 850))
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
	frame.search.SetValue("teresa")
	frame._search_all(None)
	pump(15)
	print("GLOBAL SEARCH", len(frame.titles), any(t.title == "Teresa" for t in frame.titles), frame.live.view.GetCurrentURL(), [t.title for t in frame.titles[:6]], frame._page_text[:300], 'READY',frame.live._page_ready,'SIZE',frame.live.view.GetSize(),'STATUS',frame.GetStatusBar().GetStatusText(), flush=True)
	frame._navigate("/es-es/detail/series-783")
	pump(12)
	print("DETAILS", "177" in frame._page_text, "EPISODES", len([t for t in frame.titles if t.kind == "Episodio"]), frame.live.view.GetCurrentURL(), frame._page_text[:300], flush=True)
	if not frame.live.loading_all:
		frame._load_all(None)
	pump(15)
	print("MORE EPISODES", len([t for t in frame.titles if t.kind == "Episodio"]), flush=True)
	frame._ranges(None)
	pump(3)
	print("EPISODE GROUPS", frame.episode_group.GetCount(), flush=True)
	if frame.episode_group.GetCount() > 1:
		frame.episode_group.SetSelection(frame.episode_group.GetCount()-1)
		frame._select_range(None)
		pump(5)
		print("LAST GROUP", frame._page_text.find("161 - 177") >= 0, len(frame.titles), flush=True)
	frame._start_player("https://vix.com/es-es/video/video-2959119")
	pump(12)
	print("PLAYER", frame.player.status.GetValue(), flush=True)
	frame.live.control("toggle")
	pump(2)
	print("PAUSE", frame.player.status.GetValue(), flush=True)
	frame.live.navigate("https://vix.com/es-es/account/mi-cuenta")
	pump(8)
	print("ACCOUNT PAGE", frame.live.view.GetCurrentURL(), flush=True)
finally:
	frame.salir()
	pump(.5)
