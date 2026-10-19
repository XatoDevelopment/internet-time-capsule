import html
from datetime import datetime, timezone

from .cliente import get_json


def obtener(d):
    inicio = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())
    datos = get_json("https://api.stackexchange.com/2.3/questions", params={
        "fromdate": inicio,
        "todate": inicio + 86399,
        "order": "desc",
        "sort": "votes",
        "site": "stackoverflow",
        "pagesize": 6,
    })
    preguntas = (datos or {}).get("items") or []
    if not preguntas:
        return {"error": "Sin preguntas destacadas en Stack Overflow ese día 😴"}

    top = preguntas[0]
    autor = (top.get("owner") or {}).get("display_name", "anónimo")
    return {
        "titulo": html.unescape(top["title"]),
        "cita": f"Pregunta más votada de ese día: {top.get('score', 0)} votos y {top.get('answer_count', 0)} respuestas",
        "extra": f"Por {html.unescape(autor)}",
        "url": top["link"],
        "items": [
            {"texto": f"{html.unescape(q['title'])} · {q.get('score', 0)} votos", "url": q["link"]}
            for q in preguntas[1:6]
        ],
        "instantanea": d.isoformat(),
    }
