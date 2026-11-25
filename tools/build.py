#!/usr/bin/env python3
"""Genera la web estática de LCR Hoteles y Apartamentos en /public.

Fuente de contenido: content/crawl.json (texto e imágenes de lcrhoteles.com del 17.11.2026).
Datos editables sin tocar código: content/prices.json, content/offers.json, content/config.json.
Uso:  python3 tools/build.py
"""
import json, os, re, html, shutil
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "public")
def _default_theme():
    try: return str(json.load(open(os.path.join(ROOT, "content", "config.json"))).get("theme", ""))
    except Exception: return ""
THEME = os.environ["THEME"] if "THEME" in os.environ else _default_theme()   # THEME="" fuerza el diseño antiguo
LUX = THEME in ("4", "5", "6", "7", "8", "9", "10", "11", "12")   # estructura común "montaña" (theme-lux.css)
VIV = THEME in ("7", "8", "9", "10", "11", "12")
SOFT = THEME in ("10", "11", "12")             # suaves y de lujo (theme-soft.css encima de vivid)                  # variantes claras de colores vivos (theme-vivid.css)            # "1" | "2" | "3" → rediseño; vacío = diseño actual
PUB = os.path.join(ROOT, os.environ["PUB_DIR"]) if os.environ.get("PUB_DIR") else ASSETS
BASE = "https://www.lcrhoteles.com"
LANGS = ["es", "en", "fr"]

def jload(name, default=None):
    p = os.path.join(ROOT, "content", name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default

crawl = jload("crawl.json")
config = jload("config.json", {})
SITE_URL = config.get("site_url", BASE).rstrip("/")
MIRAI = config.get("mirai_url", "")
PHONE_TEL, PHONE_TXT = "+34974485483", "+34 974 485 483"
EMAIL = "reservas@lcrhoteles.com"
WHATSAPP = "https://wa.me/34687003603"

HOTELS = [
    ("hotel-tierra-biescas", "Hotel Tierra de Biescas", "logo_tierra-biescas.webp", "home_tab_corpo-biescas.webp"),
    ("hotel-posada-de-ruba", "La Posada de Ruba", "logo_ruba.webp", "home_tab_corpo-ruba.webp"),
    ("apartamentos-lcr-boutique", "Apartamentos LCR Boutique", "logo_lcr-boutique.webp", "home_tab_corpo-boutique.webp"),
    ("apartamentos-lcr-suites", "Apartamentos LCR Suites", "logo_lcr-suites.webp", "home_tab_corpo-suites.webp"),
    ("apartamento-lcr-los-valles", "Apartamento LCR Los Valles", "logos_los-valles.webp", "home_tab_corpo-valles.webp"),
]
HOTEL_SLUGS = [h[0] for h in HOTELS]
HNAME = {h[0]: h[1] for h in HOTELS}
APT = {"apartamentos-lcr-boutique", "apartamentos-lcr-suites", "apartamento-lcr-los-valles"}

# subpágina ES -> (EN, FR)
SUBS = {
    "habitaciones": ("rooms", "chambres"), "apartamentos": ("rooms", "appartements"),
    "ofertas": ("offers", "offres"), "galeria": ("gallery", "galerie"), "bodas": ("weddings", "mariages"),
    "stages-deportivos": ("sports-camps", "stages-sportifs"), "gastronomia": ("gastronomy", "gastronomie"),
    "eventos-empresa": ("corporate-events", "evenements-entreprise"),
}
TOP = {
    "entorno": ("location", "emplacement"), "actividades": ("activities", "activites"),
    "contacto": ("contact", "contact"), "aviso-legal": ("legal-notice", "mentions-legales"),
    "politica-cookies": ("cookie-policy", "politique-des-cookies"), "signup": ("signup", "signup"),
}
LI = {"es": 0, "en": 0, "fr": 1}

def loc(seg, table, lang):
    if lang == "es": return seg
    return table[seg][0 if lang == "en" else 1]

def url(lang, key):
    """key: ruta ES con / inicial y final (p.ej. /hotel-tierra-biescas/habitaciones/individual/)"""
    parts = [p for p in key.split("/") if p]
    out = []
    for i, p in enumerate(parts):
        if i == 0 and p in TOP: out.append(loc(p, TOP, lang))
        elif i == 1 and p in SUBS: out.append(loc(p, SUBS, lang))
        else: out.append(p)
    pre = "" if lang == "es" else "/" + lang
    return pre + "/" + "/".join(out) + ("/" if out else "")

def HU(lang, h, sub=None, r=None):
    return url(lang, f"/{h}/" + (f"{sub}/" if sub else "") + (f"{r}/" if r else ""))

def parse_path(path):
    lang = "es"
    m = re.match(r"^/(en|fr)(/.*)?$", path)
    if m: lang, path = m.group(1), (m.group(2) or "/")
    parts = [p for p in path.split("/") if p]
    if not parts: return lang, "/"
    if any(p.startswith("detalle-de") or p == "membersarea" for p in parts): return None
    if len(parts) == 1:
        for es, tr in TOP.items():
            if parts[0] == loc(es, TOP, lang): return lang, f"/{es}/"
        if parts[0] in HOTEL_SLUGS: return lang, f"/{parts[0]}/"
    if len(parts) == 2 and parts[0] in HOTEL_SLUGS:
        for es in SUBS:
            if parts[0] in APT and es == "habitaciones": continue
            if parts[0] not in APT and es == "apartamentos": continue
            if parts[1] == loc(es, SUBS, lang): return lang, f"/{parts[0]}/{es}/"
    return None

PAGES = {}   # (lang,key) -> crawl entry
for u, v in crawl.items():
    r = parse_path(u.replace(BASE, ""))
    if r: PAGES[r] = v

def P(lang, key):
    return PAGES.get((lang, key)) or PAGES.get(("es", key))

FIX = {"Apartmentos": "Apartamentos", "Pirinero": "Pirineo", "totalemnte": "totalmente", "Tierra de Biesas": "Tierra de Biescas",
       "Aprovecha nuestros descuentos exclusivos": "Aprovecha nuestros descuentos exclusivos"}
def fix(t):
    for a, b in FIX.items(): t = t.replace(a, b)
    return t
def esc(t): return html.escape(fix(t), quote=True)
def slug(t):
    t = t.lower()
    for a, b in zip("áéíóúüñàèç", "aeiouunaec"): t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")

# ---------------------------------------------------------------- textos de interfaz
UI = {
 "es": dict(skip="Saltar al contenido", home="Inicio", entorno="Entorno", actividades="Actividades", club="Club LCR", contacto="Contacto",
   login="Acceder", menu="Menú", call="Llamar", from_="Desde", per_night="€ por noche", pick="Elegir fechas", rooms="Habitaciones", apts="Apartamentos",
   offers="Ofertas", gallery="Galería", weddings="Bodas", camps="Stages deportivos", gastro="Gastronomía", corp="Eventos de empresa", all_offers="Ver todas las ofertas",
   see="Ver alojamiento", more="Ver más", legal="Aviso legal", cookies="Política de cookies", owner="Titular", follow="Síguenos", back="Volver",
   other_rooms="Otras opciones", price_note="Precio «desde» por noche, dato del", rooms_title="Elige tu descanso", offers_title="Ofertas exclusivas",
   gallery_title="Fotos", benefits="Ventajas de reservar en la web", f_name="Nombre", f_email="Email", f_phone="Teléfono", f_subject="Asunto", f_msg="Mensaje",
   f_priv="He leído y acepto la política de privacidad y el aviso legal.", f_send="Enviar", f_club_ok="Quiero unirme al Club LCR y acepto recibir las ventajas del club en mi email.",
   f_ok="Gracias. Hemos recibido tu mensaje. El equipo de reservas lo revisará y te responderá al email que nos has indicado.",
   f_ok_club="Gracias. Hemos recibido tu solicitud de alta en el Club LCR. El equipo de reservas se pondrá en contacto contigo en el email que nos has indicado.",
   f_err="No hemos podido enviar el formulario. Inténtalo de nuevo o escríbenos a", f_after="Al enviar, el equipo de reservas recibe tu consulta por email y te responde al email que indiques.",
   f_req="Campos obligatorios", club_title="Únete al Club LCR", contact_title="Contacto", contact_lead="Escríbenos y el equipo de reservas te responderá. Para reservar, elige tus fechas en la ficha de cada habitación.",
   address="Dirección", book_direct="Reserva en la web oficial", missing_lang="Esta página no está disponible en este idioma; se muestra en español.",
   wa="WhatsApp", footer_hotels="Alojamientos", footer_info="Información", private_note="Para reservar:", no_price="Consulta el precio al elegir fechas"),
 "en": dict(skip="Skip to content", home="Home", entorno="Location", actividades="Activities", club="LCR Club", contacto="Contact",
   login="Sign in", menu="Menu", call="Call", from_="From", per_night="€ per night", pick="Choose dates", rooms="Rooms", apts="Apartments",
   offers="Offers", gallery="Gallery", weddings="Weddings", camps="Sports camps", gastro="Gastronomy", corp="Corporate events", all_offers="See all offers",
   see="See accommodation", more="See more", legal="Legal notice", cookies="Cookie policy", owner="Owner", follow="Follow us", back="Back",
   other_rooms="Other options", price_note="“From” price per night, data from", rooms_title="Choose your rest", offers_title="Exclusive offers",
   gallery_title="Photos", benefits="Advantages of booking on the web", f_name="Name", f_email="Email", f_phone="Phone", f_subject="Subject", f_msg="Message",
   f_priv="I have read and accept the privacy policy and legal notice.", f_send="Send", f_club_ok="I want to join the LCR Club and agree to receive the club benefits by email.",
   f_ok="Thank you. We have received your message. The reservations team will review it and reply to the email you gave us.",
   f_ok_club="Thank you. We have received your LCR Club sign-up. The reservations team will contact you at the email you gave us.",
   f_err="We could not send the form. Please try again or write to us at", f_after="When you send it, the reservations team receives your enquiry by email and replies to the email you give.",
   f_req="Required fields", club_title="Join the LCR Club", contact_title="Contact", contact_lead="Write to us and the reservations team will reply. To book, choose your dates on each room page.",
   address="Address", book_direct="Book on the official website", missing_lang="This page is not available in this language; it is shown in Spanish.",
   wa="WhatsApp", footer_hotels="Accommodation", footer_info="Information", private_note="To book:", no_price="See the price when you choose dates"),
 "fr": dict(skip="Aller au contenu", home="Accueil", entorno="Emplacement", actividades="Activités", club="Club LCR", contacto="Contact",
   login="Se connecter", menu="Menu", call="Appeler", from_="À partir de", per_night="€ la nuit", pick="Choisir les dates", rooms="Chambres", apts="Appartements",
   offers="Offres", gallery="Galerie", weddings="Mariages", camps="Stages sportifs", gastro="Gastronomie", corp="Événements d’entreprise", all_offers="Voir toutes les offres",
   see="Voir l’hébergement", more="En savoir plus", legal="Mentions légales", cookies="Politique des cookies", owner="Titulaire", follow="Suivez-nous", back="Retour",
   other_rooms="Autres options", price_note="Prix « à partir de » par nuit, donnée du", rooms_title="Choisissez votre séjour", offers_title="Offres exclusives",
   gallery_title="Photos", benefits="Avantages de réserver sur le site", f_name="Nom", f_email="E-mail", f_phone="Téléphone", f_subject="Objet", f_msg="Message",
   f_priv="J’ai lu et j’accepte la politique de confidentialité et les mentions légales.", f_send="Envoyer", f_club_ok="Je souhaite rejoindre le Club LCR et j’accepte de recevoir les avantages du club par e-mail.",
   f_ok="Merci. Nous avons bien reçu votre message. L’équipe des réservations le lira et vous répondra à l’adresse e-mail indiquée.",
   f_ok_club="Merci. Nous avons bien reçu votre inscription au Club LCR. L’équipe des réservations vous contactera à l’adresse e-mail indiquée.",
   f_err="Impossible d’envoyer le formulaire. Réessayez ou écrivez-nous à", f_after="À l’envoi, l’équipe des réservations reçoit votre demande par e-mail et vous répond à l’adresse indiquée.",
   f_req="Champs obligatoires", club_title="Rejoignez le Club LCR", contact_title="Contact", contact_lead="Écrivez-nous et l’équipe des réservations vous répondra. Pour réserver, choisissez vos dates sur la fiche de chaque chambre.",
   address="Adresse", book_direct="Réservez sur le site officiel", missing_lang="Cette page n’est pas disponible dans cette langue ; elle s’affiche en espagnol.",
   wa="WhatsApp", footer_hotels="Hébergements", footer_info="Informations", private_note="Pour réserver :", no_price="Voir le prix en choisissant les dates"),
}
SUBLABEL = {"habitaciones": "rooms", "apartamentos": "apts", "ofertas": "offers", "galeria": "gallery", "bodas": "weddings",
            "stages-deportivos": "camps", "gastronomia": "gastro", "eventos-empresa": "corp"}

# ---------------------------------------------------------------- datos editables
PRICES = jload("prices.json")
if PRICES is None:
    PRICES = {"updated": "2026-11-17", "currency": "EUR", "from_per_night": {
        "hotel-tierra-biescas": {"individual": 54, "estandar": 91, "premium": 98, "junior-suite": 122, "familiar": 122, "suite": 157},
        "hotel-posada-de-ruba": {"doble-compacta": 64, "doble": 67, "doble-confort": 91, "familiar": 67},
        "apartamentos-lcr-boutique": {"boutique-estandar": 69},
        "apartamentos-lcr-suites": {"suites-3": 122, "suites-4": 122},
        "apartamento-lcr-los-valles": {"apartamento-los-valles": 122}}}
    json.dump(PRICES, open(os.path.join(ROOT, "content/prices.json"), "w"), ensure_ascii=False, indent=2)

def pairs(items):
    out, cur = [], None
    for t, x in items:
        if t == "h3": cur = {"title": x, "desc": ""}; out.append(cur)
        elif t == "p" and cur and not cur["desc"]: cur["desc"] = x
    return out

def offers_from_crawl(h):
    res = {}
    for lang in LANGS:
        pg = PAGES.get((lang, f"/{h}/ofertas/"))
        if not pg: continue
        body = []; seen = False
        for t, x in pg["items"]:
            if t == "h2" and x.lower().startswith(("ofertas", "offers", "offres")): seen = True; continue
            if seen: body.append((t, x))
        res[lang] = pairs(body)
    n = len(res.get("es", []))
    if not n: return []
    return [{l: res[l][i] for l in LANGS if l in res and len(res[l]) == n} for i in range(n)]

OFFERS = jload("offers.json")
if OFFERS is None:
    OFFERS = {h: offers_from_crawl(h) for h in HOTEL_SLUGS}
    json.dump(OFFERS, open(os.path.join(ROOT, "content/offers.json"), "w"), ensure_ascii=False, indent=2)

# ---------------------------------------------------------------- habitaciones
def parse_rooms(items):
    common, rooms, cur = [], [], None
    for t, x in items:
        if t == "h3": cur = {"name": x, "desc": "", "feats": []}; rooms.append(cur)
        elif t == "p" and cur is not None and not cur["desc"]: cur["desc"] = x
        elif t == "li":
            if cur is None: common.append(x)
            elif x not in cur["feats"]: cur["feats"].append(x)
    return common, rooms

ROOMS = OrderedDict()   # (hotel) -> list of {slug, i18n{lang:{name,desc,feats}}}
def build_room_data():
    # tierra y posada
    for h in ["hotel-tierra-biescas", "hotel-posada-de-ruba"]:
        langs = {l: parse_rooms(PAGES[(l, f"/{h}/habitaciones/")]["items"]) for l in LANGS if (l, f"/{h}/habitaciones/") in PAGES}
        es_common, es_rooms = langs["es"]
        lst = []
        for i, r in enumerate(es_rooms):
            d = {l: (langs[l][1][i] if l in langs and len(langs[l][1]) == len(es_rooms) else r) for l in LANGS}
            lst.append({"slug": slug(r["name"]), "i18n": d, "common": {l: (langs[l][0] if l in langs else es_common) for l in LANGS}})
        ROOMS[h] = lst
    # apartamentos (la ficha de Boutique lista los 9)
    langs = {l: parse_rooms(PAGES[(l, "/apartamentos-lcr-boutique/apartamentos/")]["items"]) for l in LANGS if (l, "/apartamentos-lcr-boutique/apartamentos/") in PAGES}
    es_common, es_rooms = langs["es"]
    for h in APT: ROOMS[h] = []
    for i, r in enumerate(es_rooms):
        n = r["name"].lower()
        owner = "apartamentos-lcr-suites" if n.startswith("suites") else "apartamento-lcr-los-valles" if "valles" in n else "apartamentos-lcr-boutique"
        d = {l: (langs[l][1][i] if l in langs and len(langs[l][1]) == len(es_rooms) else r) for l in LANGS}
        ROOMS[owner].append({"slug": slug(r["name"]), "i18n": d, "common": {l: (langs[l][0] if l in langs else es_common) for l in LANGS}})
build_room_data()

def price_of(h, slug_):
    return PRICES["from_per_night"].get(h, {}).get(slug_)

import datetime, base64, urllib.parse
def _parties(n=2):
    return urllib.parse.quote(base64.b64encode(json.dumps([{"adults": n, "children": []}], separators=(",", ":")).encode()).decode(), safe="")

def mirai_link(lang, h, room=None):
    if MIRAI:
        ci = (datetime.date.today() + datetime.timedelta(days=7)).strftime("%d/%m/%Y").replace("/", "%2F")
        return (MIRAI.replace("{hotel}", h).replace("{room}", room or "").replace("{lang}", lang)
                .replace("{checkin}", ci).replace("{nights}", "2").replace("{parties}", _parties(2))
                .replace("{chain}", str(config.get("mirai_hotels", {}).get(h) or config.get("mirai_chain_default", "66013"))))
    return url(lang, "/contacto/") + (f"?alojamiento={h}" + (f"&habitacion={room}" if room else ""))

# ---------------------------------------------------------------- fotos de habitación
RP_KEY = {"hotel-tierra-biescas": "biescas", "hotel-posada-de-ruba": "ruba", "apartamentos-lcr-boutique": "boutique",
          "apartamentos-lcr-suites": "suites", "apartamento-lcr-los-valles": "valles"}
ROOM_PHOTOS = jload("room_photos.json", {})
def room_pool(h):
    k = RP_KEY.get(h, "")
    d = os.path.join(ASSETS, "img")
    return sorted(f for f in os.listdir(d) if f.startswith(f"home-{k}_rooms-")) if k else []
def room_photo(h, slug_, idx=0):
    ov = ROOM_PHOTOS.get(h, {}).get(slug_)
    if ov: return ov[0]
    fixed = {v[0] for v in ROOM_PHOTOS.get(h, {}).values() if isinstance(v, list)}
    pool = [f for f in room_pool(h) if f not in fixed] or room_pool(h)
    return pool[idx % len(pool)] if pool else None

# ---------------------------------------------------------------- imágenes
def bn(src): return src.split("/")[-1]
def is_logo(n): return n.startswith("logo") or n.startswith("map-") or n.startswith("tpl_instagram")
def page_images(pg, skip=()):
    seen, out = set(), []
    for i in pg["imgs"]:
        n = bn(i["src"])
        if is_logo(n) or n in seen or n in skip or n.startswith("home_tab_corpo"): continue
        seen.add(n); out.append((n, i["alt"]))
    return out
LOGO_ALT = {}
for v in crawl.values():
    for i in v["imgs"]: LOGO_ALT.setdefault(bn(i["src"]), i["alt"])
IMG_SIZES = jload("img_sizes.json", {})
def img(n, alt=None, cls="", lazy=True, w=None, h=None, sizes=None):
    a = alt if alt is not None else LOGO_ALT.get(n, "")
    a = a.strip('"')
    info = IMG_SIZES.get(n)
    if info and not w: w, h = info["w"], info["h"]
    sz = f' width="{w}" height="{h}"' if w else ""
    ss = ""
    if info and info["v"]:
        stem = n[:-5]
        cand = [f"/img/r/{stem}-w{v}.webp {v}w" for v in info["v"]] + [f"/img/{n} {info['w']}w"]
        ss = f' srcset="{", ".join(cand)}" sizes="{sizes or ("100vw" if not lazy else "(max-width: 760px) 100vw, 50vw")}"'
    return f'<img src="/img/{n}" alt="{esc(a)}"{sz}{ss}{" loading=lazy" if lazy else ""}{" class=" + cls if cls else ""} decoding="async">'

# ---------------------------------------------------------------- estaciones
SEASONS = jload("seasons.json", {})
SORDER = SEASONS.get("order", ["winter", "autumn", "summer", "spring"])
SNAME = {"es": {"winter": "Invierno", "spring": "Primavera", "summer": "Verano", "autumn": "Otoño"},
         "en": {"winter": "Winter", "spring": "Spring", "summer": "Summer", "autumn": "Autumn"},
         "fr": {"winter": "Hiver", "spring": "Printemps", "summer": "Été", "autumn": "Automne"}}
SUI = {"es": {"title": "Pirineo 4 estaciones", "for": "Fotos para tu estancia en", "prev": "Estación anterior", "next": "Estación siguiente", "tabs": "Estación del año"},
       "en": {"title": "Pyrenees, 4 seasons", "for": "Photos for your stay in", "prev": "Previous season", "next": "Next season", "tabs": "Season"},
       "fr": {"title": "Pyrénées 4 saisons", "for": "Photos pour votre séjour en", "prev": "Saison précédente", "next": "Saison suivante", "tabs": "Saison"}}
def season_of(m, d):
    for k, (a, b) in SEASONS.get("windows", {}).items():
        if (a[0], a[1]) <= (b[0], b[1]):
            if (a[0], a[1]) <= (m, d) <= (b[0], b[1]): return k
        elif (m, d) >= (a[0], a[1]) or (m, d) <= (b[0], b[1]): return k
    return "winter"
def default_season():
    t = datetime.date.today() + datetime.timedelta(days=SEASONS.get("default_offset_days", 30))
    return season_of(t.month, t.day)
def season_json():
    data = {"windows": SEASONS.get("windows"), "offset": SEASONS.get("default_offset_days", 30), "names": SNAME, "ui": SUI, "order": SORDER}
    return f'<script type="application/json" id="seasons-data">{json.dumps(data, ensure_ascii=False)}</script>'
SEASON_IMGS = set()
def season_activities(lang):
    """{estación: [(imagen, texto)]} emparejando por orden las fotos y los textos de «Pirineo 4 estaciones»."""
    out = {}
    for l in (lang, "es"):
        pg = PAGES.get((l, "/actividades/")) or crawl.get("https://www.lcrhoteles.com/actividades/")
        if not pg: continue
        its = pg["items"]
        k = next((i for i, (t, x) in enumerate(its) if t == "h3" and re.search(r"4 estaciones|4 seasons|4 saisons", x, re.I)), None)
        if k is None: continue
        ps = []
        for t, x in its[k + 1:]:
            if t in ("h2", "h3"): break
            if t == "p": ps.append(x)
        labels = ps[1:37]
        if len(labels) != 36: continue
        names = [bn(i["src"]) for i in pg["imgs"]]
        for n, sn in enumerate(SORDER):
            fs = [x for x in names if x.startswith(f"actividades_{sn}-")]
            out[sn] = list(zip(fs, labels[n * 9:(n + 1) * 9]))
        intro = ps[0] if ps else ""
        return out, intro
    return {}, ""
for _sn in SORDER:
    for _f in os.listdir(os.path.join(ASSETS, "img")):
        if _f.startswith(f"actividades_{_sn}-") or _f.startswith("home_season-") or _f.startswith("home_destination-"): SEASON_IMGS.add(_f)

def seasonal_bg(lang):
    ds = default_season(); hs = SEASONS.get("hero", {})
    tags = "".join((f'<img data-s-img="{sn}" src="/img/{hs[sn]}" alt="{esc(LOGO_ALT.get(hs[sn], ""))}" class="on" decoding="async">' if sn == ds else
                    f'<img data-s-img="{sn}" data-src="/img/{hs[sn]}" alt="{esc(LOGO_ALT.get(hs[sn], ""))}" decoding="async">') for sn in SORDER if sn in hs)
    return f'<div class="hero-img seasonal">{tags}</div>'

def season_tabs(lang, cls="s-tabs"):
    ds = default_season(); n = SNAME[lang]
    b = "".join(f'<button type="button" role="tab" data-s="{sn}" aria-selected="{"true" if sn == ds else "false"}">{n[sn]}</button>' for sn in sorted(SORDER, key=lambda x: ["winter", "spring", "summer", "autumn"].index(x)))
    u = SUI[lang]
    return (f'<div class="{cls}"><button type="button" class="s-arrow" data-dir="-1" aria-label="{u["prev"]}">‹</button>'
            f'<div class="s-list" role="tablist" aria-label="{u["tabs"]}">{b}</div><button type="button" class="s-arrow" data-dir="1" aria-label="{u["next"]}">›</button></div>')

def season_picker(lang):
    u = SUI[lang]
    return f'<div class="seasonbar glass"><span class="sdetect" aria-live="polite">{u["for"]} <b></b></span>{season_tabs(lang, "s-tabs mini")}</div>'

def season_block(lang):
    acts, _ = season_activities(lang)
    if not acts: return ""
    ds = default_season(); panels = []
    for sn in SORDER:
        cards = "".join(f'<article class="card act"><a class="thumb" aria-hidden="true" tabindex="-1">{img(f, t)}</a><h3>{esc(t)}</h3></article>' for f, t in acts.get(sn, []))
        panels.append(f'<div class="s-panel" role="tabpanel" data-s="{sn}"{"" if sn == ds else " hidden"}><div class="cards snap acts">{cards}</div></div>')
    return f'<div class="seasons" data-seasons>{season_tabs(lang)}{"".join(panels)}</div>'

# ---------------------------------------------------------------- piezas HTML
def addr_of(h, lang):
    pg = P(lang, f"/{h}/")
    its = pg["items"] if pg else []
    for k, (t, x) in enumerate(its):
        if t == "h2" and re.search(r"localizaci|location|emplacement", x, re.I):
            hs = [y for tt, y in its[k + 1:k + 6] if tt == "h3"]
            if len(hs) >= 2: return hs[1]
    return ""

def nav_html(lang, cur_key):
    u = UI[lang]
    items = [(f"/{h}/", HNAME[h]) for h in HOTEL_SLUGS] + [("/entorno/", u["entorno"]), ("/actividades/", u["actividades"]), ("/signup/", u["club"]), ("/contacto/", u["contacto"])]
    li = []
    if THEME:   # rediseño: los 5 alojamientos van en un desplegable
        sub = []
        for key, label in items[:len(HOTEL_SLUGS)]:
            active = ' aria-current="page"' if cur_key and cur_key.startswith(key) else ""
            sub.append(f'<li><a href="{url(lang, key)}"{active}>{esc(label)}</a></li>')
        on = " on" if cur_key and any(cur_key.startswith(k) for k, _ in items[:len(HOTEL_SLUGS)]) else ""
        li.append(f'<li class="has-sub{on}"><button type="button" aria-expanded="false" aria-haspopup="true">{esc(u["footer_hotels"])}</button><ul class="sub glass">{"".join(sub)}</ul></li>')
        items = items[len(HOTEL_SLUGS):]
    for key, label in items:
        active = ' aria-current="page"' if cur_key and (cur_key == key or cur_key.startswith(key) and key.count("/") == 2 and key != "/") else ""
        li.append(f'<li><a href="{url(lang, key)}"{active}>{esc(label)}</a></li>')
    return "<ul>" + "".join(li) + "</ul>"

def lang_switch(lang, key, avail):
    out = []
    for l in LANGS:
        if l == lang: out.append(f'<a href="{url(l, key)}" lang="{l}" aria-current="true" class="on">{l.upper()}</a>')
        else: out.append(f'<a href="{url(l, key)}" lang="{l}" hreflang="{l}">{l.upper()}</a>')
    return '<div class="langs" role="group" aria-label="Idioma / Language / Langue">' + "".join(out) + "</div>"

def header(lang, key, avail):
    u = UI[lang]
    return f'''<a class="skip" href="#main">{u['skip']}</a>
<header class="top"><div class="wrap bar">
<a class="logo" href="{url(lang, "/")}">{img("logo_lcr-condensed.webp", "LCR Hoteles y Apartamentos", lazy=False)}</a>
<button class="burger" aria-expanded="false" aria-controls="nav"><span class="sr">{u["menu"]}</span><i></i></button>
<nav id="nav" aria-label="{u["menu"]}">{nav_html(lang, key)}</nav>
<div class="tools">{lang_switch(lang, key, avail)}<a class="login" href="{url(lang, "/signup/")}">{u["login"]}</a>
<a class="tel" href="tel:{PHONE_TEL}" aria-label="{u["call"]} {PHONE_TXT}">{PHONE_TXT}</a></div>
</div></header>'''

FUND = ["logo_next-generation-eu.webp", "logo-espana-transformacion-digital.webp", "logo-recuperacion-transformacion-resiliencia.webp",
        "logo-aragon.webp", "logo-ecologia-demografico.webp", "logo-idae.webp"]
def footer(lang):
    u = UI[lang]
    hot = "".join(f'<li><a href="{HU(lang, h)}">{esc(HNAME[h])}</a><br><span>{esc(addr_of(h, lang) or addr_of(h, "es"))}</span></li>' for h in HOTEL_SLUGS)
    fund = "".join(img(n, w=None) for n in FUND if os.path.exists(os.path.join(PUB, "img", n)))
    return f'''<footer class="foot"><div class="wrap cols">
<div><h2>LCR Hoteles y Apartamentos</h2><p>{u["owner"]}: ALTOTUR, S.L.</p>
<p><a href="tel:{PHONE_TEL}">{PHONE_TXT}</a><br><a href="{WHATSAPP}">{u["wa"]} 687 003 603</a><br><a href="mailto:{EMAIL}">{EMAIL}</a></p></div>
<div><h2>{u["footer_hotels"]}</h2><ul class="addr">{hot}</ul></div>
<div><h2>{u["footer_info"]}</h2><ul><li><a href="{url(lang, "/entorno/")}">{u["entorno"]}</a></li><li><a href="{url(lang, "/actividades/")}">{u["actividades"]}</a></li>
<li><a href="{url(lang, "/signup/")}">{u["club"]}</a></li><li><a href="{url(lang, "/contacto/")}">{u["contacto"]}</a></li>
<li><a href="{url(lang, "/aviso-legal/")}">{u["legal"]}</a></li><li><a href="{url(lang, "/politica-cookies/")}">{u["cookies"]}</a></li>
<li><a href="https://www.instagram.com/pirineohuesca/" rel="noopener">Instagram @pirineohuesca</a></li></ul></div>
</div><div class="wrap fund">{fund}</div></footer>'''

def page_shell(lang, key, title, desc, body, avail, extra_head=""):
    alts = "".join(f'<link rel="alternate" hreflang="{l}" href="{SITE_URL}{url(l, key)}">' for l in avail)
    xdef = f'<link rel="alternate" hreflang="x-default" href="{SITE_URL}{url("es", key)}">' if "es" in avail else ""
    theme_head = f'<link rel="stylesheet" href="/fonts/theme-fonts.css"><link rel="stylesheet" href="/css/fx.css">{"<link rel=stylesheet href=/css/theme-lux.css>" if LUX else ""}{"<link rel=stylesheet href=/css/theme-vivid.css>" if VIV else ""}{"<link rel=stylesheet href=/css/theme-soft.css>" if SOFT else ""}<link rel="stylesheet" href="/css/theme-{THEME}.css">' if THEME else ""
    theme_body = f' class="t{THEME}{" lux has-dock" if LUX else ""}{" vivid" if VIV else ""}{" soft" if SOFT else ""}"' if THEME else ""
    hk = next((h for h in HOTEL_SLUGS if key.startswith(f"/{h}/")), None)
    dock = booking_dock(lang, hk) if LUX else ""
    return f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE_URL}{url(lang, key)}">{alts}{xdef}
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:type" content="website">
<link rel="icon" href="/img/logo_lcr-condensed.webp"><link rel="stylesheet" href="/fonts/fonts.css"><link rel="stylesheet" href="/css/site.css">{theme_head}{extra_head}
</head><body{theme_body}>
{header(lang, key, avail)}
<main id="main">{body}</main>
{footer(lang)}
{dock}
<script src="/js/site.js" defer></script>{season_json() if LUX else ""}{"<script src=/js/fx.js defer></script>" if THEME else ""}</body></html>'''

BB = {"es": ("Entrada", "Noches", "Adultos"), "en": ("Check-in", "Nights", "Adults"), "fr": ("Arrivée", "Nuits", "Adultes")}
def booking_bar(lang):
    u = UI[lang]
    if MIRAI and "{checkin}" in MIRAI:
        a, b, c = BB[lang]
        tpl = MIRAI.replace("{lang}", lang)
        ns = "".join(f'<option value="{n}"{" selected" if n == 2 else ""}>{n}</option>' for n in range(1, 15))
        ad = "".join(f'<option value="{n}"{" selected" if n == 2 else ""}>{n}</option>' for n in range(1, 11))
        return (f'<form class="bookbar glass" method="get" action="{mirai_link(lang, "")}" data-tpl="{esc(tpl)}">'
                f'<label><span>{a}</span><input type="date" name="checkin" required></label>'
                f'<label class="s"><span>{b}</span><select name="nights">{ns}</select></label>'
                f'<label class="s"><span>{c}</span><select name="adults">{ad}</select></label>'
                f'<button class="btn" type="submit">{u["pick"]}</button></form>')
    opts = "".join(f'<option value="{h}" data-url="{mirai_link(lang, h)}">{esc(HNAME[h])}</option>' for h in HOTEL_SLUGS)
    return (f'<form class="bookbar glass" method="get" action="{url(lang, "/contacto/")}"><label><span>{u["footer_hotels"]}</span>'
            f'<select name="alojamiento" aria-label="{u["footer_hotels"]}">{opts}</select></label>'
            f'<button class="btn" type="submit">{u["pick"]}</button></form>')

STATS = {"es": ("alojamientos", "tipos de habitación y apartamento", "desde", "/ noche"), "en": ("properties", "room and apartment types", "from", "/ night"),
         "fr": ("hébergements", "types de chambres et appartements", "à partir de", "/ nuit")}
def hero_stats(lang):
    n_rooms = sum(len(v) for v in ROOMS.values())
    prices = [p for d in PRICES["from_per_night"].values() for p in d.values() if p]
    a, b, c, d = STATS[lang]
    return (f'<ul class="stats glass"><li><b>{len(HOTEL_SLUGS)}</b><span>{a}</span></li><li><b>{n_rooms}</b><span>{b}</span></li>'
            f'<li><b>{c} {min(prices)} €</b><span>{d}</span></li></ul>' if prices else "")

def hero(lang, h1, eyebrow, lead, image, cta=None, cls=""):
    c = f'<a class="btn" href="{cta[1]}">{esc(cta[0])}</a>' if cta else ""
    seasonal = bool(image and image[0] == "__season__" and LUX and SEASONS)
    video = bool(image and image[0] == "__video__" and LUX)
    plain_img = bool(image and not image[0].startswith("__"))
    bg = (seasonal_bg(lang) if seasonal else hero_video_bg(lang) if video else f'<div class="hero-img">{img(image[0], image[1], lazy=False)}</div>' if plain_img else "")
    bar = ((hero_stats(lang) if LUX else booking_bar(lang))) if (THEME and "home" in cls) else ""
    if seasonal: bar += season_picker(lang)
    tick = activity_ticker(lang) if video else ""
    return f'<section class="hero {cls}">{bg}<div class="wrap hero-in">{f"<p class=eyebrow>{esc(eyebrow)}</p>" if eyebrow else ""}<h1>{esc(h1)}</h1>{f"<p class=lead>{esc(lead)}</p>" if lead else ""}{c}{bar}</div>{tick}</section>'

def benefits_strip(items):
    seen = []
    for t, x in items:
        if t == "h3" and x not in seen: seen.append(x)
    return '<div class="benefits"><ul class="wrap">' + "".join(f"<li>{esc(x)}</li>" for x in seen) + "</ul></div>" if seen else ""

def group_sections(body):
    secs = []; cur = {"title": None, "paras": [], "chips": [], "cards": [], "subs": []}; card = None
    def push():
        nonlocal cur
        if cur["title"] or cur["paras"] or cur["chips"] or cur["cards"]: secs.append(cur)
    for t, x in body:
        if t == "h2":
            push(); cur = {"title": x, "paras": [], "chips": [], "cards": [], "subs": []}; card = None
        elif t == "h3":
            card = {"title": x, "ps": [], "lis": []}
            if not any(c["title"] == x and not c["ps"] for c in cur["cards"]): cur["cards"].append(card)
        elif t == "h4": cur["subs"].append(x)
        elif t == "p":
            if card is not None:
                if x not in card["ps"]: card["ps"].append(x)
            elif x not in cur["paras"]: cur["paras"].append(x)
        elif t == "li":
            tgt = card["lis"] if card is not None else cur["chips"]
            if x not in tgt: tgt.append(x)
    push()
    # deduplicar tarjetas idénticas (carruseles repetidos)
    for s in secs:
        seen, uniq = set(), []
        for c in s["cards"]:
            k = (c["title"], tuple(c["ps"]), tuple(c["lis"]))
            if k not in seen: seen.add(k); uniq.append(c)
        s["cards"] = uniq
    return secs

_FLIP = [0]
def light(sec):
    n = len(sec["cards"]) + len(sec["chips"]) + len(sec["subs"]) + sum(len(c["lis"]) + len(c["ps"]) for c in sec["cards"])
    chars = sum(len(p) for p in sec["paras"]) + sum(len(p) for c in sec["cards"] for p in c["ps"])
    return n <= 5 and chars <= 900 and bool(sec["paras"] or sec["cards"])

class Pool:
    """Fotos de la propia página para rellenar secciones con poco contenido (sin huecos)."""
    KEYS = [(r"gastron|restaur|dining|cuisine|desayun|breakfast", "gastronomia"), (r"spa|wellness|bienestar", "spa"),
            (r"evento|boda|event|mariage|stage", "events"), (r"habitaci|room|chambre|apartament", "rooms")]
    def __init__(self, pg, skip=(), strict=False):
        self.l = [n for n, _ in page_images(pg, skip)] if pg else []
        self.used = set(skip); self.strict = strict
    def take(self, sec):
        if not LUX or not self.l or not light(sec): return None
        t = (sec.get("title") or "").lower()
        key = next((k for rx, k in self.KEYS if re.search(rx, t)), None)
        pick = next((n for n in self.l if key and f"_{key}-" in n), None)
        if pick is None and key is None:
            pick = next((n for n in self.l if "_intro-" in n), None) or (None if self.strict else self.l[0])
        if pick is None: return None
        self.l.remove(pick); self.used.add(pick); return pick

def render_section(s, extra="", skip_title=False, side=None):
    if LUX and s["title"] and not (s["paras"] or s["chips"] or s["cards"] or s["subs"] or extra):
        badge = img("actividades_biosfera.webp") if re.search(r"biosfera|biosphere", s["title"], re.I) else ""
        return f'<section class="sec tight"><div class="wrap strip">{badge}<h2 id="{slug(s["title"])}">{esc(s["title"])}</h2></div></section>'
    out = [f'<section class="sec"><div class="wrap{" wideblock" if "data-seasons" in extra else ""}">']
    if s["title"] and not skip_title: out.append(f'<h2 id="{slug(s["title"])}">{esc(s["title"])}</h2>')
    if side:
        _FLIP[0] += 1
        out.append(f'<div class="split{" flip" if _FLIP[0] % 2 else ""}"><div class="txt">')
    short = s["paras"] and len(s["paras"]) >= 2 and all(len(p) < 50 for p in s["paras"][:-1])
    if short:
        out.append('<ul class="chips">' + "".join(f"<li>{esc(p)}</li>" for p in s["paras"] if len(p) < 50) + "</ul>")
        paras = [p for p in s["paras"] if len(p) >= 50]
    else: paras = s["paras"]
    out.extend(f"<p>{esc(p)}</p>" for p in paras)
    if s["chips"]: out.append('<ul class="chips">' + "".join(f"<li>{esc(c)}</li>" for c in s["chips"]) + "</ul>")
    labels = [c for c in s["cards"] if not c["ps"] and not c["lis"]]
    real = [c for c in s["cards"] if c["ps"] or c["lis"]]
    if labels and not real:
        out.append('<ul class="chips">' + "".join(f'<li>{esc(c["title"])}</li>' for c in labels) + "</ul>")
    elif labels:
        out.extend(f'<p class="eyebrow">{esc(c["title"])}</p>' for c in labels[:1])
        real = real + [dict(c) for c in labels[1:]]
    if real:
        out.append('<div class="cards">' + "".join(
            f'<article class="card"><h3>{esc(c["title"])}</h3>' + "".join(f"<p>{esc(p)}</p>" for p in c["ps"]) +
            ('<ul class="chips sm">' + "".join(f"<li>{esc(l)}</li>" for l in c["lis"]) + "</ul>" if c["lis"] else "") + "</article>" for c in real) + "</div>")
    if s["subs"]: out.append('<ul class="chips">' + "".join(f"<li>{esc(x)}</li>" for x in s["subs"]) + "</ul>")
    out.append(extra)
    if side: out.append(f'</div><figure class="side">{img(side)}</figure></div>')
    out.append("</div></section>")
    return "".join(out)

def split_page(items):
    pre, body, h1 = [], [], None
    for t, x in items:
        if h1 is None:
            if t == "h1": h1 = x
            else: pre.append((t, x))
        else: body.append((t, x))
    if h1 is not None and not (pre and pre[0][0] == "h2" and re.search(r"ventaj|advantag|avantag|benefit", pre[0][1], re.I)):
        body = pre + body; pre = []
    if h1 is None: body, pre = pre, []
    return pre, h1, body

def gallery_html(lang, pg, skip=()):
    ims = page_images(pg, skip)[:12]
    if not ims: return ""
    return f'<section class="sec alt"><div class="wrap"><h2>{UI[lang]["gallery_title"]}</h2><div class="gal">' + "".join(
        f'<figure>{img(n, a)}</figure>' for n, a in ims) + "</div></div></section>"

def room_cards(lang, h, only=None):
    rs = ROOMS.get(h, [])
    sub = "apartamentos" if h in APT else "habitaciones"
    cards = []
    for ix, r in enumerate(rs):
        d = r["i18n"][lang]
        p = price_of(h, r["slug"])
        ph = room_photo(h, r["slug"], ix) if LUX else None
        thumb = ""
        if ph:
            pool = room_pool(h) + [x for x in hotel_photos(h, 12) if x not in room_pool(h)]
            thumb = mini(lang, [ph] + [x for x in pool if x != ph][:3], HU(lang, h, sub, r["slug"]))
        pr = f'<p class="price">{UI[lang]["from_"]} <b>{p}</b> {UI[lang]["per_night"]}</p>' if p else ""
        cards.append(f'<article class="card room{" withimg" if thumb else ""}">{thumb}<h3><a href="{HU(lang, h, sub, r["slug"])}">{esc(d["name"])}</a></h3>'
                     f'<p>{esc(d["desc"][:170].rsplit(" ", 1)[0] + "…" if len(d["desc"]) > 170 else d["desc"])}</p>{pr}'
                     f'<p class="row"><a class="btn sm" href="{mirai_link(lang, h, r["slug"])}">{UI[lang]["pick"]}</a> '
                     f'<a class="link" href="{HU(lang, h, sub, r["slug"])}">{UI[lang]["more"]}</a></p></article>')
    return '<div class="cards">' + "".join(cards) + "</div>"

def offers_html(lang, h):
    of = OFFERS.get(h, [])
    cards = []
    for o in of:
        d = o.get(lang) or o.get("es")
        cards.append(f'<article class="card offer"><h3>{esc(d["title"])}</h3><p class="pct">{esc(d["desc"])}</p></article>')
    return '<div class="cards">' + "".join(cards) + "</div>" if cards else ""

def sub_nav(lang, h, cur):
    u = UI[lang]
    links = [(f"/{h}/", u["home"])]
    for es in SUBS:
        if (("es", f"/{h}/{es}/") in PAGES) and (("es", f"/{h}/{es}/") in PAGES): links.append((f"/{h}/{es}/", u[SUBLABEL[es]]))
    return '<nav class="subnav" aria-label="' + esc(HNAME[h]) + '"><ul class="wrap">' + "".join(
        f'<li><a href="{url(lang, k)}"{" aria-current=page" if k == cur else ""}>{esc(l)}</a></li>' for k, l in links) + "</ul></nav>"

def avail_langs(key):
    return LANGS   # todas las páginas se generan en los tres idiomas (con texto ES si falta traducción)

def write(lang, key, content):
    path = url(lang, key)
    d = os.path.join(PUB, path.strip("/"))
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(content)
    GENERATED.append((lang, key))
GENERATED = []

def title_of(pg, fallback):
    t = fix(pg["title"]) if pg else fallback
    t = re.sub(r"\s*[-|]\s*(Web Oficial|Official Website|Site Officiel)\s*$", "", t)
    t = t.replace("LCR Hoteles & Apartamentos", "LCR Hoteles y Apartamentos")
    return t if "LCR Hoteles" in t else t + " | LCR Hoteles y Apartamentos"

# ---------------------------------------------------------------- v3: SEO, reserva fija, vídeo, carruseles, experiencias, reseñas, club, localización
SEO = jload("seo.json", {})
EXPER = jload("experiences.json", {"items": []})
REVIEWS = jload("reviews.json", {"summary": {}, "items": []})
U3 = {
 "es": {"stays": "Nuestros alojamientos en Biescas", "exp": "Experiencias top en el Pirineo", "exp_lead": "Esquí, tirolinas, las fiestas de Biescas, rutas y mucho más: el Pirineo se vive todo el año.",
        "exp_all": "Ver todas las actividades", "rev": "Lo que dicen nuestros huéspedes", "rev_lead": "Opiniones de quienes ya se han alojado con nosotros.",
        "rev_demo": "MUESTRA DE DISEÑO · no son reseñas reales", "rev_all": "Ver todas las opiniones", "club_cta": "Hazte miembro del Club LCR",
        "prev": "Foto anterior", "next": "Foto siguiente", "dist": "Distancias", "map": "Mapa de Biescas con nuestros alojamientos", "pause": "Pausar vídeo", "play": "Reproducir vídeo",
        "gal_room": "Fotos de las habitaciones y del hotel", "book": "Reserva", "demo_name": "Nombre del huésped", "demo_text": "Aquí irá la reseña real de un huésped, con su nombre y su foto, cuando se disponga de ellas con su permiso.",
        "src": {"google": "Google", "tripadvisor": "Tripadvisor", "booking": "Booking.com"}},
 "en": {"stays": "Our accommodations in Biescas", "exp": "Top experiences in the Pyrenees", "exp_lead": "Skiing, zip lines, Biescas festivals, hikes and much more: the Pyrenees are for all year round.",
        "exp_all": "See all activities", "rev": "What our guests say", "rev_lead": "Opinions from guests who have already stayed with us.",
        "rev_demo": "DESIGN SAMPLE · not real reviews", "rev_all": "See all reviews", "club_cta": "Join the LCR Club",
        "prev": "Previous photo", "next": "Next photo", "dist": "Distances", "map": "Map of Biescas with our accommodations", "pause": "Pause video", "play": "Play video",
        "gal_room": "Room and hotel photos", "book": "Booking", "demo_name": "Guest name", "demo_text": "The real review of a guest will appear here, with their name and photo, once available with their permission.",
        "src": {"google": "Google", "tripadvisor": "Tripadvisor", "booking": "Booking.com"}},
 "fr": {"stays": "Nos hébergements à Biescas", "exp": "Meilleures expériences dans les Pyrénées", "exp_lead": "Ski, tyroliennes, fêtes de Biescas, randonnées et bien plus : les Pyrénées se vivent toute l'année.",
        "exp_all": "Voir toutes les activités", "rev": "Ce que disent nos clients", "rev_lead": "Avis de ceux qui ont déjà séjourné chez nous.",
        "rev_demo": "EXEMPLE DE DESIGN · faux avis", "rev_all": "Voir tous les avis", "club_cta": "Rejoignez le Club LCR",
        "prev": "Photo précédente", "next": "Photo suivante", "dist": "Distances", "map": "Carte de Biescas avec nos hébergements", "pause": "Mettre la vidéo en pause", "play": "Lire la vidéo",
        "gal_room": "Photos des chambres et de l'hôtel", "book": "Réservation", "demo_name": "Nom du client", "demo_text": "L'avis réel d'un client apparaîtra ici, avec son nom et sa photo, dès qu'ils seront disponibles avec son accord.",
        "src": {"google": "Google", "tripadvisor": "Tripadvisor", "booking": "Booking.com"}},
}
ICO = {
 "cal": '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3.5" y="5" width="17" height="15" rx="3"/><path d="M8 3v4M16 3v4M3.5 10h17"/></svg>',
 "moon": '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"/></svg>',
 "user": '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 20c1-4 4-6 8-6s7 2 8 6"/></svg>',
 "bed": '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 18V7M3 13h18v5M21 13v-2a3 3 0 0 0-3-3h-7v5"/></svg>',
 "train": '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="3" width="14" height="14" rx="3"/><path d="M5 11h14M9 21l2-4M15 21l-2-4"/><circle cx="9" cy="14" r=".6"/><circle cx="15" cy="14" r=".6"/></svg>',
 "plane": '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15l-8-4V5a1.5 1.5 0 0 0-3 0v6l-8 4v2l8-1.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-3.5l8 1.5z"/></svg>',
 "pin": '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>',
 "star": '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M12 2.8l2.8 5.9 6.4.8-4.7 4.4 1.2 6.4L12 17.2 6.3 20.3l1.2-6.4L2.8 9.5l6.4-.8z"/></svg>',
}

def hotel_from(h):
    ps = [p for p in PRICES["from_per_night"].get(h, {}).values() if p]
    return min(ps) if ps else None

def hotel_photos(h, n=8):
    """Fotos propias del alojamiento (de su ficha en la web actual), con las de habitación y zonas comunes primero."""
    pg = PAGES.get(("es", f"/{h}/"))
    names = [x for x, _ in page_images(pg)] if pg else []
    rank = lambda f: next((i for i, k in enumerate(("_intro-", "_rooms-", "_spa-", "_gastronomia-", "_events-")) if k in f), 9)
    names = [f for f in names if os.path.exists(os.path.join(ASSETS, "img", f))]
    return sorted(names, key=lambda f: (rank(f), names.index(f)))[:n]

def mini(lang, photos, href, cls=""):
    t = U3[lang]
    sz_ = "(max-width: 1200px) 100vw, 1180px" if "big" in cls else "(max-width: 760px) 84vw, 340px"
    figs = "".join((f'<a class="slide" href="{href}" tabindex="-1">{img(p, None, lazy=(i > 0), sizes=sz_)}</a>' if href else f'<div class="slide">{img(p, None, lazy=(i > 0), sizes=sz_)}</div>') for i, p in enumerate(photos))
    nav = (f'<button type="button" class="mini-nav prev" aria-label="{t["prev"]}">‹</button><button type="button" class="mini-nav next" aria-label="{t["next"]}">›</button>'
           '<div class="mini-dots" aria-hidden="true"></div>') if len(photos) > 1 else ""
    return f'<div class="mini {cls}" data-mini><div class="mini-track">{figs}</div>{nav}</div>'

# ---- reserva fija (desktop: barra inferior; móvil: botón que abre el panel)
def booking_dock(lang, hotel=None):
    u = UI[lang]; a, b, c = BB[lang]
    if not (MIRAI and "{checkin}" in MIRAI):
        opts = "".join(f'<option value="{h}">{esc(HNAME[h])}</option>' for h in HOTEL_SLUGS)
        return (f'<form class="dock" method="get" action="{url(lang, "/contacto/")}"><div class="dock-f"><label class="f">{ICO["bed"]}<span>{u["footer_hotels"]}</span>'
                f'<select name="alojamiento">{opts}</select></label><button class="btn" type="submit">{u["pick"]}</button></div></form>')
    tpl = MIRAI.replace("{lang}", lang)
    chain = str(config.get("mirai_chain_default", "66013"))
    ns = "".join(f'<option value="{n}"{" selected" if n == 2 else ""}>{n}</option>' for n in range(1, 15))
    ad = "".join(f'<option value="{n}"{" selected" if n == 2 else ""}>{n}</option>' for n in range(1, 11))
    hs = config.get("mirai_hotels", {})
    sel = ""
    if hs:
        sel = (f'<label class="f h">{ICO["bed"]}<span>{u["footer_hotels"]}</span><select name="hotel"><option value="{chain}">—</option>' +
               "".join(f'<option value="{v}"{" selected" if hotel == k else ""}>{esc(HNAME[k])}</option>' for k, v in hs.items() if k in HNAME) + "</select></label>")
    return (f'<form class="dock" method="get" action="{mirai_link(lang, "")}" data-tpl="{esc(tpl)}" data-chain="{chain}" aria-label="{U3[lang]["book"]}">'
            f'<button type="button" class="dock-open" aria-expanded="false">{ICO["cal"]}<span>{u["pick"]}</span></button>'
            f'<div class="dock-f">{sel}<label class="f d">{ICO["cal"]}<span>{a}</span><input type="date" name="checkin" required></label>'
            f'<label class="f s">{ICO["moon"]}<span>{b}</span><select name="nights">{ns}</select></label>'
            f'<label class="f s">{ICO["user"]}<span>{c}</span><select name="adults">{ad}</select></label>'
            f'<button class="btn" type="submit">{u["pick"]}</button></div></form>')

# ---- portada con vídeo (si existe public/video/hero.mp4|webm) y rótulo de actividades
TICKER = ["actividades_winter-formigal.webp", "actividades_spring-tirolina.webp", "actividades_summer-festival.webp", "actividades_winter-parapente.webp",
          "actividades_summer-bike.webp", "actividades_autumn-feria.webp", "actividades_summer-ordesa.webp", "actividades_winter-raqueta.webp",
          "actividades_summer-artouste.webp", "actividades_spring-feria.webp"]
def hero_video_bg(lang):
    vd = os.path.join(ASSETS, "video"); srcs = ""
    for ext, mime in (("webm", "video/webm"), ("mp4", "video/mp4")):
        if os.path.exists(os.path.join(vd, f"hero.{ext}")): srcs += f'<source src="/video/hero.{ext}" type="{mime}">'
    poster = "home_destination-01.webp"
    vid = (f'<video class="hv" autoplay muted loop playsinline preload="auto" poster="/img/{poster}" aria-hidden="true" tabindex="-1">{srcs}</video>'
           f'<button type="button" class="vid-toggle" data-pause="{U3[lang]["pause"]}" data-play="{U3[lang]["play"]}" aria-label="{U3[lang]["pause"]}">❚❚</button>') if srcs else ""
    return f'<div class="hero-img vid">{img(poster, LOGO_ALT.get(poster, ""), lazy=False)}{vid}</div>'

def activity_ticker(lang):
    acts, _ = season_activities(lang)
    lab = {f: t for v in acts.values() for f, t in v}
    items = [lab[f] for f in TICKER if f in lab]
    if not items: return ""
    row = "".join(f"<li>{esc(x)}</li>" for x in items)
    return f'<div class="ticker" aria-hidden="true"><ul>{row}{row}</ul></div>'

# ---- experiencias top
def experiences_block(lang, note=""):
    t = U3[lang]; n = SNAME[lang]; tiles = []
    for e in EXPER.get("items", []):
        if not os.path.exists(os.path.join(ASSETS, "img", e["img"])): continue
        name = e.get(lang) or e["es"]
        tiles.append(f'<a class="xp{" big" if e.get("big") else ""}" href="{url(lang, "/actividades/")}?estacion={e["season"]}">{img(e["img"], name)}'
                     f'<span class="xp-s">{n[e["season"]]}</span><span class="xp-t">{esc(name)}</span></a>')
    if not tiles: return ""
    nt = ("<p class=\"note\">" + esc(note) + "</p>") if note else ""
    return (f'<section class="sec" id="experiencias"><div class="wrap wideblock"><h2>{t["exp"]}</h2><p class="lead2">{t["exp_lead"]}</p>{nt}'
            f'<div class="xps">{"".join(tiles)}</div><p><a class="btn sm" href="{url(lang, "/actividades/")}">{t["exp_all"]}</a></p></div></section>')

# ---- club de lujo (inicio) y reseñas
CLUB_IMG = "home-biescas_spa-04.webp"
def club_benefits(sec):
    out, seen = [], set()
    for c in sec["cards"]:
        if c["title"] in seen or re.fullmatch(r"destin\w*|destination", c["title"].strip(), re.I): continue
        seen.add(c["title"]); out.append((c["title"], c["ps"][0] if c["ps"] else ""))
    return out
def club_block(lang, sec, full=False):
    u = UI[lang]; t = U3[lang]
    ben = "".join(f'<li class="glass"><b>{esc(a)}</b>{f"<span>{esc(b)}</span>" if b else ""}</li>' for a, b in club_benefits(sec))
    intro = "".join(f"<p>{esc(p)}</p>" for p in sec["paras"][:1])
    ttl = (f'<h1 class="sr">{esc(sec["title"])}</h1>' if full else f'<h2 id="club">{esc(sec["title"])}</h2>') if sec.get("title") else ""
    return (f'<section class="club{" full" if full else ""}"><div class="club-img">{img(CLUB_IMG, LOGO_ALT.get(CLUB_IMG, ""))}</div>'
            f'<div class="wrap club-in">{ttl}{intro}<ul class="club-ben">{ben}</ul><a class="btn" href="{"#unirse" if full else url(lang, "/signup/")}">{t["club_cta"]}</a></div></section>')

def stars(n):
    return '<span class="stars" role="img" aria-label="%s/5">%s</span>' % (n, ICO["star"] * int(round(n)))
def reviews_block(lang):
    t = U3[lang]; items = REVIEWS.get("items", []); demo = False
    if not items and os.environ.get("REVIEWS_DEMO"):
        demo = True
        demo_src = [("google", "hotel-tierra-biescas"), ("tripadvisor", "hotel-posada-de-ruba"), ("booking", "apartamentos-lcr-boutique"),
                    ("google", "apartamento-lcr-los-valles"), ("tripadvisor", "apartamentos-lcr-suites"), ("booking", "hotel-tierra-biescas")]
        items = []
        for i, (s_, h_) in enumerate(demo_src):
            ph = [x for x in hotel_photos(h_, 6) if "_rooms-" in x or "_intro-" in x][:2] if i % 2 == 0 else []
            items.append({"source": s_, "author": f'{t["demo_name"]} {i + 1}', "rating": 5 if i != 2 else 4, "hotel": h_, "text": t["demo_text"], "photos": ph})
    if not items: return ""
    cards = []
    for r in items:
        ini = "".join(w[0] for w in (r.get("author") or "?").split()[:2]).upper()
        av = f'<img src="{r["avatar"] if r["avatar"].startswith("http") else "/img/" + r["avatar"]}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer">' if r.get("avatar") else f'<span class="ini">{esc(ini)}</span>'
        ph = "".join(f'<img src="/img/{p}" alt="" loading="lazy" decoding="async">' for p in r.get("photos", [])[:3])
        hn = f'<span class="rh">{esc(HNAME[r["hotel"]])}</span>' if r.get("hotel") in HNAME else ""
        src = t["src"].get(r.get("source"), r.get("source", ""))
        link = f'<a class="rl" href="{esc(r["url"])}" rel="noopener nofollow" target="_blank">{src}</a>' if r.get("url") else f'<span class="rl">{src}</span>'
        cards.append(f'<article class="card rev"><header><span class="av">{av}</span><div><b>{esc(r.get("author", ""))}</b>{stars(r.get("rating", 5))}</div>{link}</header>'
                     f'<p>{esc(r.get("text", ""))}</p>{f"<div class=rph>{ph}</div>" if ph else ""}<footer>{hn}<span>{esc(r.get("date", ""))}</span></footer></article>')
    links = "".join(f'<a class="btn sm ghost" href="{esc(v)}" rel="noopener" target="_blank">{t["src"].get(k, k)}</a>' for k, v in config.get("reviews_links", {}).items() if v)
    summ = "".join(f'<li><b>{v.get("rating", "")}</b>{stars(v.get("rating", 5))}<span>{t["src"].get(k, k)} · {v.get("count", "")}</span></li>' for k, v in REVIEWS.get("summary", {}).items())
    flag = f'<p class="demo-flag">{t["rev_demo"]}</p>' if demo else ""
    return (f'<section class="sec reviews" id="resenas"><div class="wrap wideblock"><h2>{t["rev"]}</h2><p class="lead2">{t["rev_lead"]}</p>{flag}'
            f'{f"<ul class=rsum>{summ}</ul>" if summ else ""}<div class="cards snap revs">{"".join(cards)}</div>{f"<p class=rlinks>{links}</p>" if links else ""}</div></section>')

# ---- localización compacta
def location_block(lang, sec, h):
    t = U3[lang]
    intro = next((c for c in sec["cards"] if c["ps"]), None)
    addr = next((c["title"] for c in sec["cards"] if re.search(r"\b\d{5}\b", c["title"])), "")
    rows = []
    for c in sec["cards"]:
        if c is intro or c["title"] == addr: continue
        for m in re.finditer(r"([^.]+?),?\s*(?:a|at|à|-|–)?\s*(\d+(?:[.,]\d+)?)\s*km", c["title"]):
            place = m.group(1).strip(" ,:-–"); km = m.group(2)
            ic = "train" if re.search(r"renfe|train|gare|estaci[oó]n de tren", place, re.I) else "plane" if re.search(r"aeropuerto|airport|a[eé]roport", place, re.I) else "pin"
            rows.append(f'<li>{ICO[ic]}<span>{esc(place)}</span><b>{km} km</b></li>')
    if not (intro and rows): return None
    mp = "map-frame-mb.webp"
    mapimg = f'<figure class="loc-map">{img(mp, t["map"])}</figure>' if os.path.exists(os.path.join(ASSETS, "img", mp)) else ""
    eb = ('<p class="eyebrow">' + ICO["pin"] + " " + esc(addr) + "</p>") if addr else ""
    return (f'<section class="sec"><div class="wrap wideblock"><h2 id="{slug(sec["title"])}">{esc(sec["title"])}</h2>'
            f'<div class="loc"><div class="loc-main">{eb}<h3>{esc(intro["title"])}</h3><p>{esc(intro["ps"][0])}</p></div>'
            f'<div class="loc-list"><h3>{t["dist"]}</h3><ul>{"".join(rows)}</ul></div>{mapimg}</div></div></section>')

# ---- datos estructurados (JSON-LD)
def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "</script>"
def parse_addr(a):
    m = re.match(r"(.*?)\s*(\d{5})\s+([^,]+),\s*([^,]+)", a or "")
    if not m: return None
    return {"@type": "PostalAddress", "streetAddress": m.group(1).strip(" ,"), "postalCode": m.group(2), "addressLocality": m.group(3).strip(), "addressRegion": m.group(4).strip(), "addressCountry": "ES"}
def ld_hotel(lang, h):
    pg = PAGES.get(("es", f"/{h}/")); ph = hotel_photos(h, 3)
    o = {"@context": "https://schema.org", "@type": "Hotel" if h in ("hotel-tierra-biescas", "hotel-posada-de-ruba") else "LodgingBusiness",
         "name": HNAME[h], "url": f"{SITE_URL}{url(lang, f'/{h}/')}", "telephone": PHONE_TXT, "email": EMAIL, "inLanguage": lang,
         "image": [f"{SITE_URL}/img/{x}" for x in ph], "sameAs": ["https://www.instagram.com/pirineohuesca/"],
         "parentOrganization": {"@type": "Organization", "name": "LCR Hoteles y Apartamentos", "url": SITE_URL}}
    a = parse_addr(addr_of(h, "es"))
    if a: o["address"] = a
    if h == "hotel-tierra-biescas": o["starRating"] = {"@type": "Rating", "ratingValue": "4"}
    f = hotel_from(h)
    if f: o["priceRange"] = f"desde {f} €"
    return ld(o)
def ld_home(lang):
    org = {"@context": "https://schema.org", "@type": "Organization", "name": "LCR Hoteles y Apartamentos", "url": SITE_URL, "telephone": PHONE_TXT, "email": EMAIL,
           "logo": f"{SITE_URL}/img/logo_lcr-condensed.webp", "sameAs": ["https://www.instagram.com/pirineohuesca/"]}
    ws = {"@context": "https://schema.org", "@type": "WebSite", "name": "LCR Hoteles y Apartamentos", "url": SITE_URL, "inLanguage": lang}
    return ld(org) + ld(ws)
def ld_crumbs(lang, items):
    return ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": f"{SITE_URL}{u_}"} for i, (n, u_) in enumerate(items)]})

# ---------------------------------------------------------------- páginas
def build_home_lux(lang):
    pg = P(lang, "/"); u = UI[lang]; t = U3[lang]; seo = SEO.get(lang) or SEO.get("es", {})
    pre, h1, body = split_page(pg["items"]); secs = group_sections(body); lead = secs[0]
    cards = []
    for i, (h, name, logo, thumb) in enumerate(HOTELS):
        desc = lead["paras"][1 + i] if len(lead["paras"]) > 1 + i else ""
        fp = hotel_from(h)
        price = f'<p class="from">{u["from_"]} <b>{fp}</b> {u["per_night"]}</p>' if fp else ""
        cards.append(f'<article class="card stay">{mini(lang, hotel_photos(h) or [thumb], HU(lang, h))}<h3><a href="{HU(lang, h)}">{esc(name)}</a></h3>'
                     f'<p>{esc(desc)}</p>{price}<a class="btn sm" href="{HU(lang, h)}">{u["see"]}</a></article>')
    find = lambda rx: next((x for x in secs[1:] if re.search(rx, x["title"] or "", re.I)), None)
    club, explora, act, insta = find(r"club"), find(r"explora|explore|explorez"), find(r"^(actividades|activities|activités)$"), find(r"@pirineohuesca")
    b = [benefits_strip(pre), hero(lang, seo.get("h1") or lead["title"], lead["title"], lead["paras"][0] if lead["paras"] else "", ("__video__", ""), None, "home"),
         f'<section class="sec" id="alojamientos"><div class="wrap wideblock"><h2>{t["stays"]}</h2><div class="cards five snap">{"".join(cards)}</div></div></section>']
    if act and SEASONS:
        intro = next((c["ps"][0] for c in act["cards"] if c["ps"]), "")
        b.append(render_section(dict(act, cards=[], subs=[], paras=[intro] if intro else act["paras"]), season_block(lang) + f'<p><a class="btn sm" href="{url(lang, "/actividades/")}">{u["actividades"]}</a></p>'))
    b.append(experiences_block(lang, " ".join(explora["paras"][:1]) if explora else ""))
    if insta:
        ex = '<div class="gal insta">' + "".join(f"<figure>{img(f'tpl_instagram-0{i}.webp')}</figure>" for i in range(6)) + "</div>"
        b.append(render_section(dict(insta, title="Instagram " + insta["title"]), ex))
    if club: b.append(club_block(lang, club))
    b.append(reviews_block(lang))
    write(lang, "/", page_shell(lang, "/", seo.get("title") or title_of(pg, "LCR Hoteles y Apartamentos"), seo.get("desc") or pg["desc"], "".join(b), LANGS, ld_home(lang)))

def build_home(lang):
    if LUX: return build_home_lux(lang)
    pg = P(lang, "/"); u = UI[lang]
    pre, h1, body = split_page(pg["items"])
    secs = group_sections(body)
    lead = secs[0]
    cards = []
    for i, (h, name, logo, thumb) in enumerate(HOTELS):
        desc = lead["paras"][1 + i] if len(lead["paras"]) > 1 + i else ""
        cards.append(f'<article class="card stay"><a class="thumb" href="{HU(lang, h)}">{img(thumb)}</a><h3><a href="{HU(lang, h)}">{esc(name)}</a></h3>'
                     f'<p>{esc(desc)}</p><a class="btn sm" href="{HU(lang, h)}">{u["see"]}</a></article>')
    b = [benefits_strip(pre), hero(lang, lead["title"], h1, lead["paras"][0] if lead["paras"] else "", (("__season__", "") if (LUX and SEASONS) else ("home_destination-01.webp", LOGO_ALT.get("home_destination-01.webp", ""))), None, "home"),
         f'<section class="sec"><div class="wrap"><div class="cards five">{"".join(cards)}</div></div></section>']
    pool = Pool(pg, skip=SEASON_IMGS)
    for s in secs[1:]:
        extra = ""
        if LUX and SEASONS and re.fullmatch(r"actividades|activities|activités", (s["title"] or "").strip(), re.I):
            intro = next((c["ps"][0] for c in s["cards"] if c["ps"]), "")
            b.append(render_section(dict(s, cards=[], subs=[], paras=[intro] if intro else s["paras"]), season_block(lang) + f'<p><a class="btn sm" href="{url(lang, "/actividades/")}">{u["actividades"]}</a></p>')); continue
        if re.search(r"@pirineohuesca", s["title"] or ""):
            extra = '<div class="gal insta">' + "".join(f"<figure>{img(f'tpl_instagram-0{i}.webp')}</figure>" for i in range(6)) + "</div>"
            s = dict(s); s["title"] = "Instagram " + s["title"]
        b.append(render_section(s, extra, side=None if extra else pool.take(s)))
    write(lang, "/", page_shell(lang, "/", title_of(pg, "LCR Hoteles y Apartamentos"), pg["desc"] or lead["paras"][0][:155], "".join(b), LANGS))

def build_hotel_home(lang, h):
    key = f"/{h}/"; pg = P(lang, key); u = UI[lang]
    pre, h1, body = split_page(pg["items"])
    secs = group_sections(body)
    himg = next(iter(page_images(pg)), None)
    pool = Pool(pg, skip={himg[0]} if himg else (), strict=True)
    # intro = párrafos antes del primer h2
    intro = []
    for t, x in body:
        if t == "h2": break
        if t == "p": intro.append(x)
    first_h2 = next((i for i, (t, _) in enumerate(body) if t == "h2"), 0)
    lead = intro[0] if intro else ""
    out = [benefits_strip(pre), hero(lang, h1 or HNAME[h], "", lead, himg, (u["pick"], mirai_link(lang, h))), sub_nav(lang, h, key)]
    sust = intro[1:]
    if sust: out.append(f'<section class="sec"><div class="wrap"><ul class="chips">' + "".join(f"<li>{esc(p)}</li>" for p in sust) + "</ul></div></section>")
    # secciones: la primera es habitaciones, la que contiene 'ofertas' es la de ofertas
    for i, s in enumerate(secs):
        if intro and i == 0 and s["title"] is None: continue
        if i == 0 or (secs[0]["title"] is None and i == 1):
            rp = [p for c in s["cards"] for p in c["ps"]] + s["paras"]
            out.append(f'<section class="sec alt" id="rooms"><div class="wrap"><h2>{esc(UI[lang]["apts"] if h in APT else u["rooms_title"])}</h2>'
                       f'{"".join(f"<p>{esc(p)}</p>" for p in rp[:1])}{room_cards(lang, h)}</div></section>')
            continue
        if LUX and re.search(r"localizaci|location|emplacement", s["title"] or "", re.I):
            blk = location_block(lang, s, h)
            if blk: out.append(blk); continue
        if re.search(r"ofertas|offers|offres", s["title"] or "", re.I):
            ex = offers_html(lang, h)
            if ("es", f"/{h}/ofertas/") in PAGES: ex += f'<p><a class="btn sm" href="{url(lang, f"/{h}/ofertas/")}">{u["all_offers"]}</a></p>'
            out.append(render_section(dict(s, cards=[]), ex)); continue
        if LUX and re.search(r"club", s["title"] or "", re.I):
            out.append(club_block(lang, s)); continue
        if re.search(r"club", s["title"] or "", re.I):
            out.append(render_section(s, f'<p><a class="btn sm" href="{url(lang, "/signup/")}">{u["club_title"]}</a></p>', side=pool.take(s))); continue
        out.append(render_section(s, side=pool.take(s)))
    if LUX and SEASONS:
        out.append(f'<section class="sec"><div class="wrap wideblock"><h2>{SUI[lang]["title"]}</h2>{season_block(lang)}</div></section>')
    out.append(gallery_html(lang, pg, skip=pool.used))
    xh = (ld_hotel(lang, h) + ld_crumbs(lang, [("LCR", url(lang, "/")), (HNAME[h], url(lang, key))])) if LUX else ""
    write(lang, key, page_shell(lang, key, title_of(pg, HNAME[h]), pg["desc"] or lead[:155], "".join(out), LANGS, xh))

def build_rooms_list(lang, h):
    sub = "apartamentos" if h in APT else "habitaciones"
    key = f"/{h}/{sub}/"; u = UI[lang]
    pg = P(lang, key) or P(lang, f"/{h}/")
    title = u["apts"] if h in APT else u["rooms"]
    common = ROOMS[h][0]["common"][lang] if ROOMS[h] else []
    intro = pg["desc"] if pg and ("es", key) in PAGES else ""
    out = [hero(lang, f"{title} · {HNAME[h]}", "", intro, None, None, "plain"), sub_nav(lang, h, key)]
    out.append(f'<section class="sec"><div class="wrap">' + (f'<ul class="chips">' + "".join(f"<li>{esc(c)}</li>" for c in common) + "</ul>" if common and h not in APT else "") + room_cards(lang, h) + "</div></section>")
    if h == "apartamentos-lcr-boutique":   # la ficha original lista los 9 apartamentos
        for oh in ("apartamentos-lcr-suites", "apartamento-lcr-los-valles"):
            out.append(f'<section class="sec alt"><div class="wrap"><h2>{esc(HNAME[oh])}</h2>{room_cards(lang, oh)}</div></section>')
    write(lang, key, page_shell(lang, key, f"{title} | {HNAME[h]} | LCR", intro or f"{title} {HNAME[h]}", "".join(out), LANGS))

def build_room(lang, h, r):
    sub = "apartamentos" if h in APT else "habitaciones"
    key = f"/{h}/{sub}/{r['slug']}/"; u = UI[lang]; d = r["i18n"][lang]
    p = price_of(h, r["slug"])
    pr = (f'<p class="price big">{u["from_"]} <b>{p}</b> {u["per_night"]}</p><p class="note">{u["price_note"]} {PRICES["updated"][8:]}.{PRICES["updated"][5:7]}.{PRICES["updated"][:4]}.</p>'
          if p else f'<p class="note">{u["no_price"]}</p>')
    pg = P(lang, f"/{h}/")
    ims = page_images(pg)
    himg = ims[0] if ims else None
    gal = ""
    if LUX:
        rix = [x["slug"] for x in ROOMS[h]].index(r["slug"])
        ph = room_photo(h, r["slug"], rix)
        if ph: himg = (ph, LOGO_ALT.get(ph, ""))
        allp = room_pool(h) + [x for x in hotel_photos(h, 14) if x not in room_pool(h)]
        pool = ([himg[0]] if himg else []) + [f for f in allp if not himg or f != himg[0]]
        if len(pool) > 1: gal = f'<section class="sec alt"><div class="wrap wideblock"><h2>{U3[lang]["gal_room"]}</h2>{mini(lang, pool, None, "big")}</div></section>'
    feats = "".join(f"<li>{esc(f)}</li>" for f in dict.fromkeys(r["common"][lang][:0] + d["feats"]))
    common = "".join(f"<li>{esc(f)}</li>" for f in r["common"][lang]) if h not in APT else ""
    others = "".join(f'<li><a href="{HU(lang, h, sub, o["slug"])}">{esc(o["i18n"][lang]["name"])}</a></li>' for o in ROOMS[h] if o is not r)
    body = [hero(lang, d["name"], HNAME[h], "", himg, None, "" if himg else "plain"),
            f'<section class="sec"><div class="wrap two"><div><p>{esc(d["desc"])}</p>'
            f'{"<h2>" + u["rooms_title"] + "</h2>" if False else ""}<ul class="chips">{feats}{common}</ul></div>'
            f'<aside class="book">{pr}<a class="btn" href="{mirai_link(lang, h, r["slug"])}">{u["pick"]}</a>'
            f'<p class="note">{u["book_direct"]}: {PHONE_TXT} · <a href="mailto:{EMAIL}">{EMAIL}</a></p></aside></div></section>',
            gal,
            f'<section class="sec alt"><div class="wrap"><h2>{u["other_rooms"]}</h2><ul class="chips links">{others}</ul>'
            f'<p><a class="link" href="{HU(lang, h, sub)}">← {u["back"]}</a></p></div></section>']
    xh = ld_crumbs(lang, [("LCR", url(lang, "/")), (HNAME[h], url(lang, f"/{h}/")), (d["name"], url(lang, key))]) if LUX else ""
    write(lang, key, page_shell(lang, key, f'{d["name"]} | {HNAME[h]} | LCR', d["desc"][:155], "".join(body), LANGS, xh))

def build_generic(lang, key, h=None):
    pg = P(lang, key); u = UI[lang]
    miss = ("es", key) in PAGES and (lang, key) not in PAGES and lang != "es"
    pre, h1, body = split_page(pg["items"])
    secs = group_sections(body)
    himg = next(iter(page_images(pg)), None)
    if LUX and SEASONS and key in ("/actividades/", "/entorno/"): himg = ("__season__", "")
    pool = Pool(pg, skip=({himg[0]} if himg else set()) | (SEASON_IMGS if LUX else set()))
    nav = sub_nav(lang, h, key) if h else ""
    out = [hero(lang, h1 or title_of(pg, "").split(" | ")[0], "", pg["desc"], himg, None, "plain" if not himg else ""), nav]
    if miss: out.append(f'<div class="wrap"><p class="note">{u["missing_lang"]}</p></div>')
    for s in secs:
        if h and key.endswith("/ofertas/") and re.search(r"^ofertas$|^offers$|^offres$", (s["title"] or "").strip(), re.I):
            out.append(render_section(dict(s, cards=[]), offers_html(lang, h))); continue
        if LUX and SEASONS and key == "/actividades/":
            c4 = next((c for c in s["cards"] if re.search(r"4 estaciones|4 seasons|4 saisons", c["title"], re.I)), None)
            if c4:
                out.append(render_section(dict(s, cards=[c for c in s["cards"] if c is not c4], paras=s["paras"] + c4["ps"][:1]), season_block(lang))); continue
        out.append(render_section(s, side=pool.take(s)))
    ev = key.split("/")[-2] in ("bodas", "stages-deportivos", "eventos-empresa")
    if ev:
        out.append(f'<section class="sec alt"><div class="wrap"><p><a class="btn" href="{url(lang, "/contacto/")}?alojamiento={h}&asunto={key.split("/")[-2]}">{u["contacto"]}</a></p></div></section>')
    out.append(gallery_html(lang, pg, skip=pool.used))
    write(lang, key, page_shell(lang, key, title_of(pg, key), pg["desc"] or (h1 or ""), "".join(out), LANGS))

def form_field(name, label, typ="text", req=True, area=False):
    r = " required" if req else ""
    if area: return f'<p><label for="{name}">{label}{" *" if req else ""}</label><textarea id="{name}" name="{name}" rows="6"{r}></textarea></p>'
    return f'<p><label for="{name}">{label}{" *" if req else ""}</label><input id="{name}" name="{name}" type="{typ}"{r}></p>'

def build_contact(lang):
    u = UI[lang]; key = "/contacto/"
    opts = "".join(f'<option value="{h}">{esc(HNAME[h])}</option>' for h in HOTEL_SLUGS)
    rc = config.get("recaptcha_site_key", "")
    rc_html = f'<div class="g-recaptcha" data-sitekey="{rc}"></div><script src="https://www.google.com/recaptcha/api.js" async defer></script>' if rc else ""
    form = (f'<form class="form" method="post" action="/api/contact" data-ok="{esc(u["f_ok"])}" data-err="{esc(u["f_err"])} {EMAIL}">'
            f'<input type="hidden" name="lang" value="{lang}"><p class="hp" aria-hidden="true"><label>Web <input name="web" tabindex="-1" autocomplete="off"></label></p>'
            f'<p><label for="alojamiento">{u["footer_hotels"]}</label><select id="alojamiento" name="alojamiento"><option value="">—</option>{opts}</select></p>'
            + form_field("nombre", u["f_name"]) + form_field("email", u["f_email"], "email") + form_field("telefono", u["f_phone"], "tel", False)
            + form_field("asunto", u["f_subject"]) + form_field("mensaje", u["f_msg"], area=True)
            + f'<p class="check"><label><input type="checkbox" name="privacidad" value="1" required> {u["f_priv"]} *</label></p>{rc_html}'
            f'<p class="note">{u["f_after"]} <br>{u["f_req"]}: *</p><button class="btn" type="submit">{u["f_send"]}</button><p class="status" role="status" aria-live="polite"></p></form>')
    side = (f'<aside class="book"><h2>{u["contacto"]}</h2><p><a href="tel:{PHONE_TEL}">{PHONE_TXT}</a><br><a href="{WHATSAPP}">{u["wa"]} 687 003 603</a><br>'
            f'<a href="mailto:{EMAIL}">{EMAIL}</a></p></aside>')
    body = hero(lang, u["contact_title"], "", u["contact_lead"], None, None, "plain") + f'<section class="sec"><div class="wrap two"><div>{form}</div>{side}</div></section>'
    write(lang, key, page_shell(lang, key, f'{u["contact_title"]} | LCR Hoteles y Apartamentos', u["contact_lead"], body, LANGS))

def build_signup(lang):
    u = UI[lang]; key = "/signup/"
    pg = P(lang, key)
    pre, h1, body = split_page(pg["items"]) if pg else ([], None, [])
    secs = group_sections(body)
    form = (f'<form class="form" method="post" action="/api/club" data-ok="{esc(u["f_ok_club"])}" data-err="{esc(u["f_err"])} {EMAIL}">'
            f'<input type="hidden" name="lang" value="{lang}"><p class="hp" aria-hidden="true"><label>Web <input name="web" tabindex="-1" autocomplete="off"></label></p>'
            + form_field("nombre", u["f_name"]) + form_field("email", u["f_email"], "email") + form_field("telefono", u["f_phone"], "tel", False)
            + f'<p class="check"><label><input type="checkbox" name="consentimiento" value="1" required> {u["f_club_ok"]} *</label></p>'
            f'<p class="check"><label><input type="checkbox" name="privacidad" value="1" required> {u["f_priv"]} *</label></p>'
            f'<p class="note">{u["f_after"]} <br>{u["f_req"]}: *</p><button class="btn" type="submit">{u["f_send"]}</button><p class="status" role="status" aria-live="polite"></p></form>')
    if LUX:
        sec0 = secs[0] if secs else {"title": None, "paras": [], "cards": []}
        b = club_block(lang, dict(sec0, title=u["club_title"]), True) + f'<section class="sec" id="unirse"><div class="wrap narrow"><div class="formpanel">{form}</div></div></section>'
    else:
        b = hero(lang, u["club_title"], "", "", None, None, "plain") + "".join(render_section(s) for s in secs) + f'<section class="sec alt"><div class="wrap">{form}</div></section>'
    write(lang, key, page_shell(lang, key, f'{u["club_title"]} | LCR Hoteles y Apartamentos', u["club_title"], b, LANGS))

def build_404():
    body = '<section class="hero plain"><div class="wrap hero-in"><h1>404</h1><p class="lead">Página no encontrada · Page not found · Page introuvable</p><a class="btn" href="/">LCR Hoteles y Apartamentos</a></div></section>'
    open(os.path.join(PUB, "404.html"), "w", encoding="utf-8").write(page_shell("es", "/", "404 | LCR Hoteles y Apartamentos", "404", body, ["es"]))

def build_sitemap():
    urls = []
    for lang, key in GENERATED:
        alts = "".join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{SITE_URL}{url(l, key)}"/>' for l in LANGS)
        urls.append(f"<url><loc>{SITE_URL}{url(lang, key)}</loc>{alts}</url>")
    open(os.path.join(PUB, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">' + "".join(urls) + "</urlset>")
    open(os.path.join(PUB, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")

def prepare_pub():
    if PUB == ASSETS: return
    os.makedirs(PUB, exist_ok=True)
    for n in ("img", "fonts", "video"):
        t = os.path.join(PUB, n)
        if os.path.isdir(os.path.join(ASSETS, n)) and not os.path.lexists(t): os.symlink(os.path.join(ASSETS, n), t)
    for n in ("css", "js"):
        shutil.rmtree(os.path.join(PUB, n), ignore_errors=True)
        shutil.copytree(os.path.join(ASSETS, n), os.path.join(PUB, n))

def main():
    prepare_pub()
    for d in os.listdir(PUB):
        if d not in ("img", "fonts", "css", "js", "video"): shutil.rmtree(os.path.join(PUB, d), ignore_errors=True) if os.path.isdir(os.path.join(PUB, d)) else os.remove(os.path.join(PUB, d))
    for lang in LANGS:
        build_home(lang); build_contact(lang); build_signup(lang)
        for h in HOTEL_SLUGS:
            build_hotel_home(lang, h)
            build_rooms_list(lang, h)
            for r in ROOMS[h]: build_room(lang, h, r)
        # páginas genéricas: todas las claves ES existentes que no se han generado a medida
        done = {'/', '/contacto/', '/signup/'} | {f"/{h}/" for h in HOTEL_SLUGS}
        for (l, key) in sorted(k for k in PAGES if k[0] == "es"):
            if key in done: continue
            parts = [p for p in key.split("/") if p]
            if len(parts) == 2 and parts[1] in ("habitaciones", "apartamentos"): continue
            build_generic(lang, key, parts[0] if parts[0] in HOTEL_SLUGS else None)
    build_404(); build_sitemap()
    print(f"{len(GENERATED)} páginas generadas")

if __name__ == "__main__":
    main()
