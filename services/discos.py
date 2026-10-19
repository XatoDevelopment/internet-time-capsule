from .cliente import MUSICBRAINZ, get_json

API = "https://musicbrainz.org/ws/2/release-group/"  # sin clave; el User-Agent se envía


def _artista(g):
    creditos = g.get("artist-credit") or [{}]
    return (creditos[0] or {}).get("name", "")


def obtener(d):
    datos = get_json(API, params={
        "query": f"firstreleasedate:{d.isoformat()} AND primarytype:album",
        "fmt": "json",
        "limit": 8,
    }, limitador=MUSICBRAINZ)
    if datos is None:
        return {"error": "No se pudo consultar MusicBrainz."}

    grupos = datos.get("release-groups") or []
    if not grupos:
        return {"error": "No hay álbumes registrados con esa fecha 😴"}

    primero = grupos[0]
    return {
        "titulo": primero["title"],
        "cita": f"Álbum publicado ese día por {_artista(primero) or 'artista desconocido'}",
        "extra": "Base de datos MusicBrainz",
        "url": f"https://musicbrainz.org/release-group/{primero['id']}",
        "items": [
            {"texto": f"{g['title']} · {_artista(g)}", "url": f"https://musicbrainz.org/release-group/{g['id']}"}
            for g in grupos[1:7]
        ],
        "instantanea": d.isoformat(),
    }
