from .cliente import get_json

API = "https://query.wikidata.org/sparql"  # sin clave

PLANTILLA = """
SELECT ?item ?itemLabel ?tipoLabel WHERE {
  { ?item wdt:P31 wd:Q11424 . BIND(wd:Q11424 AS ?tipo) }
  UNION
  { ?item wdt:P31 wd:Q7889 . BIND(wd:Q7889 AS ?tipo) }
  ?item wdt:P577 ?fecha .
  FILTER(?fecha = "FECHAT00:00:00Z"^^xsd:dateTime)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "es,en". }
}
LIMIT 12
"""


def obtener(d):
    consulta = PLANTILLA.replace("FECHA", d.isoformat())
    datos = get_json(API, params={"query": consulta, "format": "json"}, timeout=20)
    if datos is None:
        return {"error": "Wikidata no respondió (la consulta puede tardar; prueba de nuevo)."}

    vistos, filas = set(), []
    for b in datos.get("results", {}).get("bindings", []):
        nombre = b.get("itemLabel", {}).get("value", "")
        if not nombre or (nombre.startswith("Q") and nombre[1:].isdigit()):
            continue  # sin etiqueta legible
        if nombre in vistos:
            continue
        vistos.add(nombre)
        filas.append({
            "texto": f"{nombre} · {b.get('tipoLabel', {}).get('value', '')}",
            "url": b["item"]["value"],
        })

    if not filas:
        return {"error": "Ningún estreno de cine ni videojuego registrado ese día 😴"}

    return {
        "titulo": filas[0]["texto"],
        "cita": "Películas y videojuegos con esa fecha de publicación en Wikidata",
        "url": filas[0]["url"],
        "items": filas[1:7],
        "instantanea": d.isoformat(),
    }
