"""Los errores de un marco secundario no se presentan como fallo del catálogo."""
from types import SimpleNamespace


def test_secondary_frame_error_is_ignored(app_wx):
	import wx
	from app.ui.site_panel import SitePanel
	window = wx.Frame(None)
	statuses = []
	panel = SitePanel(window, lambda data: None, statuses.append)
	panel.view = SimpleNamespace(GetCurrentURL=lambda: "https://vix.com/es-es", Stop=lambda: None)
	panel._requested_url = "https://vix.com/es-es"
	try:
		panel._error(SimpleNamespace(GetURL=lambda: "https://ads.example.test/frame"))
		assert statuses == []
		panel._error(SimpleNamespace(GetURL=lambda: "https://vix.com/es-es"))
		assert len(statuses) == 1
	finally:
		panel.stop()
		window.Destroy()
