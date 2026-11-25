# LCR Hoteles y Apartamentos · web pública

Web estática (ES / EN / FR) generada a partir del contenido actual de lcrhoteles.com (rastreado el 17.11.2026) y del PRD del 17.11.2026.
No se inventa ningún dato: textos, fotos y precios vienen de la web actual y del PRD.

## Estructura
- `public/` web ya generada (HTML, CSS, JS, fuentes e imágenes). Es lo que se sirve.
- `server.py` servidor (solo librería estándar de Python) + formularios `/api/contact` y `/api/club`.
- `tools/build.py` regenera `public/` desde `content/`. `tools/crawl.py` vuelve a leer lcrhoteles.com.
- `content/prices.json` precios «desde» por noche. `content/offers.json` ofertas. `content/config.json` ajustes. Se editan sin tocar código; después `python3 tools/build.py`.
- `Dockerfile` + `railway.json` despliegue en Railway.

## Pendiente de confirmar (no inventado)
1. **URL del motor Mirai**: pon en `content/config.json` → `mirai_url` (admite `{hotel}`, `{room}`, `{lang}`). Mientras esté vacío, «Elegir fechas» lleva al formulario de contacto.
2. **Email de aviso**: variables de Railway `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` (y `NOTIFY_EMAIL`, por defecto reservas@lcrhoteles.com). Sin SMTP, cada consulta se guarda en `data/consultas.jsonl` y no se envía.
3. **reCAPTCHA**: `recaptcha_site_key` en config y `RECAPTCHA_SECRET` en Railway. Sin claves hay campo trampa y límite de envíos.
4. **Los Valles tiene dos direcciones** en la web actual (Av. del Manzano 8-12 en su ficha, Avda. del Manzano 19 en la ficha de apartamentos). Se muestra la de su ficha hasta que se confirme.
5. Precios «desde» sin dato en el PRD (Boutique Vistas, Grande, Balcón y vistas, Suites 1 y 2): no se muestra precio.
6. En la web actual, `/en/activities/` y `/en/contact/` dan redirección en bucle. Aquí `/en/activities/` se muestra con el texto en español (no hay versión EN accesible).
7. SEO y SEO para IA: fuera de esta versión (se definirá punto por punto). Solo hay lo básico: título, descripción, hreflang, canonical, sitemap.

## Local
```
python3 tools/build.py
PORT=8080 python3 server.py
```

## Rediseño (opciones 4–9) — archivos editables
- `content/seo.json`: H1, meta title y meta description de la portada (ES/EN/FR).
- `content/config.json`: `mirai_url` (con `{chain}`, `{checkin}`, `{nights}`, `{parties}`, `{lang}`), `mirai_hotels` (slug → valor de Mirai por hotel, vacío por ahora) y `reviews_links`.
- `content/experiences.json`: «Experiencias top» de la portada.
- `content/reviews.json`: reseñas REALES (vacío = la sección no se muestra). `REVIEWS_DEMO=1` solo para ver el diseño en preview.
- `content/seasons.json`: fechas de cada estación (fotos de Actividades).
- `content/room_photos.json`: foto de cada habitación (solo la Suite de Tierra de Biescas está verificada).
- `public/video/hero.mp4` (+ `hero.webm`): vídeo de fondo de la portada. Sin vídeo se ve la foto.
- `python3 tools/optimize.py` (requiere Pillow): comprime imágenes y crea versiones pequeñas (`public/img/r/`).
- Preview: `THEME=7 PUB_DIR=preview/7 python3 tools/build.py` y `python3 -m http.server 8107` dentro de `preview/7`.
