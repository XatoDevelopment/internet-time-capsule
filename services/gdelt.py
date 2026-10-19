from .cliente import GDELT, get_json

API = "https://api.gdeltproject.org/api/v2/doc/doc"  # sin clave; cobertura desde 2015


def obtener(d):
    datos = get_json(
        API,
        params={
            "query": "sourcelang:english",
            "mode": "artlist",
            "maxrecords": 8,
            "format": "json",
            "startdatetime": f"{d:%Y%m%d}000000",
            "enddatetime": f"{d:%Y%m%d}235959",
        },
        timeout=20,
        limitador=GDELT,
    )
    arts = [a for a in (datos or {}).get("articles") or [] if a.get("title")]
    if not arts:
        return {"error": "GDELT no tenía titulares guardados para este día 😴"}

    return {
        "titulo": arts[0]["title"],
        "cita": "Titulares de medios de todo el mundo, en inglés (GDELT)",
        "extra": arts[0].get("domain", ""),
        "url": arts[0]["url"],
        "items": [
            {"texto": f"{a['title']} · {a.get('domain', '')}", "url": a["url"]}
            for a in arts[1:7]
        ],
        "instantanea": d.isoformat(),
    }
