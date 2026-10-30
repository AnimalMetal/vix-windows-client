"""Prueba de En vivo: canales nativos, categorías y ausencia de autoplay al explorar."""
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["APP_DATA_DIR"] = str(ROOT / "data/temp/live-guide-check")

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
latest = {}
original = frame.live.on_snapshot

def snapshot(data):
	latest.clear()
	latest.update(data)
	original(data)

frame.live.on_snapshot = snapshot

def pump_until(condition, seconds=25):
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
	frame.section.SetStringSelection("En vivo")
	frame._al_actualizar(None)
	pump_until(lambda: len(frame.titles) > 15)
	print('CHANNELS', len(frame.titles), 'CATEGORIES', ascii(frame.home_group.GetStrings()), flush=True)
	print('EXAMPLE', ascii([(t.channel_number,t.title,t.now_playing,t.programme_time) for t in frame.titles[:3]]), flush=True)
	print('CURRENT PROGRAMMES',sum(t.now_playing!='Programación actual no disponible' for t in frame.titles),flush=True)
	frame.home_group.SetStringSelection("Humor")
	frame._group_changed(None)
	assert any(t.channel_number == "330" for t in frame.visible_titles)
	frame.query.SetValue("330")
	assert len(frame.visible_titles) == 1 and frame.visible_titles[0].title == "Vecinos"
	print('CATEGORY AND NUMBER FILTER OK',flush=True)
	print('BROWSING MEDIA', latest.get('media'), flush=True)
	assert frame.titles
	assert frame.lista.GetColumnCount() == 7
	assert not latest.get('media') or latest['media']['paused']
	assert not frame.account_dialog.IsShown()
	frame.home_group.SetSelection(0)
	frame.query.SetValue("100")
	assert frame.visible_titles and frame.visible_titles[0].channel_number == "100"
	frame._open_selected(None)
	assert pump_until(lambda: bool(frame.player.media) and frame.player.media.get('isLive') and frame.player.media.get('ready',0)>=3 and not frame.player.media.get('paused'),30),frame.player.status.GetValue()
	assert not frame.player.seek.IsEnabled()
	print('LIVE PLAYBACK',ascii(frame.player.status.GetValue()),flush=True)
	assert '498' not in frame.player.status.GetValue()
	if frame.player.media.get('canSeek'):
		frame.live.control('live')
		assert pump_until(lambda: bool(frame.player.media) and frame.player.media.get('liveDelay') is not None and frame.player.media['liveDelay']<=5,20)
		print('RETURN TO LIVE EDGE OK',flush=True)
	url = frame.live.view.GetCurrentURL()
	frame._al_actualizar(None)
	assert frame.live.view.GetCurrentURL() == url
	frame.live.control('toggle')
	assert pump_until(lambda: bool(frame.player.media) and frame.player.media.get('paused'))
	print('LIVE PAUSE OK',flush=True)
	frame.live.view.RunScriptAsync("document.dispatchEvent(new KeyboardEvent('keydown',{key:'F6',bubbles:true,cancelable:true})); 'keyboard bridge exercised'")
	assert pump_until(lambda: frame.notebook.GetSelection() == 0)
	print('RETURN TO CHANNEL GUIDE OK',flush=True)
finally:
	frame.salir()
	pump_until(lambda: not frame, 2)
