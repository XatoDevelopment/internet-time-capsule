from .cliente import get_json

API = "https://date.nager.at/api/v3/PublicHolidays"  # sin clave
PAISES = [("ES", "España"), ("MX", "México"), ("AR", "Argentina"),
          ("CO", "Colombia"), ("US", "EE. UU."), ("GB", "Reino Unido")]


def obtener(d):
    festivos, consultados = [], []
    for codigo, nombre in PAISES:
        datos = get_json(f"{API}/{d.year}/{codigo}")
        if datos is None:
            continue
        consultados.append(nombre)
        nombres = [f.get("localName", "") for f in datos if f.get("date") == d.isoformat()]
        if nombres:
            festivos.append({"texto": f"{nombre}: {', '.join(nombres)}"})

    if not consultados:
        return {"error": "No se pudo consultar el calendario de festivos."}

    if festivos:
        titulo, cita = festivos[0]["texto"], f"Día festivo en {len(festivos)} de los países consultados"
    else:
        titulo, cita = "Día laborable en los países consultados", "Ningún festivo nacional ese día"
    return {
        "titulo": titulo,
        "cita": cita,
        "extra": "Países: " + ", ".join(consultados),
        "url": "https://date.nager.at/",
        "items": festivos[1:],
        "instantanea": d.isoformat(),
    }
