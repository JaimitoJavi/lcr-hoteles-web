#!/usr/bin/env python3
"""Genera la web estática de LCR Hoteles y Apartamentos en /public.

Fuente de contenido: content/crawl.json (texto e imágenes de lcrhoteles.com del 17.11.2026).
Datos editables sin tocar código: content/prices.json, content/offers.json, content/config.json.
Uso:  python3 tools/build.py
"""
import json, os, re, html, shutil
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "public")
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

def mirai_link(lang, h, room=None):
    if MIRAI:
        return MIRAI.replace("{hotel}", h).replace("{room}", room or "").replace("{lang}", lang)
    return url(lang, "/contacto/") + (f"?alojamiento={h}" + (f"&habitacion={room}" if room else ""))

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
def img(n, alt=None, cls="", lazy=True, w=None, h=None):
    a = alt if alt is not None else LOGO_ALT.get(n, "")
    a = a.strip('"')
    sz = f' width="{w}" height="{h}"' if w else ""
    return f'<img src="/img/{n}" alt="{esc(a)}"{sz}{" loading=lazy" if lazy else ""}{" class=" + cls if cls else ""} decoding="async">'

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
    return f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE_URL}{url(lang, key)}">{alts}{xdef}
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:type" content="website">
<link rel="icon" href="/img/logo_lcr-condensed.webp"><link rel="stylesheet" href="/fonts/fonts.css"><link rel="stylesheet" href="/css/site.css">{extra_head}
</head><body>
{header(lang, key, avail)}
<main id="main">{body}</main>
{footer(lang)}
<script src="/js/site.js" defer></script></body></html>'''

def hero(lang, h1, eyebrow, lead, image, cta=None, cls=""):
    c = f'<a class="btn" href="{cta[1]}">{esc(cta[0])}</a>' if cta else ""
    bg = f'<div class="hero-img">{img(image[0], image[1], lazy=False)}</div>' if image else ""
    return f'<section class="hero {cls}">{bg}<div class="wrap hero-in">{f"<p class=eyebrow>{esc(eyebrow)}</p>" if eyebrow else ""}<h1>{esc(h1)}</h1>{f"<p class=lead>{esc(lead)}</p>" if lead else ""}{c}</div></section>'

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

def render_section(s, extra="", skip_title=False):
    out = ['<section class="sec"><div class="wrap">']
    if s["title"] and not skip_title: out.append(f'<h2 id="{slug(s["title"])}">{esc(s["title"])}</h2>')
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
    out.append(extra + "</div></section>")
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
    for r in rs:
        d = r["i18n"][lang]
        p = price_of(h, r["slug"])
        pr = f'<p class="price">{UI[lang]["from_"]} <b>{p}</b> {UI[lang]["per_night"]}</p>' if p else ""
        cards.append(f'<article class="card room"><h3><a href="{HU(lang, h, sub, r["slug"])}">{esc(d["name"])}</a></h3>'
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

# ---------------------------------------------------------------- páginas
def build_home(lang):
    pg = P(lang, "/"); u = UI[lang]
    pre, h1, body = split_page(pg["items"])
    secs = group_sections(body)
    lead = secs[0]
    cards = []
    for i, (h, name, logo, thumb) in enumerate(HOTELS):
        desc = lead["paras"][1 + i] if len(lead["paras"]) > 1 + i else ""
        cards.append(f'<article class="card stay"><a class="thumb" href="{HU(lang, h)}">{img(thumb)}</a><h3><a href="{HU(lang, h)}">{esc(name)}</a></h3>'
                     f'<p>{esc(desc)}</p><a class="btn sm" href="{HU(lang, h)}">{u["see"]}</a></article>')
    b = [benefits_strip(pre), hero(lang, lead["title"], h1, lead["paras"][0] if lead["paras"] else "", ("home_destination-01.webp", LOGO_ALT.get("home_destination-01.webp", "")), None, "home"),
         f'<section class="sec"><div class="wrap"><div class="cards five">{"".join(cards)}</div></div></section>']
    for s in secs[1:]:
        extra = ""
        if re.search(r"@pirineohuesca", s["title"] or ""):
            extra = '<div class="gal insta">' + "".join(f"<figure>{img(f'tpl_instagram-0{i}.webp')}</figure>" for i in range(6)) + "</div>"
            s = dict(s); s["title"] = "Instagram " + s["title"]
        b.append(render_section(s, extra))
    write(lang, "/", page_shell(lang, "/", title_of(pg, "LCR Hoteles y Apartamentos"), pg["desc"] or lead["paras"][0][:155], "".join(b), LANGS))

def build_hotel_home(lang, h):
    key = f"/{h}/"; pg = P(lang, key); u = UI[lang]
    pre, h1, body = split_page(pg["items"])
    secs = group_sections(body)
    himg = next(iter(page_images(pg)), None)
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
        if re.search(r"ofertas|offers|offres", s["title"] or "", re.I):
            ex = offers_html(lang, h)
            if ("es", f"/{h}/ofertas/") in PAGES: ex += f'<p><a class="btn sm" href="{url(lang, f"/{h}/ofertas/")}">{u["all_offers"]}</a></p>'
            out.append(render_section(dict(s, cards=[]), ex)); continue
        if re.search(r"club", s["title"] or "", re.I):
            out.append(render_section(s, f'<p><a class="btn sm" href="{url(lang, "/signup/")}">{u["club_title"]}</a></p>')); continue
        out.append(render_section(s))
    out.append(gallery_html(lang, pg))
    write(lang, key, page_shell(lang, key, title_of(pg, HNAME[h]), pg["desc"] or lead[:155], "".join(out), LANGS))

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
    feats = "".join(f"<li>{esc(f)}</li>" for f in dict.fromkeys(r["common"][lang][:0] + d["feats"]))
    common = "".join(f"<li>{esc(f)}</li>" for f in r["common"][lang]) if h not in APT else ""
    others = "".join(f'<li><a href="{HU(lang, h, sub, o["slug"])}">{esc(o["i18n"][lang]["name"])}</a></li>' for o in ROOMS[h] if o is not r)
    body = [hero(lang, d["name"], HNAME[h], "", himg, None, "plain"),
            f'<section class="sec"><div class="wrap two"><div><p>{esc(d["desc"])}</p>'
            f'{"<h2>" + u["rooms_title"] + "</h2>" if False else ""}<ul class="chips">{feats}{common}</ul></div>'
            f'<aside class="book">{pr}<a class="btn" href="{mirai_link(lang, h, r["slug"])}">{u["pick"]}</a>'
            f'<p class="note">{u["book_direct"]}: {PHONE_TXT} · <a href="mailto:{EMAIL}">{EMAIL}</a></p></aside></div></section>',
            f'<section class="sec alt"><div class="wrap"><h2>{u["other_rooms"]}</h2><ul class="chips links">{others}</ul>'
            f'<p><a class="link" href="{HU(lang, h, sub)}">← {u["back"]}</a></p></div></section>']
    write(lang, key, page_shell(lang, key, f'{d["name"]} | {HNAME[h]} | LCR', d["desc"][:155], "".join(body), LANGS))

def build_generic(lang, key, h=None):
    pg = P(lang, key); u = UI[lang]
    miss = ("es", key) in PAGES and (lang, key) not in PAGES and lang != "es"
    pre, h1, body = split_page(pg["items"])
    secs = group_sections(body)
    himg = next(iter(page_images(pg)), None)
    nav = sub_nav(lang, h, key) if h else ""
    out = [hero(lang, h1 or title_of(pg, "").split(" | ")[0], "", pg["desc"], himg, None, "plain" if not himg else ""), nav]
    if miss: out.append(f'<div class="wrap"><p class="note">{u["missing_lang"]}</p></div>')
    for s in secs:
        if h and key.endswith("/ofertas/") and re.search(r"^ofertas$|^offers$|^offres$", (s["title"] or "").strip(), re.I):
            out.append(render_section(dict(s, cards=[]), offers_html(lang, h))); continue
        out.append(render_section(s))
    ev = key.split("/")[-2] in ("bodas", "stages-deportivos", "eventos-empresa")
    if ev:
        out.append(f'<section class="sec alt"><div class="wrap"><p><a class="btn" href="{url(lang, "/contacto/")}?alojamiento={h}&asunto={key.split("/")[-2]}">{u["contacto"]}</a></p></div></section>')
    out.append(gallery_html(lang, pg, skip={himg[0]} if himg else ()))
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

def main():
    for d in os.listdir(PUB):
        if d not in ("img", "fonts", "css", "js"): shutil.rmtree(os.path.join(PUB, d), ignore_errors=True) if os.path.isdir(os.path.join(PUB, d)) else os.remove(os.path.join(PUB, d))
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
