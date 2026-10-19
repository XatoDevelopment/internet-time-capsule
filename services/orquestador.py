import logging
from concurrent.futures import ThreadPoolExecutor

from . import (apod, cache, clima, discos, economia, festivos, gdelt, hackernews,
               lanzamientos, news, reddit, stackoverflow, terremotos, wikipedia)
from .wayback import SIN_DATOS

log = logging.getLogger(__name__)

FUENTES = {
    "wikipedia": wikipedia.obtener,
    "wikipedia_es": wikipedia.obtener_es,
    "efemerides": wikipedia.efemerides,
    "actualidad": wikipedia.actualidad,
    "reddit": reddit.obtener,
    "hackernews": hackernews.obtener,
    "stackoverflow": stackoverflow.obtener,
    "gdelt": gdelt.obtener,
    "noticias": news.obtener,
    "apod": apod.obtener,
    "clima": clima.obtener,
    "terremotos": terremotos.obtener,
    "economia": economia.obtener,
    "discos": discos.obtener,
    "lanzamientos": lanzamientos.obtener,
    "festivos": festivos.obtener,
}


def get_source(nombre, d, ciudad=None):
    if nombre == "clima":
        ciudad = ciudad if ciudad in clima.CIUDADES else "madrid"
        clave = f"clima:{ciudad}"
        funcion = lambda dd: clima.obtener(dd, ciudad)
    else:
        clave = nombre
        funcion = FUENTES[nombre]

    en_cache = cache.leer(d.isoformat(), clave)
    if en_cache is not None:
        return en_cache

    try:
        datos = funcion(d)
    except Exception:  # una fuente rota nunca tumba la cápsula
        log.exception("Fallo en la fuente %s", clave)
        datos = {"error": SIN_DATOS}

    cache.guardar(d.isoformat(), clave, datos)
    return datos


def get_all(d):
    with ThreadPoolExecutor(max_workers=len(FUENTES)) as pool:
        futuros = {n: pool.submit(get_source, n, d) for n in FUENTES}
        return {n: f.result() for n, f in futuros.items()}
