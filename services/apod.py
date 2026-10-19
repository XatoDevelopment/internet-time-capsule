import os
from datetime import date
from urllib.parse import urlparse

from .cliente import get_json

PRIMERA = date(1995, 6, 16)


def obtener(d):
    if d < PRIMERA:
        return {"error": "La NASA no publicó esta imagen antes de 1995 😴"}

    # DEMO_KEY funciona sin registro. NASA_API_KEY es opcional para más cuota.
    clave = os.environ.get("NASA_API_KEY", "DEMO_KEY")
    j = get_json("https://api.nasa.gov/planetary/apod", params={
        "date": d.isoformat(),
        "api_key": clave,
        "thumbs": "true",
    })
    if not j or "title" not in j:
        return {"error": "La NASA no respondió. Puede que se haya agotado la cuota de DEMO_KEY."}

    imagen = j.get("url") if j.get("media_type") == "image" else j.get("thumbnail_url")
    if imagen:
        imagen = imagen.replace("http://", "https://", 1)
        if urlparse(imagen).hostname != "apod.nasa.gov":
            imagen = None

    texto = j.get("explanation", "")
    return {
        "titulo": j.get("title", "Astronomy Picture of the Day"),
        "cita": texto[:280] + ("…" if len(texto) > 280 else ""),
        "extra": "NASA · Astronomy Picture of the Day (texto en inglés)",
        "imagen": imagen,
        "hero": imagen,
        "url": j.get("hdurl") or j.get("url") or "https://apod.nasa.gov/apod/",
        "instantanea": d.isoformat(),
    }
