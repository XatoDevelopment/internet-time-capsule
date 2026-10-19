"""Genera el póster PNG 1200x1600 en el servidor, con imágenes incluidas.

v2.1: créditos XatoDev, mejor tipografía, descarga de APOD HD.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .cliente import SESSION

W, H = 1200, 1600
PAPEL = (244, 239, 228)
TINTA = (29, 27, 24)
GRIS = (111, 106, 95)
CLARO = (241, 228, 207)
TARJETA = (255, 253, 247)
LINEA = (216, 208, 190)
VERDE = (10, 110, 90)
HOSTS_OK = {"upload.wikimedia.org", "thumb.wikimedia.org", "apod.nasa.gov"}

# (clave de la fuente, etiqueta, color)
TARJETAS = [
    ("wikipedia", "WIKIPEDIA", (29, 27, 24)),
    ("efemerides", "EFEMÉRIDES", (138, 90, 0)),
    ("reddit", "REDDIT", (255, 69, 0)),
    ("hackernews", "HACKER NEWS", (255, 102, 0)),
    ("apod", "NASA · FOTO DEL DÍA", (11, 61, 145)),
    ("clima", "CLIMA", (217, 119, 6)),
]

FUENTES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "fonts")
_fuentes = {}


def _fuente(tam, negrita=False):
    clave = (tam, negrita)
    if clave not in _fuentes:
        nombre = "DejaVuSans-Bold.ttf" if negrita else "DejaVuSans.ttf"
        rutas = [
            os.path.join(FUENTES_DIR, nombre),
            f"/usr/share/fonts/truetype/dejavu/{nombre}",
            "/system/fonts/Roboto-Bold.ttf" if negrita else "/system/fonts/Roboto-Regular.ttf",
        ]
        f = None
        for ruta in rutas:
            try:
                f = ImageFont.truetype(ruta, tam)
                break
            except OSError:
                continue
        if f is None:
            f = ImageFont.load_default(size=tam)
        _fuentes[clave] = f
    return _fuentes[clave]


def _limpio(texto):
    return "".join(c for c in str(texto) if ord(c) < 0x2600)


def _envolver(texto, fuente, ancho):
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if fuente.getlength(prueba) <= ancho:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def _bajar(url):
    if not url:
        return None
    p = urlparse(url)
    if p.scheme != "https" or p.hostname not in HOSTS_OK:
        return None
    try:
        r = SESSION.get(url, timeout=12)
        if r.status_code != 200:
            return None
        return Image.open(BytesIO(r.content)).convert("RGB")
    except Exception:
        return None


def _cabecera(img, hero, fecha):
    alto = 400
    if hero:
        img.paste(ImageOps.fit(hero, (W, alto)), (0, 0))
    else:
        ImageDraw.Draw(img).rectangle([0, 0, W, alto], fill=TINTA)

    velo = Image.new("RGBA", (W, alto), (0, 0, 0, 0))
    dv = ImageDraw.Draw(velo)
    for y in range(alto):
        dv.line([(0, y), (W, y)], fill=(0, 0, 0, int(60 + 150 * y / alto)))
    fondo = Image.alpha_composite(img.crop((0, 0, W, alto)).convert("RGBA"), velo).convert("RGB")
    img.paste(fondo, (0, 0))

    d = ImageDraw.Draw(img)
    d.text((60, 56), "INTERNET TIME CAPSULE", font=_fuente(30, True), fill=CLARO)
    d.text((56, 110), fecha, font=_fuente(120, True), fill=(255, 255, 255))
    d.text((60, 292), "Así estaba la red ese día", font=_fuente(32), fill=(230, 224, 212))


def _tarjeta(img, x, y, w, h, etiqueta, color, datos, foto):
    d = ImageDraw.Draw(img)
    d.rectangle([x, y, x + w, y + h], fill=TARJETA, outline=LINEA, width=2)
    d.rectangle([x, y, x + w, y + 8], fill=color)

    cy = y + 8
    if foto:
        img.paste(ImageOps.fit(foto, (w, 150)), (x, cy))
        cy += 150
    cy += 16

    pad = 22
    ancho = w - 2 * pad
    d.text((x + pad, cy), etiqueta, font=_fuente(20, True), fill=color)
    cy += 36

    if "error" in datos:
        titulo, cuerpo = None, _limpio(datos["error"])
    else:
        titulo = _limpio(datos.get("titulo", ""))
        cuerpo = _limpio(datos.get("cita") or datos.get("extra") or "")

    if titulo:
        lineas_t = _envolver(titulo, _fuente(28, True), ancho)
        if len(lineas_t) > 2:
            lineas_t = lineas_t[:2]
            lineas_t[-1] = lineas_t[-1].rstrip() + "…"
        for linea in lineas_t:
            d.text((x + pad, cy), linea, font=_fuente(28, True), fill=TINTA)
            cy += 36
        cy += 6

    fin = y + h - 46
    fc = _fuente(20)
    lineas_c = _envolver(cuerpo, fc, ancho)
    maximo = max(0, int((fin - cy) // 26))
    if len(lineas_c) > maximo:
        lineas_c = lineas_c[:maximo]
        if lineas_c:
            lineas_c[-1] = lineas_c[-1].rstrip() + "…"
    for linea in lineas_c:
        d.text((x + pad, cy), linea, font=fc, fill=GRIS)
        cy += 26

    if datos.get("instantanea"):
        d.text((x + pad, y + h - 36), f"Instantánea {datos['instantanea']}", font=_fuente(18), fill=GRIS)


def render(fecha, datos):
    hero_url = (datos.get("wikipedia") or {}).get("hero") or (datos.get("apod") or {}).get("hero")
    urls = [hero_url] + [(datos.get(clave) or {}).get("imagen") for clave, _, _ in TARJETAS]
    with ThreadPoolExecutor(max_workers=8) as pool:
        imgs = list(pool.map(_bajar, urls))
    hero, fotos = imgs[0], dict(zip([c[0] for c in TARJETAS], imgs[1:]))

    img = Image.new("RGB", (W, H), PAPEL)
    _cabecera(img, hero, fecha)

    margen, col_w, gap_col, gap_fila, arriba, alto_card = 40, 540, 40, 24, 430, 350
    for i, (clave, etiqueta, color) in enumerate(TARJETAS):
        col, fila = i % 2, i // 2
        x = margen + col * (col_w + gap_col)
        y = arriba + fila * (alto_card + gap_fila)
        _tarjeta(img, x, y, col_w, alto_card, etiqueta, color, datos.get(clave) or {}, fotos.get(clave))

    d = ImageDraw.Draw(img)
    d.text((60, 1540), "Creado por XatoDev · Xatodev.contacto@gmail.com", font=_fuente(20), fill=GRIS)
    d.text((60, 1568), "internettimecapsule.com", font=_fuente(24, True), fill=VERDE)

    buf = BytesIO()
    img.save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf


def render_apod(datos_apod):
    """Genera una imagen vertical atractiva solo con la foto NASA del día."""
    if not datos_apod or datos_apod.get("error"):
        return None
    url = datos_apod.get("imagen") or datos_apod.get("hero")
    foto = _bajar(url)
    if foto is None:
        return None

    # Lienzo 1080x1350 (formato stories / portrait)
    pw, ph = 1080, 1350
    canvas = Image.new("RGB", (pw, ph), TINTA)
    # Foto ocupando la parte superior
    alto_foto = 900
    canvas.paste(ImageOps.fit(foto, (pw, alto_foto)), (0, 0))

    # Degradado inferior
    velo = Image.new("RGBA", (pw, 280), (0, 0, 0, 0))
    dv = ImageDraw.Draw(velo)
    for y in range(280):
        dv.line([(0, y), (pw, y)], fill=(0, 0, 0, int(20 + 200 * y / 280)))
    zona = canvas.crop((0, alto_foto - 200, pw, alto_foto)).convert("RGBA")
    zona = Image.alpha_composite(zona, velo.crop((0, 0, pw, 200))).convert("RGB")
    canvas.paste(zona, (0, alto_foto - 200))

    d = ImageDraw.Draw(canvas)
    titulo = _limpio(datos_apod.get("titulo", "Astronomy Picture of the Day"))
    lineas = _envolver(titulo, _fuente(36, True), pw - 80)
    cy = alto_foto + 24
    d.text((40, cy), "NASA · FOTO DEL DÍA", font=_fuente(18, True), fill=(120, 180, 255))
    cy += 36
    for linea in lineas[:3]:
        d.text((40, cy), linea, font=_fuente(34, True), fill=(255, 255, 255))
        cy += 42
    cita = _limpio(datos_apod.get("cita", ""))[:220]
    if cita:
        cy += 8
        for linea in _envolver(cita, _fuente(20), pw - 80)[:4]:
            d.text((40, cy), linea, font=_fuente(20), fill=(200, 200, 210))
            cy += 26

    d.text((40, ph - 48), "Internet Time Capsule · XatoDev", font=_fuente(18), fill=GRIS)

    buf = BytesIO()
    canvas.save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf
