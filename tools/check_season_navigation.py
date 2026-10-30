"""Verifica temporadas reales usando solo los controles nativos del cliente."""
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["APP_DATA_DIR"] = str(ROOT / "data/temp/season-client-check")

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
frame.SetSize((1100, 950))
frame.Layout()

def pump_until(condition, seconds=20):
	loop = wx.GUIEventLoop()
	active = wx.EventLoopActivator(loop)
	end = time.monotonic() + seconds
	try:
		while time.monotonic() < end:
			while loop.Pending():
				loop.Dispatch()
			app.ProcessPendingEvents()
			loop.ProcessIdle()
			if condition():
				return True
			time.sleep(.02)
		return False
	finally:
		del active

try:
	for identifier in sys.argv[1:] or ["502", "3974", "584"]:
		if identifier.startswith("search:"):
			query = identifier.split(":", 1)[1]
			frame.search.SetValue(query)
			frame._search_all(None)
			assert pump_until(lambda: any(t.title.casefold() == query.casefold() and t.kind == "Serie" for t in frame.titles)), frame.GetStatusBar().GetStatusText()
			title = next(t for t in frame.titles if t.title.casefold() == query.casefold() and t.kind == "Serie")
			print("FOUND", ascii(title.title), title.url, flush=True)
			frame._navigate(title.url)
		else:
			frame._navigate("/es-es/detail/series-" + identifier)
		assert pump_until(lambda: frame.season_choice.GetCount() > 1 and bool(frame._episode_urls)), frame.GetStatusBar().GetStatusText()
		options = frame.season_choice.GetStrings()
		print(identifier, 'SEASONS', ascii(options), flush=True)
		for target in [options[-1], options[0]]:
			before = list(frame._episode_urls)
			frame.season_choice.SetStringSelection(target)
			frame._select_episode_content("season")
			assert pump_until(lambda: frame._selector_pending is None and frame._selectors.get('season',{}).get('selected') == target and bool(frame._episode_urls) and frame._episode_urls != before), (target, frame.GetStatusBar().GetStatusText())
			assert frame.season_choice.GetStrings() == options
			print('CHANGED', ascii(target), len(frame._episode_urls), 'episodes', flush=True)
	frame._navigate("/es-es/detail/series-783")
	assert pump_until(lambda: frame.episode_group.GetCount() > 1 and bool(frame._episode_urls))
	options = frame.episode_group.GetStrings()
	before = list(frame._episode_urls)
	frame.episode_group.SetSelection(len(options) - 1)
	frame._select_range(None)
	assert pump_until(lambda: frame._selector_pending is None and frame._episode_urls != before)
	assert frame.episode_group.GetStrings() == options
	print('EPISODE RANGES', len(options), 'options retained; final range selected', flush=True)
finally:
	frame.salir()
	pump_until(lambda: not frame, 2)
