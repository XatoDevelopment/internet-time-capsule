import html
import re
from urllib.parse import quote

from .cliente import get_json

IGNORADOS = ("Main Page", "Portada", "Special:", "Especial:", "Wikipedia:", "Archivo:", "File:")


def _titulo(a):
    return ((a.get("titles") or {}).get("normalized") or a.get("title") or "").replace("_", " ")


def _enlace(a):
    return ((a or {}).get("content_urls") or {}).get("desktop", {}).get("page")


def _miniatura(a):
    return ((a or {}).get("thumbnail") or {}).get("source")


def _url_wiki(lang, titulo):
    return f"https://{lang}.wikipedia.org/wiki/{quote(titulo.replace(' ', '_'))}"


def _mas_leidos(lang, d):
    """Artículos más leídos del día. Usa el feed destacado y, si no hay datos, la API de visitas."""
    datos = get_json(f"https://{lang}.wikipedia.org/api/rest_v1/feed/featured/{d:%Y/%m/%d}")
    arts = ((datos or {}).get("mostread") or {}).get("articles", [])
    potd = _miniatura((datos or {}).get("image"))
    if not arts:
        pv = get_json(f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/{lang}.wikipedia/all-access/{d:%Y/%m/%d}")
        try:
            arts = [{"title": a["article"], "views": a["views"]} for a in pv["items"][0]["articles"]]
        except (TypeError, KeyError, IndexError):
            arts = []
    return potd, [a for a in arts if _titulo(a) and not _titulo(a).startswith(IGNORADOS)]


def _wiki(lang, d, etiqueta):
    potd, arts = _mas_leidos(lang, d)
    if not arts:
        return {"error": "Wikipedia no tenía datos de lectura para este día 😴"}

    primero = arts[0]
    titulo = _titulo(primero)
    extracto = primero.get("extract", "")
    imagen = _miniatura(primero)
    url = _enlace(primero)
    if not (extracto and imagen and url):
        resumen = get_json(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(titulo.replace(' ', '_'))}") or {}
        extracto = extracto or resumen.get("extract", "")
        imagen = imagen or (resumen.get("thumbnail") or {}).get("source")
        url = url or (resumen.get("content_urls") or {}).get("desktop", {}).get("page") or _url_wiki(lang, titulo)

    items = []
    for a in arts[1:6]:
        visitas = f"{a.get('views', 0):,}".replace(",", ".")
        items.append({
            "texto": f"{_titulo(a)} · {visitas} visitas",
            "url": _enlace(a) or _url_wiki(lang, _titulo(a)),
            "imagen": _miniatura(a),
        })

    return {
        "titulo": titulo,
        "cita": extracto[:260] + ("…" if len(extracto) > 260 else ""),
        "extra": f"Artículo más leído en {etiqueta} ese día",
        "imagen": imagen,
        "url": url,
        "items": items,
        "hero": potd,
        "instantanea": d.isoformat(),
    }


def obtener(d):
    return _wiki("en", d, "Wikipedia en inglés")


def obtener_es(d):
    return _wiki("es", d, "Wikipedia en español")


def efemerides(d):
    datos = get_json(f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{d:%m/%d}")
    eventos = (datos or {}).get("events") or []
    if not eventos:
        return {"error": "No hay efemérides para este día 😴"}

    eventos.sort(key=lambda e: 0 if _miniatura((e.get("pages") or [{}])[0]) else 1)
    items = []
    for e in eventos[:6]:
        pagina = (e.get("pages") or [{}])[0]
        items.append({
            "texto": f"{e.get('year', '')}: {e.get('text', '')[:180]}",
            "url": _enlace(pagina),
            "imagen": _miniatura(pagina),
        })
    return {
        "titulo": "Hechos destacados de este día",
        "cita": "Efemérides de la Wikipedia en inglés",
        "imagen": items[0]["imagen"],
        "url": items[0]["url"],
        "items": items,
        "instantanea": d.isoformat(),
    }


def actualidad(d):
    datos = get_json(f"https://en.wikipedia.org/api/rest_v1/feed/featured/{d:%Y/%m/%d}")
    noticias = (datos or {}).get("news") or []
    if not noticias:
        return {"error": "Sin noticias destacadas para este día 😴"}

    items = []
    for n in noticias[:6]:
        texto = html.unescape(re.sub(r"<[^>]+>", "", n.get("story", ""))).strip()
        enlaces = n.get("links") or []
        primero = enlaces[0] if enlaces else {}
        items.append({"texto": texto, "url": _enlace(primero), "imagen": _miniatura(primero)})

    return {
        "titulo": items[0]["texto"][:160],
        "cita": "Lo que Wikipedia destacaba como actualidad ese día",
        "imagen": items[0]["imagen"],
        "url": items[0]["url"],
        "items": items[1:],
        "instantanea": d.isoformat(),
    }
