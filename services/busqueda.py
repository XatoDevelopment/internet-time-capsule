"""Búsqueda por palabra clave y rango de fechas en fuentes gratuitas, sin registro."""
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
    return {"items": [], "error": msg}


def _sin_etiquetas(texto):
    return html.unescape(re.sub(r"<[^>]+>", "", texto or "")).strip()


def _fecha_gdelt(s):
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if s and len(s) >= 8 else ""


def hackernews(q, desde, hasta, idioma):
    datos = get_json("https://hn.algolia.com/api/v1/search", params={
        "query": q,
        "tags": "story",
        "numericFilters": f"created_at_i>={_ts(desde)},created_at_i<={_ts(hasta, True)}",
        "hitsPerPage": 15,
    })
    if datos is None:
        return _error("No se pudo consultar Hacker News.")
    hits = [h for h in datos.get("hits", []) if h.get("title")]
    hits.sort(key=lambda h: h.get("points") or 0, reverse=True)
    return {"items": [{
        "texto": f"{h['title']} · {h.get('points') or 0} puntos",
        "url": h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
        "fecha": (h.get("created_at") or "")[:10],
    } for h in hits[:10]]}


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
        "pagesize": 10,
    })
    if datos is None:
        return _error("No se pudo consultar Stack Overflow.")
    return {"items": [{
        "texto": f"{html.unescape(p['title'])} · {p.get('score', 0)} votos",
        "url": p["link"],
        "fecha": datetime.fromtimestamp(p["creation_date"], timezone.utc).date().isoformat(),
    } for p in datos.get("items", [])]}


def gdelt(q, desde, hasta, idioma):
    lengua = {"en": "english", "es": "spanish"}[idioma]
    datos = get_json(GDELT_API, params={
        "query": f"{q} sourcelang:{lengua}".strip(),
        "mode": "artlist",
        "maxrecords": 15,
        "format": "json",
        "sort": "datedesc",
        "startdatetime": f"{desde:%Y%m%d}000000",
        "enddatetime": f"{hasta:%Y%m%d}235959",
    }, timeout=20, limitador=GDELT)
    if datos is None:
        return _error("GDELT no respondió. Limita una consulta cada 5 segundos, prueba de nuevo.")
    return {"items": [{
        "texto": f"{a['title']} · {a.get('domain', '')}",
        "url": a["url"],
        "fecha": _fecha_gdelt(a.get("seendate", "")),
    } for a in datos.get("articles") or [] if a.get("title")]}


def musicbrainz(q, desde, hasta, idioma):
    partes = [f"firstreleasedate:[{desde.isoformat()} TO {hasta.isoformat()}]", "primarytype:album"]
    if q:
        limpio = q.replace('"', "")
        partes.insert(0, f'releasegroup:"{limpio}"')
    datos = get_json("https://musicbrainz.org/ws/2/release-group/", params={
        "query": " AND ".join(partes),
        "fmt": "json",
        "limit": 10,
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
            "fecha": g.get("first-release-date", ""),
        })
    return {"items": items}


def wikipedia(q, desde, hasta, idioma):
    if not q:
        return _error("Escribe una palabra clave para buscar en Wikipedia.")
    datos = get_json(f"https://{idioma}.wikipedia.org/w/api.php", params={
        "action": "query",
        "list": "search",
        "srsearch": q,
        "srlimit": 10,
        "format": "json",
    })
    if datos is None:
        return _error("No se pudo consultar Wikipedia.")
    resultados = (datos.get("query") or {}).get("search", [])
    return {"items": [{
        "texto": f"{r['title']} — {_sin_etiquetas(r.get('snippet'))}",
        "url": f"https://{idioma}.wikipedia.org/wiki/{quote(r['title'].replace(' ', '_'))}",
        "fecha": "",
    } for r in resultados]}


FUENTES_BUSQUEDA = {
    "hackernews": hackernews,
    "stackoverflow": stackoverflow,
    "gdelt": gdelt,
    "musicbrainz": musicbrainz,
    "wikipedia": wikipedia,
}


def _ejecutar(nombre, q, desde, hasta, idioma):
    rango = f"{desde.isoformat()}..{hasta.isoformat()}"
    clave = f"busq:{nombre}:{idioma}:{q.lower()}"
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
