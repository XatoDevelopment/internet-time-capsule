import json
import logging
import os
import sqlite3
import time
from contextlib import closing

log = logging.getLogger(__name__)

RUTA = os.environ.get(
    "ITC_DB",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache_v2.db"),
)
TTL_OK = 30 * 24 * 3600
TTL_ERROR = 2 * 24 * 3600


def _conectar():
    return sqlite3.connect(RUTA, timeout=10)


def init():
    with closing(_conectar()) as con, con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS cache (
                fecha TEXT NOT NULL,
                fuente TEXT NOT NULL,
                json_data TEXT NOT NULL,
                ok INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                PRIMARY KEY (fecha, fuente)
            )"""
        )


def leer(fecha, fuente):
    with closing(_conectar()) as con:
        fila = con.execute(
            "SELECT json_data, ok, created_at FROM cache WHERE fecha=? AND fuente=?",
            (fecha, fuente),
        ).fetchone()
    if not fila:
        return None
    datos, ok, creado = fila
    if time.time() - creado > (TTL_OK if ok else TTL_ERROR):
        return None
    return json.loads(datos)


def guardar(fecha, fuente, datos):
    ok = 0 if "error" in datos else 1
    try:
        with closing(_conectar()) as con, con:
            con.execute(
                "INSERT OR REPLACE INTO cache (fecha, fuente, json_data, ok, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (fecha, fuente, json.dumps(datos, ensure_ascii=False), ok, int(time.time())),
            )
    except sqlite3.Error:
        log.exception("No se pudo guardar en caché %s/%s", fecha, fuente)
