"""Contratos de lectura del sitio renderizado y controles de reproducción."""
from urllib.parse import quote, urlsplit

from app.services.catalogue import Title, safe_url
from app.services.episode_navigation import SELECTOR_RUNTIME, SELECTOR_SNAPSHOT
from app.services.live_guide import GUIDE_RUNTIME


def search_url(query: str) -> str:
	return safe_url("/es-es/search?q=" + quote(query.strip(), safe=""))


def catalogue_location(url: str) -> bool:
	parts = urlsplit(url)
	path = parts.path.removeprefix("/es-es").rstrip("/")
	return parts.hostname == "vix.com" and parts.scheme == "https" and (
		path in {"", "/search", "/canales", "/deportes", "/noticias", "/micro-dramas"}
		or path.startswith(("/ondemand/", "/ondemandplus/", "/detail/", "/canales/"))
		or path == "/ondemand"
	)


def snapshot_titles(data: dict) -> list[Title]:
	"""Convierte enlaces visibles en registros; no importa formularios de cuenta."""
	if not catalogue_location(data.get("url", "")):
		return []
	result = {}
	for item in data.get("items", []):
		try:
			url = safe_url(item["url"])
			name = item["title"].strip()
			if not name:
				continue
			path = urlsplit(url).path.removeprefix("/es-es")
			url = safe_url(path)
			kind = "Episodio" if "/video/" in path else "Canal" if "/canales/" in path else "Serie" if "/detail/series-" in path else "Película" if "/detail/video-" in path else "Colección"
			groups = list(result[url].groups) if url in result else []
			if item.get("group") and item["group"] not in groups:
				groups.append(item["group"])
			result[url] = Title(path, name, kind, url, item.get("description", ""), str(item.get("year") or ""), item.get("genres", ""), item.get("rating", ""), groups)
		except (ValueError, KeyError, TypeError, AttributeError):
			continue
	return list(result.values())


SNAPSHOT_SCRIPT = "(() => {" + GUIDE_RUNTIME + ";" + SELECTOR_RUNTIME + r"""
 const path=location.pathname.replace(/^\/es-es/,'');
 const catalogue=location.hostname==='vix.com' && (/^\/(detail|ondemand|ondemandplus|canales)(\/|$)/.test(path)||['','/','/search','/deportes','/noticias','/micro-dramas'].includes(path));
 const items=[];
 let state={};try{state=JSON.parse(document.querySelector('#__NEXT_DATA__')?.textContent||'{}').props?.apolloState||{}}catch(e){}
 if(location.hostname==='vix.com'&&/^\/canales(\/|$)/.test(path)&&!window.__vixClientGuide.seeded&&Object.values(state).some(v=>v?.__typename==='EpgChannel')){window.__vixClientGuide.seeded=true;window.__vixClientCaptureGuide(state,state)}
 if(catalogue) for(const a of document.querySelectorAll('a[href]')) {
  if(a.closest('header,nav')) continue;
  const u=new URL(a.href,location.href);
  if(u.hostname!=='vix.com'||u.hash||!/^\/(?:es-es\/)?(detail\/|video\/|canales\/.+|ondemand\/.+)/.test(u.pathname)) continue;
  const title=(a.querySelector('img')?.alt||a.getAttribute('aria-label')||a.innerText||'').trim();
  const match=u.pathname.match(/(series|video)-(\d+)/);
  const meta=match?state['VideoContent:'+match[1]+':mcp:'+match[2]]||{}:{};
  const description=(meta.description||a.closest('article,li')?.innerText||a.parentElement?.innerText||'').trim();
  const genres=(meta.genresV2||[]).map(g=>(state[g.__ref]||g).name||'').filter(Boolean).join(', ');
  let group='Destacados';
  for(let p=a.parentElement;p&&p!==document.body;p=p.parentElement){const h=p.querySelector('h2');if(h&&(h.compareDocumentPosition(a)&Node.DOCUMENT_POSITION_FOLLOWING)){group=h.innerText.trim()||group;break}}
  if(title) items.push({url:u.href,title,group,description:description.slice(0,10000),year:meta.copyrightYear,genres,rating:(meta.ratings||[]).map(r=>r.ratingValue).join(', ')});
 }
 const video=location.hostname==='vix.com'?document.querySelector('video'):null;
 const media=video?{paused:video.paused,ended:video.ended,ready:video.readyState,time:video.currentTime,duration:Number.isFinite(video.duration)?video.duration:null,isLive:/^\/canales(\/|$)/.test(path),canSeek:!!video.seekable.length,liveDelay:video.seekable.length?Math.max(0,video.seekable.end(video.seekable.length-1)-video.currentTime):null,muted:video.muted,volume:video.volume,error:video.error?.message||window.__vixClientPlayerError||'',audio:[...video.audioTracks||[]].map(t=>({label:t.label,language:t.language,enabled:t.enabled})),subtitles:[...video.textTracks||[]].map(t=>({label:t.label,language:t.language,kind:t.kind,mode:t.mode}))}:null;
 let identity={signedIn:null,profile:''};
 if(location.hostname==='vix.com'){
  const loggedCookie=document.cookie.split(';').map(c=>c.trim()).find(c=>c.startsWith('vix_user_logged='));
  if(loggedCookie){const logged=decodeURIComponent(loggedCookie.slice('vix_user_logged='.length)).replace(/"/g,'');if(logged==='true'||logged==='false')identity.signedIn=logged==='true';}
  else if(document.readyState!=='loading'&&document.querySelector('main,header,nav'))identity.signedIn=false;
  const profileRef=state.ROOT_QUERY?.currentProfile;
  const currentProfile=profileRef?.__ref?state[profileRef.__ref]:profileRef;
  identity.profile=currentProfile?.name||window.__vixClientIdentity?.profile||'';
  if(identity.signedIn===null){
   const login=[...document.querySelectorAll('a,button')].some(e=>e.getClientRects().length && /^(iniciar sesi[oó]n|ingresar|inicia sesi[oó]n)$/i.test(e.innerText.trim()));
   if(login)identity.signedIn=false;
  }
  if(identity.signedIn!==true)identity.profile='';
 }
""" + SELECTOR_SNAPSHOT + r"""
 const ranges=selectors.flatMap(s=>s.options);
 const groups=catalogue?[...document.querySelectorAll('h2')].filter(h=>h.getClientRects().length&&!h.closest('footer,[role=dialog]')).map(h=>h.innerText.trim()).filter(Boolean):[];
 const guide=location.hostname==='vix.com'&&/^\/canales(\/|$)/.test(path)?Object.values(window.__vixClientGuide.channels):[];
 const liveCategories=guide.length?[...new Set(Object.values(window.__vixClientGuide.categories))].filter(Boolean):[];
 return JSON.stringify({url:location.href,title:document.title,items,guide,liveCategories,guideUpdated:guide.length?window.__vixClientGuide.updated:null,groups:[...new Set(groups)],text:catalogue?(document.querySelector('main')||document.body).innerText.split('© 2026.')[0].slice(0,100000):'',ranges:[...new Set(ranges)],selectors,episodeUrls,episodeLoading,episodeEmpty,selectionResult:catalogue?nav.result:null,media,identity});
})()"""

LOAD_MORE_SCRIPT = r"""(() => {
 window.scrollBy(0,Math.max(600,innerHeight*.8));
 for(const e of document.querySelectorAll('main,section,div')) {
  const s=getComputedStyle(e);
  if(e.clientHeight>200 && e.scrollHeight>e.clientHeight+100 && /auto|scroll/.test(s.overflowY)) e.scrollTop+=e.clientHeight*.8;
  if(e.clientWidth>200 && e.scrollWidth>e.clientWidth+100 && /auto|scroll/.test(s.overflowX)) e.scrollLeft+=e.clientWidth*.8;
 }
 for(const b of document.querySelectorAll('button')) {
  if(/^\/(?:es-es\/)?canales(\/|$)/.test(location.pathname))break;
  const label=b.getAttribute('aria-label')||b.title||'';
  if(b.getClientRects().length && !b.disabled && /^(next|siguiente|ver más|mostrar más|cargar más)(\s|$)/i.test(label)) b.click();
 }
 return 'more';
})()"""


def player_script(action: str) -> str:
	commands = {
		"toggle": "if(v.paused){v.play().catch(e=>window.__vixClientPlayerError=e.message)}else{v.pause()}",
		"back": "if(v.seekable.length)v.currentTime=Math.max(v.seekable.start(0),v.currentTime-10)",
		"forward": "if(v.seekable.length)v.currentTime=Math.min(v.seekable.end(v.seekable.length-1),v.currentTime+10)",
		"mute": "v.muted=!v.muted",
		"louder": "v.volume=Math.min(1,v.volume+.1)",
		"quieter": "v.volume=Math.max(0,v.volume-.1)",
		"stop": "v.pause();if(v.seekable.length)v.currentTime=v.seekable.start(0)",
		"live": "if(v.seekable.length){v.currentTime=Math.max(v.seekable.start(0),v.seekable.end(v.seekable.length-1)-.5);v.play().catch(e=>window.__vixClientPlayerError=e.message)}",
	}
	command = commands[action]
	return "(() => {const v=location.hostname==='vix.com'?document.querySelector('video'):null;if(!v)return 'No hay un vídeo activo. Use Ver ahora en la página del título.';window.__vixClientPlayerError='';" + command + ";return 'Control enviado al reproductor';})()"
