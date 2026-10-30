"""Comprobación de integración del motor con páginas públicas, sin iniciar sesión."""
import json
import os
from pathlib import Path
import sys
import time

import wx
import wx.html2 as html2

os.environ["WEBVIEW2_USER_DATA_FOLDER"] = str(Path(__file__).resolve().parents[1] / "data/temp/webview-probe")
app = wx.App(False)
frame = wx.Frame(None)
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
for path in sys.argv[1:] or ["/es-es/search?q=teresa"]:
	view.LoadURL("https://vix.com" + path)
	pump(12)
	if "detail" in path and os.environ.get("APP_PROBE_RANGES"):
		view.RunScriptAsync("document.querySelector('button[aria-label=\"Selected Item\"]')?.click(); 'opened'")
		pump(1)
	view.RunScriptAsync("JSON.stringify({url:location.href,title:document.title,text:document.body.innerText.slice(0,3000),buttons:[...document.querySelectorAll('button,[role=combobox]')].map(b=>({text:b.innerText,label:b.getAttribute('aria-label'),title:b.title,tag:b.tagName,role:b.getAttribute('role')})).slice(0,50),selects:[...document.querySelectorAll('select')].map(s=>({options:[...s.options].map(o=>({text:o.text,value:o.value}))})),scrolls:[...document.querySelectorAll('main,section,div')].filter(e=>e.scrollHeight>e.clientHeight+100&&e.clientHeight>200).slice(0,5).map(e=>({tag:e.tagName,role:e.getAttribute('role'),class:e.className,height:e.clientHeight,scroll:e.scrollHeight})),video:[...document.querySelectorAll('video')].map(v=>({paused:v.paused,time:v.currentTime,error:v.error?.code,ready:v.readyState}))})")
	pump(2)
	print(json.dumps(results[-1:] ,ensure_ascii=True),flush=True)
frame.Destroy()
pump(.3)
