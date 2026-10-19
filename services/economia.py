from .cliente import get_json

API = "https://api.frankfurter.app"  # tipos de cambio del BCE desde 1999, sin clave


def obtener(d):
    datos = get_json(f"{API}/{d.isoformat()}", params={"from": "USD", "to": "EUR,GBP,MXN,JPY"})
    tasas = (datos or {}).get("rates") or {}
    if not tasas:
        return {"error": "Sin tipos de cambio para este día 😴"}

    return {
        "titulo": f"1 USD = {tasas.get('EUR', 0):.2f} EUR",
        "cita": "Tipos de cambio de referencia publicados por el Banco Central Europeo",
        "extra": f"Fecha de los datos: {datos.get('date', d.isoformat())} (día hábil más cercano)",
        "url": "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html",
        "items": [{"texto": f"1 USD = {v:.2f} {k}"} for k, v in tasas.items() if k != "EUR"],
        "instantanea": datos.get("date", d.isoformat()),
    }
