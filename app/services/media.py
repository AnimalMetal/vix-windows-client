"""Formato y órdenes del reproductor nativo, sin dependencias de interfaz."""
import math


def clock(value):
	try:
		seconds = max(0, int(value))
	except (TypeError, ValueError, OverflowError):
		return "Desconocida"
	return f"{seconds // 3600:02}:{seconds // 60 % 60:02}:{seconds % 60:02}"


def media_summary(media):
	if not media:
		return "Preparando el reproductor. Si ViX requiere iniciar sesión, use Mi cuenta."
	state = "Finalizado" if media.get("ended") else "Cargando" if media.get("ready", 4) < 3 else "Pausado" if media.get("paused") else "Reproduciendo"
	if media.get("isLive"):
		delay = media.get("liveDelay")
		position = "En directo" if delay is not None and delay <= 5 else "Retraso aproximado " + clock(delay) if delay is not None else "Emisión en vivo"
		text = f"{state}. {position}."
	else:
		text = f"{state}. {clock(media.get('time', 0))} de {clock(media.get('duration'))}."
	text += " Silenciado." if media.get("muted") else f" Volumen {round(media.get('volume', 0) * 100)} %."
	if media.get("error"):
		text += " " + media["error"]
	return text


def session_summary(identity):
	logged = identity.get("signedIn")
	if logged is True:
		profile = identity.get("profile") or "no confirmado todavía"
		return f"Sesión iniciada en ViX. Perfil: {profile}."
	if logged is False:
		return "Sin sesión iniciada en ViX."
	return "Estado de sesión aún no confirmado. Abra Mi cuenta para comprobarlo."


def value_script(kind, value):
	"""Solo acepta valores y operaciones concretas; no interpola texto del sitio."""
	if kind in {"seek", "volume"}:
		value = float(value)
		if not math.isfinite(value):
			raise ValueError("El valor debe ser finito.")
		command = f"v.volume={max(0, min(1, value))}" if kind == "volume" else f"if(v.seekable.length)v.currentTime=Math.max(v.seekable.start(0),Math.min(v.seekable.end(v.seekable.length-1),{max(0, value)}))"
	elif kind in {"subtitle", "audio"}:
		index = int(value)
		if index < -1:
			raise ValueError("Pista no válida.")
		tracks = "textTracks" if kind == "subtitle" else "audioTracks"
		property_name = "mode" if kind == "subtitle" else "enabled"
		command = f"[...v.{tracks}||[]].forEach((t,i)=>t.{property_name}=" + (f"i==={index}?'showing':'disabled'" if kind == "subtitle" else f"i==={index}") + ")"
	else:
		raise ValueError("Control no válido.")
	return "(() => {const v=location.hostname==='vix.com'?document.querySelector('video'):null;if(!v)return 'No hay vídeo activo';" + command + ";return JSON.stringify({type:'player-feedback',text:'Control de reproducción actualizado'});})()"


KEY_BRIDGE_SCRIPT = r"""(() => {
 if(window.__vixClientKeys) return;
 window.__vixClientKeys=true;
 document.addEventListener('keydown',e=>{
  const command=e.key==='F6'&&!e.ctrlKey&&!e.altKey&&!e.shiftKey?'catalogue':e.key==='F8'&&!e.ctrlKey&&!e.altKey&&!e.shiftKey?'player':null;
  if(command){e.preventDefault();e.stopImmediatePropagation();window.vixclient?.postMessage(JSON.stringify({command}));}
 },true);
})()"""


IDENTITY_OBSERVER_SCRIPT = r"""(() => {
 if(location.hostname!=='vix.com'||window.__vixClientIdentityObserver)return;
 window.__vixClientIdentityObserver=true;
 window.__vixClientIdentity={profile:''};
 const observe=payload=>{window.__vixClientCaptureGuide?.(payload);if(Array.isArray(payload)){payload.forEach(observe);return}const p=payload?.data?.currentProfile;if(p&&typeof p.name==='string')window.__vixClientIdentity.profile=p.name.slice(0,120)};
 const original=window.fetch;
 window.fetch=function(...args){return original.apply(this,args).then(response=>{
  if(/\/(gql|graphql)(\/|\?|$)/i.test(response.url))response.clone().json().then(observe).catch(()=>{});
  return response;
 })};
 const open=XMLHttpRequest.prototype.open,send=XMLHttpRequest.prototype.send;
 XMLHttpRequest.prototype.open=function(method,url,...rest){this.__vixClientProfileRequest=/\/(gql|graphql)(\/|\?|$)/i.test(String(url));return open.call(this,method,url,...rest)};
 XMLHttpRequest.prototype.send=function(...args){if(this.__vixClientProfileRequest)this.addEventListener('load',()=>{try{observe(this.responseType==='json'?this.response:JSON.parse(this.responseText))}catch(e){}},{once:true});return send.apply(this,args)};
})()"""
