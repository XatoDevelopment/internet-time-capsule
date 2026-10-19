from datetime import datetime, timezone

from .cliente import get_json

API = "https://hn.algolia.com/api/v1/search"  # Hacker News existe desde 2006


def _enlace(h):
    return h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}"


def obtener(d):
    inicio = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())
    datos = get_json(API, params={
        "tags": "story",
        "numericFilters": f"created_at_i>={inicio},created_at_i<={inicio + 86399}",
        "hitsPerPage": 100,
    })
    if datos is None:
        return {"error": "No se pudo consultar Hacker News."}

    hits = [h for h in datos.get("hits", []) if h.get("title")]
    if not hits:
        return {"error": "Hacker News no tenía historias ese día 😴"}

    hits.sort(key=lambda h: h.get("points") or 0, reverse=True)
    top = hits[0]
    return {
        "titulo": top["title"],
        "cita": f"Historia más votada de ese día: {top.get('points') or 0} puntos y {top.get('num_comments') or 0} comentarios",
        "extra": f"Por {top.get('author', 'anónimo')}",
        "url": _enlace(top),
        "items": [
            {"texto": f"{h['title']} · {h.get('points') or 0} puntos", "url": _enlace(h)}
            for h in hits[1:6]
        ],
        "instantanea": d.isoformat(),
    }
