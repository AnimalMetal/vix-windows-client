"""Guía de canales a partir de los datos de programación que publica ViX."""
from datetime import datetime, timezone

from app.services.catalogue import Title, safe_url


def parse_date(value):
	try:
		parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
		return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
	except (ValueError, TypeError, AttributeError):
		return None


def local_range(programme):
	start, end = parse_date(programme.get("start")), parse_date(programme.get("end"))
	if not start or not end:
		return "Horario no disponible"
	start, end = start.astimezone(), end.astimezone()
	return start.strftime("%H:%M") + "–" + end.strftime("%H:%M") + (end.strftime(" (%d/%m)") if end.date() != start.date() else "")


def guide_titles(channels, now=None):
	"""No presenta un programa pasado como si aún se estuviera emitiendo."""
	now = now or datetime.now(timezone.utc)
	result = []
	for channel in channels:
		try:
			url = safe_url(channel["url"])
			name = channel["title"].strip()
			if not name:
				continue
			schedule = sorted([p for p in channel.get("schedule", []) if parse_date(p.get("start")) and parse_date(p.get("end"))], key=lambda p: parse_date(p["start"]))
			current = next((p for p in schedule if parse_date(p["start"]) <= now < parse_date(p["end"])), None)
			upcoming = next((p for p in schedule if parse_date(p["start"]) > now), None)
			current_text = current.get("title", "Programa sin título") if current else "Programación actual no disponible"
			next_text = upcoming.get("title", "Programa sin título") if upcoming else "Próximo programa no disponible"
			details = [channel.get("description", ""), "Ahora: " + current_text + (" · " + local_range(current) if current else ""), "A continuación: " + next_text + (" · " + local_range(upcoming) if upcoming else "")]
			if current and current.get("description"):
				details.append(current["description"])
			if channel.get("blocked"):
				details.append("ViX indica restricciones para este canal. Puede requerir una cuenta, suscripción u otra región.")
			details.append("Programación disponible (hora local):")
			for programme in schedule:
				if parse_date(programme["end"]) > now:
					details.append(local_range(programme) + " · " + programme.get("title", "Sin título"))
			groups = list(dict.fromkeys(channel.get("groups", [])))
			result.append(Title(str(channel.get("id", url)), name, "Canal", url, "\n".join(filter(None, details)), genres=", ".join(groups), groups=groups, channel_number=str(channel.get("number", "")), now_playing=current_text, next_programme=next_text, programme_time=local_range(current) if current else "No disponible"))
		except (ValueError, TypeError, KeyError, AttributeError):
			continue
	return sorted(result, key=lambda t: (int(t.channel_number) if t.channel_number.isdigit() else 999999, t.title.casefold()))


GUIDE_RUNTIME = r"""(() => {
 if(window.__vixClientCaptureGuide)return;
 const cache=window.__vixClientGuide={channels:{},categories:{},updated:0};
 window.__vixClientCaptureGuide=(payload,state={})=>{
  const seen=new WeakSet();let count=0;
  const resolve=v=>v?.__ref?state[v.__ref]||{}:v||{};
  const list=v=>Array.isArray(v)?v:v?.edges?.map(e=>e.node)||[];
  const text=v=>typeof v==='string'?v:'';
  const walk=(value,group='',depth=0)=>{
   if(!value||typeof value!=='object'||depth>20||seen.has(value)||count++>30000)return;
   seen.add(value);
   const v=resolve(value);
   if(v!==value){walk(v,group,depth+1);return}
   if(v.__typename==='EpgCategory'){
    cache.categories[v.id]=text(v.title);
    group=text(v.title)||group;
   }
   if(v.__typename==='EpgChannel'&&v.id&&v.title){
    const category=resolve(v.category),groups=[group,text(category.title)].filter(Boolean);
    const old=cache.channels[v.id];
    const metadata=v.pageAnalyticsMetadata?.keyValues||[];
    let path=metadata.find(k=>k.key==='screen_id')?.value;
    if(/^channel:mcp:callsign:[\w-]+$/.test(v.id))path='/canales/channel-callsign-'+v.id.split(':').slice(3).join(':');
    const schedule=[];
    for(const [key,entries] of Object.entries(v))if(key.startsWith('upcomingSchedule'))for(const entry of list(entries)){
     const p=resolve(entry),video=resolve(p.video);
     if(p.startDate&&p.endDate)schedule.push({title:text(p.title)||text(video.title),start:p.startDate,end:p.endDate,description:text(video.description)});
    }
    const merged=[...new Map([...(old?.schedule||[]),...schedule].map(p=>[p.start+'|'+p.end,p])).values()].filter(p=>Date.parse(p.end)>Date.now()-3600000).sort((a,b)=>Date.parse(a.start)-Date.parse(b.start)).slice(0,100);
    if(path&&path.startsWith('/canales/'))cache.channels[v.id]={id:v.id,title:text(v.title),number:v.channelNumber??old?.number??'',url:'https://vix.com'+path,description:text(v.description),groups:[...new Set([...(old?.groups||[]),...groups])],schedule:merged,blocked:!!v.channelAvailability?.isBlocked};
    cache.updated=Date.now();
   }
   for(const [key,child] of Object.entries(v))if(!/token|password|credential|stream|imageAssets|analytics/i.test(key))walk(child,group,depth+1);
  };
  walk(payload);
 };
})()"""


BROWSE_MEDIA_GUARD = r"""
document.addEventListener('play',event=>{if(!window.__vixClientPlaybackAllowed&&event.target?.tagName==='VIDEO')event.target.pause()},true);
"""
