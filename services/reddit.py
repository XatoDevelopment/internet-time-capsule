from bs4 import BeautifulSoup

from .wayback import SIN_DATOS, fecha_snap, snapshot, url_archivo

ORIGEN = "https://www.reddit.com/r/all/"


def obtener(d):
    # La API JSON de Reddit no permite filtrar por fecha real, así que usamos Wayback
    html, ts = snapshot(ORIGEN, d)
    if not html:
        return {"error": SIN_DATOS}

    soup = BeautifulSoup(html, "html.parser")
    titulo = None
    post = soup.find("shreddit-post")  # diseño nuevo de Reddit
    if post and post.get("post-title"):
        titulo = post["post-title"]
    if not titulo:
        enlace = soup.select_one("a.title")  # diseño antiguo (old.reddit)
        if enlace:
            titulo = enlace.get_text(strip=True)
    if not titulo:
        return {"error": "Reddit no tenía este día guardado 😴"}

    return {
        "titulo": titulo,
        "cita": "Primer post de r/all en la instantánea de ese día",
        "url": url_archivo(ts, ORIGEN),
        "instantanea": fecha_snap(ts),
    }
