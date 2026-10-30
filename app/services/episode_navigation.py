"""Selectores de temporada y episodios basados en sus controles reales."""
import json


SELECTOR_RUNTIME = r"""
if(!window.__vixEpisodeNav){
 const text=e=>(e?.innerText||e?.textContent||'').trim().replace(/\s+/g,' ');
 const label=b=>text(b.querySelector('[class*="selectedText"]')||b.firstElementChild)||text(b).split('\n')[0];
 const kind=s=>/^(temporada|season|T\s*\d)/i.test(s)?'season':/^episodios?/i.test(s)?'episodes':null;
 const controls=()=>[...document.querySelectorAll('button[aria-label="Selected Item"]')].map((b,i)=>({b,id:'episodes-selector-'+i,kind:kind(label(b)),selected:label(b)})).filter(c=>c.kind);
 const cache={};
 const context=c=>location.pathname+':'+c.id+(c.kind==='episodes'?':'+(controls().find(x=>x.kind==='season')?.selected||''):'');
 const options=c=>[...new Set([...c.b.querySelectorAll('[role="option"]')].map(text).filter(Boolean))];
 const opened=c=>!!c.b.querySelector('[role="option"]');
 const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
 const episodeRoot=()=>{
  let root=controls()[0]?.b.parentElement;
  for(let p=root;p&&p!==document.body;p=p.parentElement)if(p.querySelector('a[href*="/video/"]')){root=p;break}
  return root;
 };
 const episodeUrls=()=>[...episodeRoot()?.querySelectorAll('a[href]')||[]].map(a=>a.href).filter(u=>/\/video\//.test(u));
 const snapshot=()=>controls().map(c=>({id:c.id,kind:c.kind,selected:c.selected,options:cache[context(c)]?.options||[c.selected],discovered:!!cache[context(c)]?.done}));
 window.__vixEpisodeNav={controls,cache,context,options,opened,delay,text,snapshot,episodeRoot,episodeUrls,busy:false,result:null,latest:null};
}
"""

SELECTOR_SNAPSHOT = r"""
 const nav=window.__vixEpisodeNav;
 const selectors=catalogue?nav.snapshot():[];
 const episodeRoot=catalogue?nav.episodeRoot():null;
 const episodeUrls=catalogue?nav.episodeUrls():[];
 const episodeLoading=!!episodeRoot&&[...episodeRoot.querySelectorAll('[aria-busy="true"],[role="progressbar"],[class*="Skeleton"],[class*="skeleton"]')].some(e=>e.getClientRects().length);
 const episodeEmpty=!!episodeRoot&&!episodeUrls.length&&/no hay episodios|sin episodios|no se encontraron episodios|contenido no disponible/i.test(episodeRoot.innerText);
"""


def discover_script(force=False):
	return "(() => {" + SELECTOR_RUNTIME + r"""
 const nav=window.__vixEpisodeNav;
 if(nav.busy)return 'more';
 nav.busy=true;
 (async()=>{try{
  for(const c of nav.controls()){
   const key=nav.context(c);
   if(nav.cache[key]?.done && !FORCE)continue;
   const wasOpen=nav.opened(c);
   if(!wasOpen)c.b.click();
   for(let i=0;i<10&&!nav.options(c).length;i++)await nav.delay(100);
   const values=nav.options(c);
   nav.cache[key]={options:values.length?values:[c.selected],done:!!values.length};
   if(!wasOpen&&nav.opened(c))c.b.click();
   await nav.delay(80);
  }
 }finally{nav.busy=false}})().catch(()=>{nav.busy=false});
 return 'more';
})()""".replace("FORCE", "true" if force else "false")


def selection_script(selector_id, target, request_id):
	arguments = json.dumps({"selector": selector_id, "target": target, "request": request_id}, ensure_ascii=True)
	return "(() => {" + SELECTOR_RUNTIME + "const args=" + arguments + r""";
 const nav=window.__vixEpisodeNav;
 nav.latest=args.request;
 nav.result={request:args.request,status:'pending'};
 (async()=>{try{
  for(let i=0;i<20&&nav.busy;i++)await nav.delay(100);
  if(nav.latest!==args.request)return;
  const c=nav.controls().find(c=>c.id===args.selector);
  if(!c)throw new Error('El selector ya no está disponible. Actualice temporadas y episodios.');
  if(c.selected===args.target){nav.result={request:args.request,status:'clicked',beforeUrls:nav.episodeUrls()};return}
  if(!nav.opened(c))c.b.click();
  let option;
  for(let i=0;i<15;i++){
   if(nav.latest!==args.request)return;
   option=[...c.b.querySelectorAll('[role="option"]')].find(e=>nav.text(e)===args.target);
   if(option)break;
   await nav.delay(100);
  }
  if(!option)throw new Error('No se pudo elegir '+args.target+'. Actualice temporadas y episodios.');
  const beforeUrls=nav.episodeUrls();
  (option.querySelector('[role="button"]')||option).click();
  nav.result={request:args.request,status:'clicked',beforeUrls};
 }catch(error){if(nav.latest===args.request)nav.result={request:args.request,status:'failed',message:error.message}}})()
 return 'more';
})()"""


def selection_outcome(pending, data, now):
	"""Espera la selección y sus episodios, sin congelar indefinidamente la lista."""
	result = data.get("selectionResult") or {}
	if result.get("request") == pending["request"] and result.get("status") == "failed":
		return "failed", result.get("message", "No se pudo cambiar la selección.")
	selector = next((s for s in data.get("selectors", []) if s.get("id") == pending["selector"]), {})
	urls = data.get("episodeUrls", [])
	acknowledged = not result or (result.get("request") == pending["request"] and result.get("status") == "clicked")
	before = result.get("beforeUrls", pending["before"]) if acknowledged else pending["before"]
	# ViX deja el indicador «cargar más» visible aun cuando ya hay episodios.
	# Exigir que desaparezca retenía la lista hasta el tiempo límite de 15 s.
	# Un primer episodio nuevo confirma el cambio; añadir filas de la temporada
	# anterior no basta para darlo por terminado.
	new_episodes = bool(urls) and urls[0] not in set(before)
	empty_ready = not urls and data.get("episodeEmpty") and not data.get("episodeLoading")
	same_ready = pending.get("allow_same") and urls == pending["before"] and result.get("request") == pending["request"] and result.get("status") == "clicked"
	if acknowledged and selector.get("selected") == pending["target"] and (new_episodes or empty_ready or same_ready):
		return "ready", ""
	if now - pending["started"] >= 15:
		return "failed", "No se pudo confirmar la carga de los episodios. Actualice temporadas y episodios para reintentar."
	return "waiting", ""
