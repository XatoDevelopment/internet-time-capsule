from datetime import datetime, timedelta

import requests

from .cliente import HEADERS, SESSION  # noqa: F401  (HEADERS se reexporta)

SIN_DATOS = "Internet no tenía este día 😴"
TIMEOUT = 20


def _cdx(url, d):
    """Busca capturas del mismo día (±1) y devuelve la más cercana al mediodía."""
    try:
        r = SESSION.get(
            "https://web.archive.org/cdx/search/cdx",
            params={
                "url": url,
                "from": f"{d - timedelta(days=1):%Y%m%d}",
                "to": f"{d + timedelta(days=1):%Y%m%d}",
                "output": "json",
                "filter": "statuscode:200",
                "limit": 60,
            },
            timeout=TIMEOUT,
        )
        filas = r.json() if r.status_code == 200 else []
    except (requests.RequestException, ValueError):
        return None
    if len(filas) < 2:
        return None
    objetivo = datetime(d.year, d.month, d.day, 12)
    mejor = min(filas[1:], key=lambda f: abs(datetime.strptime(f[1], "%Y%m%d%H%M%S") - objetivo))
    return mejor[1]


def _disponible(url, d):
    """Plan B: la API de disponibilidad de Wayback, aceptando hasta 2 días de diferencia."""
    try:
        r = SESSION.get(
            "https://archive.org/wayback/available",
            params={"url": url, "timestamp": f"{d:%Y%m%d}120000"},
            timeout=TIMEOUT,
        )
        cercano = (r.json().get("archived_snapshots") or {}).get("closest") or {}
    except (requests.RequestException, ValueError, AttributeError):
        return None
    if not cercano.get("available"):
        return None
    ts = cercano["timestamp"]
    if abs((datetime.strptime(ts[:8], "%Y%m%d").date() - d).days) > 2:
        return None
    return ts


def snapshot(url, d):
    """Devuelve (html, timestamp) de la captura de Wayback más cercana a la fecha."""
    ts = _cdx(url, d) or _disponible(url, d)
    if not ts:
        return None, None
    try:
        # "id_" devuelve el HTML original, sin la barra de Wayback
        r = SESSION.get(f"https://web.archive.org/web/{ts}id_/{url}", timeout=TIMEOUT)
        if r.status_code != 200:
            return None, None
        return r.text, ts
    except requests.RequestException:
        return None, None


def url_archivo(ts, url):
    return f"https://web.archive.org/web/{ts}/{url}"


def fecha_snap(ts):
    return f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
