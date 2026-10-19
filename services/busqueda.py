"""Búsqueda por palabra clave y rango de fechas en fuentes gratuitas, sin registro.

Mejoras v2.1:
- Más resultados por fuente y ranking por relevancia/puntuación
- Reddit (vía Algolia de HN no; búsqueda textual en títulos de HN + GDELT cubre mucho)
- Wikipedia: búsqueda + página de eventos del día cuando el rango es un solo día
- MusicBrainz con artistas y álbumes
- Resumen de totales y sugerencias de rangos populares
- Caché por fuente + rango + idioma
"""
import html
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import quote

from . import cache
from .cliente import GDELT, MUSICBRAINZ, get_json

log = logging.getLogger(__name__)
GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"


def _ts(d, fin=False):
    inicio = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())
    return inicio + 86399 if fin else inicio


def _error(msg):
    return {"items": [], "error": msg, "total": 0}


def _sin_etiquetas(texto):
    return html.unescape(re.sub(r"<[^>]+>", "", texto or "")).strip()


def _fecha_gdelt(s):
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if s and len(s) >= 8 else ""


def hackernews(q, desde, hasta, idioma):
    params = {
        "tags": "story",
        "numericFilters": f"created_at_i>={_ts(desde)},created_at_i<={_ts(hasta, True)}",
        "hitsPerPage": 25,
    }
    if q:
        params["query"] = q
    else:
        params["query"] = ""
        params["tags"] = "story"
    datos = get_json("https://hn.algolia.com/api/v1/search", params=params)
    if datos is None:
        return _error("No se pudo consultar Hacker News.")
    hits = [h for h in datos.get("hits", []) if h.get("title")]
    # Ranking: puntos primero, luego comentarios
    hits.sort(key=lambda h: (h.get("points") or 0, h.get("num_comments") or 0), reverse=True)
    items = [{
        "texto": f"{h['title']} · {h.get('points') or 0} pts · {h.get('num_comments') or 0} com.",
        "url": h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
        "fecha": (h.get("created_at") or "")[:10],
        "score": h.get("points") or 0,
    } for h in hits[:15]]
    return {"items": items, "total": len(items)}


def stackoverflow(q, desde, hasta, idioma):
    if not q:
        return _error("Escribe una palabra clave para buscar en Stack Overflow.")
    datos = get_json("https://api.stackexchange.com/2.3/search/advanced", params={
        "q": q,
        "fromdate": _ts(desde),
        "todate": _ts(hasta, True),
        "order": "desc",
        "sort": "votes",
        "site": "stackoverflow",
        "pagesize": 15,
        "filter": "default",
    })
    if datos is None:
        return _error("No se pudo consultar Stack Overflow.")
    items = [{
        "texto": f"{html.unescape(p['title'])} · {p.get('score', 0)} votos · {p.get('answer_count', 0)} resp.",
        "url": p["link"],
        "fecha": datetime.fromtimestamp(p["creation_date"], timezone.utc).date().isoformat(),
        "score": p.get("score", 0),
    } for p in datos.get("items", [])]
    return {"items": items, "total": len(items)}


def gdelt(q, desde, hasta, idioma):
    lengua = {"en": "english", "es": "spanish"}.get(idioma, "english")
    query = f"{q} sourcelang:{lengua}".strip() if q else f"sourcelang:{lengua}"
    datos = get_json(GDELT_API, params={
        "query": query,
        "mode": "artlist",
        "maxrecords": 20,
        "format": "json",
        "sort": "datedesc",
        "startdatetime": f"{desde:%Y%m%d}000000",
        "enddatetime": f"{hasta:%Y%m%d}235959",
    }, timeout=22, limitador=GDELT)
    if datos is None:
        return _error("GDELT no respondió. Limita una consulta cada 5 segundos, prueba de nuevo.")
    items = [{
        "texto": f"{a['title']} · {a.get('domain', '')}",
        "url": a["url"],
        "fecha": _fecha_gdelt(a.get("seendate", "")),
        "score": 0,
    } for a in datos.get("articles") or [] if a.get("title")]
    return {"items": items[:15], "total": len(items)}


def musicbrainz(q, desde, hasta, idioma):
    partes = [f"firstreleasedate:[{desde.isoformat()} TO {hasta.isoformat()}]", "primarytype:album"]
    if q:
        limpio = q.replace('"', "").strip()
        if limpio:
            partes.insert(0, f'(releasegroup:"{limpio}" OR artist:"{limpio}")')
    datos = get_json("https://musicbrainz.org/ws/2/release-group/", params={
        "query": " AND ".join(partes),
        "fmt": "json",
        "limit": 15,
    }, limitador=MUSICBRAINZ)
    if datos is None:
        return _error("No se pudo consultar MusicBrainz.")
    items = []
    for g in datos.get("release-groups") or []:
        creditos = g.get("artist-credit") or [{}]
        artista = (creditos[0] or {}).get("name", "")
        items.append({
            "texto": f"{g['title']} · {artista}",
            "url": f"https://musicbrainz.org/release-group/{g['id']}",
            "fecha": (g.get("first-release-date") or "")[:10],
            "score": 0,
        })
    return {"items": items, "total": len(items)}


def wikipedia(q, desde, hasta, idioma):
    if not q:
        return _error("Escribe una palabra clave para buscar en Wikipedia.")
    datos = get_json(f"https://{idioma}.wikipedia.org/w/api.php", params={
        "action": "query",
        "list": "search",
        "srsearch": q,
        "srlimit": 12,
        "srprop": "snippet|timestamp",
        "format": "json",
    })
    if datos is None:
        return _error("No se pudo consultar Wikipedia.")
    resultados = (datos.get("query") or {}).get("search", [])
    items = [{
        "texto": f"{r['title']} — {_sin_etiquetas(r.get('snippet'))}",
        "url": f"https://{idioma}.wikipedia.org/wiki/{quote(r['title'].replace(' ', '_'))}",
        "fecha": (r.get("timestamp") or "")[:10],
        "score": 0,
    } for r in resultados]
    return {"items": items, "total": len(items)}


def wikipedia_eventos(q, desde, hasta, idioma):
    """Cuando el rango es un solo día, muestra eventos de ese día (On This Day)."""
    if desde != hasta:
        return {"items": [], "total": 0, "omitido": True}
    # API de efemérides de Wikipedia
    mes_dia = f"{desde.month:02d}/{desde.day:02d}"
    datos = get_json(
        f"https://api.wikimedia.org/feed/v1/wikipedia/{idioma}/onthisday/all/{mes_dia}",
        timeout=15,
    )
    if datos is None:
        return _error("No se pudieron cargar las efemérides.")
    items = []
    for seccion in ("events", "births", "deaths", "holidays"):
        for ev in (datos.get(seccion) or [])[:8]:
            texto = ev.get("text") or ""
            if q and q.lower() not in texto.lower():
                continue
            anio = ""
            paginas = ev.get("pages") or []
            titulo = paginas[0].get("titles", {}).get("normalized") if paginas else ""
            url = ""
            if paginas:
                url = paginas[0].get("content_urls", {}).get("desktop", {}).get("page", "")
            if not texto and titulo:
                texto = titulo
            if not texto:
                continue
            year = ev.get("year")
            if year:
                anio = str(year)
            items.append({
                "texto": f"{anio + ' · ' if anio else ''}{texto[:180]}",
                "url": url or f"https://{idioma}.wikipedia.org/wiki/Special:OnThisDay",
                "fecha": desde.isoformat(),
                "score": 0,
            })
            if len(items) >= 12:
                break
        if len(items) >= 12:
            break
    return {"items": items, "total": len(items)}


FUENTES_BUSQUEDA = {
    "hackernews": hackernews,
    "stackoverflow": stackoverflow,
    "gdelt": gdelt,
    "musicbrainz": musicbrainz,
    "wikipedia": wikipedia,
    "eventos": wikipedia_eventos,
}


def _ejecutar(nombre, q, desde, hasta, idioma):
    rango = f"{desde.isoformat()}..{hasta.isoformat()}"
    clave = f"busq:v2:{nombre}:{idioma}:{q.lower()}"
    en_cache = cache.leer(rango, clave)
    if en_cache is not None:
        return en_cache
    try:
        datos = FUENTES_BUSQUEDA[nombre](q, desde, hasta, idioma)
    except Exception:
        log.exception("Fallo en la búsqueda %s", nombre)
        datos = _error("Fallo inesperado en esta fuente.")
    cache.guardar(rango, clave, datos)
    return datos


def buscar(q, desde, hasta, idioma):
    with ThreadPoolExecutor(max_workers=len(FUENTES_BUSQUEDA)) as pool:
        futuros = {n: pool.submit(_ejecutar, n, q, desde, hasta, idioma) for n in FUENTES_BUSQUEDA}
        return {n: f.result() for n, f in futuros.items()}
