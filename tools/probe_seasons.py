"""Inspección de los selectores públicos de una serie sin sesión de usuario."""
import os
from pathlib import Path
import sys
import time
import json
import wx
import wx.html2 as html2

os.environ["WEBVIEW2_USER_DATA_FOLDER"] = str(Path(__file__).resolve().parents[1] / "data/temp/season-probe")
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

def script(code):
	results.clear()
	view.RunScriptAsync(code)
	pump(1)
	return results[-1] if results else "NO RESULT"

try:
	for identifier in sys.argv[1:] or ["502", "3974"]:
		view.LoadURL("https://vix.com/es-es/detail/series-" + identifier)
		pump(12)
		print(identifier,script("JSON.stringify({text:document.body.innerText.slice(0,1000),selected:[...document.querySelectorAll('button[aria-label=\"Selected Item\"]')].map(e=>({text:e.innerText,html:e.parentElement.outerHTML.slice(0,5000)})),selects:[...document.querySelectorAll('select')].map(e=>e.outerHTML)})"),flush=True)
		print('OPEN',script("(() => {document.querySelector('button[aria-label=\"Selected Item\"]')?.click();return 'opened'})()"),flush=True)
		pump(.5)
		print('MENU',script("JSON.stringify({text:document.body.innerText.slice(0,2200),selected:[...document.querySelectorAll('button[aria-label=\"Selected Item\"]')].map(e=>e.parentElement.outerHTML.slice(0,12000))})"),flush=True)
finally:
	frame.Destroy()
	pump(.3)
