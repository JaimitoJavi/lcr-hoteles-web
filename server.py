#!/usr/bin/env python3
"""Servidor de LCR Hoteles y Apartamentos: sirve /public y recibe los formularios.

Variables de entorno (todas opcionales salvo para el envío real de emails):
  PORT               puerto (Railway lo define solo)
  NOTIFY_EMAIL       destino de los avisos (por defecto reservas@lcrhoteles.com)
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM   salida de email
  RECAPTCHA_SECRET   si existe, se valida reCAPTCHA v2
  DATA_DIR           carpeta donde se guarda una copia de cada consulta (por defecto ./data)
"""
import re, json, os, re, smtplib, time, urllib.parse, urllib.request
from email.message import EmailMessage
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "public")
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(ROOT, "data"))
NOTIFY = os.environ.get("NOTIFY_EMAIL", "reservas@lcrhoteles.com")
HITS = {}
OK = {"es": "Gracias. Hemos recibido tu mensaje.", "en": "Thank you. We have received your message.", "fr": "Merci. Nous avons bien reçu votre message."}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def clean(v, n=2000):
    return re.sub(r"[\r\n\t]+", " ", (v or "").strip())[:n] if n < 300 else (v or "").replace("\r", "").strip()[:n]

def send_mail(kind, d):
    lines = [f"{k}: {v}" for k, v in d.items()]
    body = "\n".join(lines)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "consultas.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"fecha": time.strftime("%Y-%m-%dT%H:%M:%S"), "tipo": kind, **d}, ensure_ascii=False) + "\n")
    host = os.environ.get("SMTP_HOST")
    if not host:
        print(f"[{kind}] SMTP_HOST no configurado; consulta guardada en {DATA_DIR}", flush=True)
        return False
    m = EmailMessage()
    m["Subject"] = f"[lcrhoteles.com] {kind}: {d.get('asunto') or d.get('nombre')}"[:200]
    m["From"] = os.environ.get("SMTP_FROM", NOTIFY)
    m["To"] = NOTIFY
    m["Reply-To"] = d["email"]
    m.set_content(body)
    port = int(os.environ.get("SMTP_PORT", "587"))
    if port == 465: s = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        s = smtplib.SMTP(host, port, timeout=20); s.starttls()
    if os.environ.get("SMTP_USER"): s.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
    s.send_message(m); s.quit()
    return True

def check_recaptcha(token, ip):
    secret = os.environ.get("RECAPTCHA_SECRET")
    if not secret: return True
    data = urllib.parse.urlencode({"secret": secret, "response": token or "", "remoteip": ip}).encode()
    try:
        r = json.load(urllib.request.urlopen("https://www.google.com/recaptcha/api/siteverify", data, timeout=10))
        return bool(r.get("success"))
    except Exception:
        return False

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=PUBLIC, **k)
    def log_message(self, fmt, *a): print("%s %s" % (self.address_string(), fmt % a), flush=True)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        p = self.path.split("?")[0]
        if p.startswith(("/img/", "/fonts/", "/css/", "/js/", "/video/")): self.send_header("Cache-Control", "public, max-age=604800")
        if p.startswith("/video/"): self.send_header("Accept-Ranges", "bytes")
        elif p.endswith("/") or p.endswith(".html"): self.send_header("Cache-Control", "public, max-age=300")
        super().end_headers()

    def do_GET(self):
        """Vídeo con peticiones parciales (Range): obligatorio para que Safari/iPhone lo reproduzcan."""
        rng, p = self.headers.get("Range"), self.path.split("?")[0]
        if rng and p.startswith("/video/"):
            fp = self.translate_path(p)
            m = re.match(r"bytes=(\d*)-(\d*)$", rng.strip())
            if m and os.path.isfile(fp) and (m.group(1) or m.group(2)):
                size = os.path.getsize(fp)
                a = int(m.group(1)) if m.group(1) else max(0, size - int(m.group(2)))
                b = int(m.group(2)) if (m.group(1) and m.group(2)) else size - 1
                b = min(b, size - 1)
                if a > b or a >= size:
                    self.send_response(416); self.send_header("Content-Range", f"bytes */{size}"); self.send_header("Content-Length", "0"); self.end_headers(); return
                self.send_response(206); self.send_header("Content-Type", self.guess_type(fp))
                self.send_header("Content-Range", f"bytes {a}-{b}/{size}"); self.send_header("Content-Length", str(b - a + 1)); self.end_headers()
                if self.command != "HEAD":
                    with open(fp, "rb") as f:
                        f.seek(a); left = b - a + 1
                        while left > 0:
                            chunk = f.read(min(65536, left))
                            if not chunk: break
                            self.wfile.write(chunk); left -= len(chunk)
                return
        super().do_GET()

    def send_error(self, code, message=None, explain=None):
        if code == 404 and os.path.exists(os.path.join(PUBLIC, "404.html")):
            body = open(os.path.join(PUBLIC, "404.html"), "rb").read()
            self.send_response(404); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers()
            if self.command != "HEAD": self.wfile.write(body)
        else: super().send_error(code, message, explain)

    def reply(self, code, obj, want_json):
        if want_json:
            b = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        else:
            lang = obj.get("lang", "es")
            b = f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>LCR</title><p style='font:18px system-ui;max-width:40em;margin:3em auto;padding:0 1em'>{obj.get('message','')}<br><a href='/{'' if lang=='es' else lang+'/'}'>LCR Hoteles y Apartamentos</a></p>".encode()
            self.send_response(code); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_POST(self):
        want_json = "application/json" in self.headers.get("Accept", "")
        path = self.path.split("?")[0]
        if path not in ("/api/contact", "/api/club"): return self.reply(404, {"ok": False, "message": "No encontrado"}, want_json)
        ip = self.headers.get("X-Forwarded-For", self.client_address[0]).split(",")[0].strip()
        now = time.time(); HITS[ip] = [t for t in HITS.get(ip, []) if now - t < 600] + [now]
        if len(HITS[ip]) > 8: return self.reply(429, {"ok": False, "message": "Demasiados envíos. Inténtalo más tarde."}, want_json)
        n = min(int(self.headers.get("Content-Length") or 0), 20000)
        f = {k: v[0] for k, v in urllib.parse.parse_qs(self.rfile.read(n).decode("utf-8", "ignore")).items()}
        lang = f.get("lang") if f.get("lang") in OK else "es"
        if f.get("web"):   # trampa anti-spam (campo oculto)
            return self.reply(200, {"ok": True, "lang": lang, "message": OK[lang]}, want_json)
        d = {"nombre": clean(f.get("nombre"), 120), "email": clean(f.get("email"), 160), "telefono": clean(f.get("telefono"), 40),
             "idioma": lang, "origen": clean(self.headers.get("Referer", ""), 200)}
        if path == "/api/contact":
            d.update(alojamiento=clean(f.get("alojamiento"), 60), asunto=clean(f.get("asunto"), 160), mensaje=clean(f.get("mensaje"), 4000))
            ok = d["nombre"] and EMAIL_RE.match(d["email"]) and d["asunto"] and d["mensaje"] and f.get("privacidad")
            kind = "Contacto"
        else:
            ok = d["nombre"] and EMAIL_RE.match(d["email"]) and f.get("consentimiento") and f.get("privacidad")
            kind = "Alta Club LCR"
        if not ok: return self.reply(400, {"ok": False, "lang": lang, "message": "Revisa los campos obligatorios."}, want_json)
        if not check_recaptcha(f.get("g-recaptcha-response"), ip): return self.reply(400, {"ok": False, "lang": lang, "message": "reCAPTCHA"}, want_json)
        try: send_mail(kind, d)
        except Exception as e:
            print("ERROR enviando email:", e, flush=True)
            return self.reply(502, {"ok": False, "lang": lang, "message": "No se pudo enviar. Escribe a " + NOTIFY}, want_json)
        self.reply(200, {"ok": True, "lang": lang, "message": OK[lang]}, want_json)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"LCR web en http://0.0.0.0:{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
