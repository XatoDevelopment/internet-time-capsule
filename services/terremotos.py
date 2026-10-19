from datetime import timedelta

from .cliente import get_json

API = "https://earthquake.usgs.gov/fdsnws/event/1/query"  # USGS, sin clave


def obtener(d):
    datos = get_json(API, params={
        "format": "geojson",
        "starttime": d.isoformat(),
        "endtime": (d + timedelta(days=1)).isoformat(),
        "minmagnitude": 4.5,
        "orderby": "magnitude",
        "limit": 6,
    })
    if datos is None:
        return {"error": "No se pudo consultar el catálogo sísmico del USGS."}

    eventos = datos.get("features") or []
    if not eventos:
        return {
            "titulo": "Día tranquilo: ningún sismo de magnitud 4,5 o más",
            "cita": "Según el catálogo sísmico del USGS",
            "url": "https://earthquake.usgs.gov/earthquakes/search/",
            "instantanea": d.isoformat(),
        }

    def texto(e):
        p = e["properties"]
        return f"M{p.get('mag', '?')} · {p.get('place', 'lugar desconocido')}"

    primero = eventos[0]["properties"]
    return {
        "titulo": texto(eventos[0]),
        "cita": "Sismo más fuerte registrado por el USGS ese día",
        "extra": f"{len(eventos)} sismos de magnitud 4,5 o más",
        "url": primero.get("url"),
        "items": [{"texto": texto(e), "url": e["properties"].get("url")} for e in eventos[1:6]],
        "instantanea": d.isoformat(),
    }
