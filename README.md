# Internet Time Capsule

**Creado por [XatoDev](mailto:Xatodev.contacto@gmail.com)** · `Xatodev.contacto@gmail.com` · v2.1

Muestra cómo estaba internet en cualquier fecha desde 2006. Todas las fuentes son gratuitas y no requieren registro ni clave de API.

## Fuentes

- **Wikipedia** (inglés y español): artículo más leído del día e imagen del día. Desde 2015.
- **Efemérides**: sucesos de ese día (Wikipedia "on this day").
- **En las noticias**: actualidad destacada de Wikipedia.
- **Reddit**: primer post de r/all en Wayback Machine.
- **Hacker News**: historia más votada (API de Algolia). Desde 2006.
- **Stack Overflow**: pregunta más votada (API pública de Stack Exchange).
- **Titulares del mundo**: GDELT. Desde 2015.
- **Portadas de periódicos**: NYT, BBC, The Guardian y El País en Wayback Machine.
- **Terremotos**: catálogo sísmico del USGS.
- **Divisas**: tipos de cambio del Banco Central Europeo (Frankfurter).
- **Álbumes publicados**: MusicBrainz.
- **Estrenos y juegos**: Wikidata (películas y videojuegos).
- **Festivos**: Nager.Date (España, México, Argentina, Colombia, EE. UU., Reino Unido).
- **NASA · Foto del día**: API APOD con DEMO_KEY (sin registro). Desde 1995.
- **Clima**: Open-Meteo, con selector de ciudad. Desde 1940.

Las imágenes pasan por `/img`, un proxy que solo acepta dominios de Wikimedia y NASA.

## Buscador mejorado

En `/buscar` puedes buscar una palabra clave dentro de un día o de un rango de hasta un año, en inglés o en español.

**Fuentes del buscador:** Hacker News, Stack Overflow, GDELT, MusicBrainz, Wikipedia y **efemérides del día** (cuando el rango es un solo día).

Cada resultado con fecha enlaza a su cápsula. Los enlaces son compartibles:

```
/buscar?q=iphone&desde=2007-01-01&hasta=2007-12-31
```

Atajos rápidos en la interfaz: iPhone 2007, Bitcoin 2010–13, COVID 2020, ChatGPT.

## Descargar imágenes

- **Póster de la cápsula** (`/share/YYYY-MM-DD.png?descargar=1`): PNG 1200×1600 con las 6 tarjetas principales, imágenes y créditos de XatoDev.
- **Foto NASA del día** (`/share/YYYY-MM-DD/apod.png?descargar=1`): formato vertical (1080×1350) listo para stories / redes, con título y explicación.

## Instalar (recomendado)

```bash
# Desde el directorio del proyecto
pip install -e .

# Arrancar
internet-time-capsule
# o el alias corto:
itc

# Escuchar en todas las interfaces
HOST=0.0.0.0 PORT=8080 internet-time-capsule
```

También puedes ejecutarlo sin instalar:

```bash
pip install -r requirements.txt
HOST=0.0.0.0 python app.py
```

Opcional: define `NASA_API_KEY` para más cuota en la foto del día.

## Desplegar

- **Render:** Build `pip install -r requirements.txt`, Start `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`.
- **Railway:** detecta el `Procfile`.
- Para conservar la caché entre reinicios, usa un volumen y apunta `ITC_DB` a una ruta dentro de él.

## Autor

**XatoDev**  
Correo: [Xatodev.contacto@gmail.com](mailto:Xatodev.contacto@gmail.com)

Proyecto personal y educativo. Feedback y colaboraciones bienvenidos.
