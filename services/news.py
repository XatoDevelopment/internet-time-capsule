from bs4 import BeautifulSoup

from .wayback import SIN_DATOS, fecha_snap, snapshot, url_archivo

PERIODICOS = [
    ("The New York Times", "https://www.nytimes.com/"),
    ("BBC News", "https://www.bbc.com/news"),
    ("The Guardian", "https://www.theguardian.com/international"),
    ("El País", "https://elpais.com/"),
]


def _titulares(html, maximo=6):
    soup = BeautifulSoup(html, "html.parser")
    vistos, resultado = set(), []
    for h in soup.select("h1, h2, h3"):
        texto = h.get_text(" ", strip=True)
        if len(texto) < 25 or texto in vistos:
            continue
        vistos.add(texto)
        resultado.append(texto)
        if len(resultado) == maximo:
            break
    return resultado


def obtener(d):
    # Intenta periódico por periódico hasta encontrar una portada guardada ese día
    for nombre, url in PERIODICOS:
        html, ts = snapshot(url, d)
        if not html:
            continue
        titulares = _titulares(html)
        if not titulares:
            continue
        return {
            "titulo": titulares[0],
            "cita": f"Portada de {nombre} en la instantánea del día",
            "extra": nombre,
            "url": url_archivo(ts, url),
            "items": [{"texto": t, "url": url_archivo(ts, url)} for t in titulares[1:]],
            "instantanea": fecha_snap(ts),
        }
    return {"error": "Ningún periódico tenía su portada guardada este día 😴"}
