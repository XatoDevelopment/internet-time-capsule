"""Internet Time Capsule — creado por XatoDev (Xatodev.contacto@gmail.com)."""
import os
from datetime import date, timedelta
from urllib.parse import urlparse

from flask import Flask, Response, abort, jsonify, render_template, request, send_file

from services import busqueda, cache, clima, imagen, orquestador
from services.cliente import SESSION

MIN_DATE = date(2006, 1, 1)
POPULARES = [
    {"fecha": "2007-01-09", "titulo": "Steve Jobs presenta el iPhone"},
    {"fecha": "2012-12-21", "titulo": "Fin del mundo maya"},
    {"fecha": "2016-11-08", "titulo": "Elecciones en EE. UU."},
    {"fecha": "2019-04-15", "titulo": "Incendio de Notre-Dame"},
    {"fecha": "2020-03-11", "titulo": "La OMS declara pandemia"},
]
IMG_HOSTS = {"upload.wikimedia.org", "thumb.wikimedia.org", "apod.nasa.gov"}
MAX_IMG_BYTES = 8 * 1024 * 1024
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

AUTHOR = "XatoDev"
AUTHOR_EMAIL = "Xatodev.contacto@gmail.com"
VERSION = "2.1.0"

_ROOT = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(_ROOT, "templates"),
    static_folder=os.path.join(_ROOT, "static"),
)
cache.init()


def fecha_por_defecto(hoy):
    try:
        return hoy.replace(year=hoy.year - 10)
    except ValueError:  # 29 de febrero
        return hoy.replace(year=hoy.year - 10, day=28)


def fecha_larga(d):
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}"


def leer_fecha(texto):
    """Devuelve la fecha si es válida (entre 2006 y hoy), o None."""
    try:
        d = date.fromisoformat(texto or "")
    except ValueError:
        return None
    return d if MIN_DATE <= d <= date.today() else None


def parse_fecha(texto):
    d = leer_fecha(texto)
    if d is None:
        abort(400, "Fecha no válida (de 2006 a hoy, formato YYYY-MM-DD)")
    return d


@app.context_processor
def inject_meta():
    return {
        "author": AUTHOR,
        "author_email": AUTHOR_EMAIL,
        "version": VERSION,
    }


@app.route("/")
def index():
    hoy = date.today()
    return render_template(
        "index.html",
        default=fecha_por_defecto(hoy).isoformat(),
        min=MIN_DATE.isoformat(),
        max=hoy.isoformat(),
        populares=POPULARES,
    )


@app.route("/buscar")
def buscar_page():
    hoy = date.today()
    return render_template(
        "buscar.html",
        default=fecha_por_defecto(hoy).isoformat(),
        min=MIN_DATE.isoformat(),
        max=hoy.isoformat(),
    )


@app.route("/acerca")
def acerca():
    return render_template("acerca.html")


@app.route("/capsula/<fecha>")
def capsula(fecha):
    d = parse_fecha(fecha)
    siguiente = d + timedelta(days=1)
    return render_template(
        "capsule.html",
        fecha=d.isoformat(),
        fecha_larga=fecha_larga(d),
        anterior=(d - timedelta(days=1)).isoformat() if d > MIN_DATE else None,
        siguiente=siguiente.isoformat() if siguiente <= date.today() else None,
        ciudades=[(k, v[0]) for k, v in clima.CIUDADES.items()],
    )


@app.route("/api/capsule/<fecha>")
def api_capsule(fecha):
    d = parse_fecha(fecha)
    return jsonify({"fecha": d.isoformat(), "fuentes": orquestador.get_all(d)})


@app.route("/api/capsule/<fecha>/<fuente>")
def api_fuente(fecha, fuente):
    d = parse_fecha(fecha)
    if fuente not in orquestador.FUENTES:
        abort(404)
    return jsonify(orquestador.get_source(fuente, d, request.args.get("ciudad")))


@app.route("/api/buscar")
def api_buscar():
    q = (request.args.get("q") or "").strip()[:80]
    idioma = request.args.get("idioma")
    if idioma not in ("en", "es"):
        idioma = "en"
    desde = leer_fecha(request.args.get("desde"))
    hasta = leer_fecha(request.args.get("hasta")) or desde
    if desde is None or hasta is None:
        return jsonify({"error": "Indica una fecha válida (de 2006 a hoy)."}), 400
    if desde > hasta:
        desde, hasta = hasta, desde
    if (hasta - desde).days > 366:
        return jsonify({"error": "El rango máximo es de un año."}), 400
    fuentes = busqueda.buscar(q, desde, hasta, idioma)
    total = sum(f.get("total", len(f.get("items") or [])) for f in fuentes.values() if not f.get("omitido"))
    return jsonify({
        "q": q,
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "total": total,
        "fuentes": fuentes,
    })


@app.route("/img")
def imagen_proxy():
    url = request.args.get("u", "")
    p = urlparse(url)
    if p.scheme != "https" or p.hostname not in IMG_HOSTS:
        abort(400)
    try:
        r = SESSION.get(url, timeout=15)
    except Exception:
        abort(502)
    tipo = r.headers.get("Content-Type", "")
    if r.status_code != 200 or not tipo.startswith("image/") or len(r.content) > MAX_IMG_BYTES:
        abort(404)
    resp = Response(r.content, mimetype=tipo)
    resp.headers["Cache-Control"] = "public, max-age=604800"
    return resp


@app.route("/share/<fecha>.png")
def share(fecha):
    d = parse_fecha(fecha)
    datos = orquestador.get_all(d)
    return send_file(
        imagen.render(d.isoformat(), datos),
        mimetype="image/png",
        as_attachment=request.args.get("descargar") == "1",
        download_name=f"capsula-{d.isoformat()}.png",
    )


@app.route("/share/<fecha>/apod.png")
def share_apod(fecha):
    """Descarga solo la foto NASA del día en formato vertical (stories)."""
    d = parse_fecha(fecha)
    datos = orquestador.get_source("apod", d)
    buf = imagen.render_apod(datos)
    if buf is None:
        abort(404, "No hay imagen APOD disponible para esta fecha.")
    return send_file(
        buf,
        mimetype="image/png",
        as_attachment=request.args.get("descargar") == "1",
        download_name=f"nasa-apod-{d.isoformat()}.png",
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok", "version": VERSION, "author": AUTHOR})


def main():
    """Punto de entrada para `internet-time-capsule` / `itc` tras instalar el paquete."""
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    print(f"Internet Time Capsule v{VERSION} · por {AUTHOR} <{AUTHOR_EMAIL}>")
    print(f"→ http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
