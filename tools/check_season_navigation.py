"""Verifica temporadas reales usando solo los controles nativos del cliente."""
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["APP_DATA_DIR"] = str(ROOT / "data/temp" / ("season-client-check-" + str(time.time_ns())))

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

if os.environ.get("PROFILE_SEASONS"):
	import json
	import wx.html2 as html2
	def debug_result(event):
		try:
			data = json.loads(event.GetString())
			if isinstance(data, dict) and data.get('type') == 'season-debug':
				print('SPINNERS', ascii(data), flush=True)
		except ValueError:
			pass
		event.Skip()
	original = frame.live.on_snapshot
	last = [None]
	def trace(data):
		pending = frame._selector_pending
		if pending:
			state = (data.get('selectionResult'), [(s['kind'], s['selected']) for s in data.get('selectors', [])], data.get('episodeLoading'), len(data.get('episodeUrls', [])), set(data.get('episodeUrls', [])) == set(pending['before']))
			if state != last[0]:
				print('TRACE', round(time.monotonic() - pending['started'], 3), ascii(state), flush=True)
				last[0] = state
				frame.live.view.RunScriptAsync("(() => {let r=window.__vixEpisodeNav.controls()[0]?.b.parentElement;for(let p=r;p&&p!==document.body;p=p.parentElement)if(p.querySelector('a[href*=\"/video/\"]')){r=p;break}return JSON.stringify({type:'season-debug',root:r?.className,spinners:[...r?.querySelectorAll('[aria-busy=\"true\"],[role=\"progressbar\"],[class*=\"Skeleton\"],[class*=\"skeleton\"]')||[]].filter(e=>e.getClientRects().length).map(e=>({tag:e.tagName,cls:e.className,role:e.getAttribute('role'),ancestors:[e.parentElement?.className,e.parentElement?.parentElement?.className]}))})})()")
		original(data)
	frame.live.on_snapshot = trace
	# The view is created lazily; the additional handler only observes diagnostics.
	frame.live.ensure_view()
	frame.live.view.Bind(html2.EVT_WEBVIEW_SCRIPT_RESULT, debug_result)

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
			started = time.monotonic()
			frame.season_choice.SetStringSelection(target)
			frame._select_episode_content("season")
			assert pump_until(lambda: frame._selector_pending is None and frame._selectors.get('season',{}).get('selected') == target and bool(frame._episode_urls) and frame._episode_urls != before), (target, frame.GetStatusBar().GetStatusText())
			assert frame.season_choice.GetStrings() == options
			assert 'No se pudo' not in frame.GetStatusBar().GetStatusText(), frame.GetStatusBar().GetStatusText()
			print('CHANGED', ascii(target), len(frame._episode_urls), 'episodes', 'SECONDS', round(time.monotonic() - started, 3), flush=True)
		# Arrowing quickly through choices and returning to the original season
		# must keep the correct rows, not an intermediate request's response.
		expected = frame._episode_urls[0]
		for target in [*options[1:4], options[0]]:
			frame.season_choice.SetStringSelection(target)
			frame._select_episode_content("season")
		assert pump_until(lambda: frame._selector_pending is None and frame._selectors.get('season', {}).get('selected') == options[0])
		assert frame._episode_urls[0] == expected
		print('RAPID SEASON CHOICES AND RETURN OK', flush=True)
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
