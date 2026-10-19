"""Cliente HTTP compartido: reintentos automáticos y límites por servicio."""
import threading
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HEADERS = {
    "User-Agent": "InternetTimeCapsule/2.1 (XatoDev; Xatodev.contacto@gmail.com)",
    "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
}


def _crear_sesion():
    s = requests.Session()
    s.headers.update(HEADERS)
    reintentos = Retry(
        total=2,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
    )
    s.mount("https://", HTTPAdapter(max_retries=reintentos))
    return s


SESSION = _crear_sesion()


class Limitador:
    """Garantiza un intervalo mínimo entre peticiones a un mismo servicio."""

    def __init__(self, segundos):
        self.segundos = segundos
        self._ultimo = 0.0
        self._lock = threading.Lock()

    def esperar(self):
        with self._lock:
            falta = self.segundos - (time.monotonic() - self._ultimo)
            if falta > 0:
                time.sleep(falta)
            self._ultimo = time.monotonic()


GDELT = Limitador(5.5)        # GDELT pide 1 petición cada 5 segundos
MUSICBRAINZ = Limitador(1.2)  # MusicBrainz pide 1 petición por segundo


def get_json(url, params=None, timeout=12, limitador=None):
    if limitador:
        limitador.esperar()
    try:
        r = SESSION.get(url, params=params, timeout=timeout)
        if r.status_code != 200:
            return None
        return r.json()
    except (requests.RequestException, ValueError):
        return None
