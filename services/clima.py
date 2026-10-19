from datetime import date, timedelta

from .cliente import get_json

CIUDADES = {
    "madrid": ("Madrid", 40.4168, -3.7038),
    "mexico": ("Ciudad de México", 19.4326, -99.1332),
    "buenos-aires": ("Buenos Aires", -34.6037, -58.3816),
    "bogota": ("Bogotá", 4.7110, -74.0721),
    "nueva-york": ("Nueva York", 40.7128, -74.0060),
    "londres": ("Londres", 51.5072, -0.1276),
}

CODIGOS = {
    0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado", 3: "Nublado",
    45: "Niebla", 48: "Niebla con escarcha", 51: "Llovizna ligera", 53: "Llovizna",
    55: "Llovizna intensa", 61: "Lluvia ligera", 63: "Lluvia", 65: "Lluvia intensa",
    71: "Nieve ligera", 73: "Nevada", 75: "Nevada intensa", 80: "Chubascos ligeros",
    81: "Chubascos", 82: "Chubascos fuertes", 95: "Tormenta", 96: "Tormenta con granizo",
    99: "Tormenta fuerte",
}


def obtener(d, ciudad="madrid"):
    if ciudad not in CIUDADES:
        ciudad = "madrid"
    nombre, lat, lon = CIUDADES[ciudad]

    # El archivo meteorológico va con unos días de retraso
    if d > date.today() - timedelta(days=5):
        return {"ciudad": ciudad, "error": "Los datos meteorológicos llegan con unos días de retraso."}

    datos = get_json("https://archive-api.open-meteo.com/v1/archive", params={
        "latitude": lat,
        "longitude": lon,
        "start_date": d.isoformat(),
        "end_date": d.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
        "timezone": "auto",
    })
    try:
        diario = datos["daily"]
        titulo = f"Máx {diario['temperature_2m_max'][0]:.0f}° · Mín {diario['temperature_2m_min'][0]:.0f}°"
        prec = diario["precipitation_sum"][0] or 0
        estado = CODIGOS.get(diario["weather_code"][0], "Tiempo variable")
    except (TypeError, KeyError, IndexError):
        return {"ciudad": ciudad, "error": "Sin datos meteorológicos para este día 😴"}

    return {
        "ciudad": ciudad,
        "titulo": titulo,
        "cita": f"{estado}. Lluvia acumulada: {prec} mm.",
        "extra": f"Clima en {nombre}",
        "url": "https://open-meteo.com/",
        "instantanea": d.isoformat(),
    }
