"""Inspección de la guía pública para construir una vista nativa de En vivo."""
import os
from pathlib import Path
import time
import json
import wx
import wx.html2 as html2

os.environ["WEBVIEW2_USER_DATA_FOLDER"] = str(Path(__file__).resolve().parents[1] / "data/temp/live-probe")
app = wx.App(False)
frame = wx.Frame(None, size=(1100, 850))
view = html2.WebView.New(frame, backend=html2.WebViewBackendEdge)
results = []
view.Bind(html2.EVT_WEBVIEW_SCRIPT_RESULT, lambda e: results.append(e.GetString()))

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
	view.LoadURL("https://vix.com/es-es/canales")
	pump(12)
	view.RunScriptAsync("JSON.stringify({url:location.href,text:document.body.innerText.slice(0,11000),buttons:[...document.querySelectorAll('button')].filter(b=>b.getClientRects().length).map(b=>({text:b.innerText,label:b.getAttribute('aria-label'),html:b.outerHTML.slice(0,800)})).slice(0,35),links:[...document.querySelectorAll('a[href]')].map(a=>({href:a.href,text:a.innerText,alt:a.querySelector('img')?.alt})).filter(a=>a.href.includes('/canales/')).slice(0,12),media:[...document.querySelectorAll('video')].map(v=>({paused:v.paused,muted:v.muted,time:v.currentTime}))})")
	pump(1)
	print(json.dumps(results[-1:],ensure_ascii=True),flush=True)
	view.RunScriptAsync("document.querySelector('video')?.pause(); 'paused'")
	pump(.2)
finally:
	frame.Destroy()
	pump(.3)
