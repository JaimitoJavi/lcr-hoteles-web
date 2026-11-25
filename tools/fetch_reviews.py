#!/usr/bin/env python3
"""Descarga reseñas de Google (API oficial Places) a content/reviews.json.

Necesita (los pone el propietario, nunca en el código):
  GOOGLE_PLACES_API_KEY   variable de entorno con la clave de Google Cloud (Places API (New) activada)
  content/config.json -> "google_place_ids": {"hotel-tierra-biescas": "ChIJ...", ...}
Google devuelve hasta 5 reseñas por sitio, con nombre y foto de perfil del autor; sus condiciones exigen mostrar
la atribución a Google y no guardar los datos más de 30 días: ejecuta este script en cada despliegue.
Uso:
  GOOGLE_PLACES_API_KEY=... python3 tools/fetch_reviews.py --find   # busca el identificador de cada hotel y lo muestra para confirmarlo
  GOOGLE_PLACES_API_KEY=... python3 tools/fetch_reviews.py          # descarga las reseñas
"""
import json, os, sys, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = json.load(open(os.path.join(ROOT, "content", "config.json")))
key = os.environ.get("GOOGLE_PLACES_API_KEY")
ids = cfg.get("google_place_ids", {})
if "--find" in sys.argv:
    if not key: sys.exit("Falta GOOGLE_PLACES_API_KEY")
    names = {"hotel-tierra-biescas": "Hotel Tierra de Biescas", "hotel-posada-de-ruba": "La Posada de Ruba Biescas", "apartamentos-lcr-boutique": "Apartamentos LCR Boutique Biescas",
             "apartamentos-lcr-suites": "Apartamentos LCR Suites Biescas", "apartamento-lcr-los-valles": "Apartamento LCR Los Valles Biescas"}
    for slug, q in names.items():
        req = urllib.request.Request("https://places.googleapis.com/v1/places:searchText", data=json.dumps({"textQuery": q, "languageCode": "es"}).encode(),
            headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress", "Content-Type": "application/json"})
        for pl in json.load(urllib.request.urlopen(req, timeout=30)).get("places", [])[:3]:
            print(f'{slug}: {pl["id"]}  {pl["displayName"]["text"]} · {pl.get("formattedAddress", "")}')
    sys.exit("Copia el identificador correcto de cada hotel en content/config.json -> google_place_ids")
if not key or not ids: sys.exit("Faltan GOOGLE_PLACES_API_KEY o google_place_ids en content/config.json")
items, rated = [], []
for slug, pid in ids.items():
    req = urllib.request.Request(f"https://places.googleapis.com/v1/places/{pid}?languageCode=es", headers={
        "X-Goog-Api-Key": key, "X-Goog-FieldMask": "rating,userRatingCount,googleMapsUri,reviews"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    if d.get("rating"): rated.append((d["rating"], d.get("userRatingCount", 0)))
    for r in d.get("reviews", []):
        if r.get("rating", 0) < 4: continue          # solo se muestran las positivas
        a = r.get("authorAttribution", {})
        items.append({"source": "google", "author": a.get("displayName", ""), "avatar": a.get("photoUri", ""), "rating": r["rating"],
                      "date": (r.get("publishTime") or "")[:7], "hotel": slug, "text": (r.get("text") or r.get("originalText") or {}).get("text", ""),
                      "url": r.get("googleMapsUri") or d.get("googleMapsUri", "")})
n = sum(c for _, c in rated)
summ = {"google": {"rating": round(sum(r * c for r, c in rated) / n, 1), "count": n}} if n else {}
json.dump({"summary": summ, "items": items}, open(os.path.join(ROOT, "content", "reviews.json"), "w"), ensure_ascii=False, indent=1)
print(f"{len(items)} reseñas guardadas")
