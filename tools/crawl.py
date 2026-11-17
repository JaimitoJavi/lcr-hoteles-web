import json, re, sys, urllib.request, ssl
from html.parser import HTMLParser

SC = "/private/tmp/claude-501/-Users-jaimelacruzsisamon-Desktop-AI-for-Startup/e7ef2f09-5a4d-476b-8e8e-ab2f1b87ac31/scratchpad"
urls = [u.strip() for u in open(SC + "/urls.txt") if u.strip() and "/category/" not in u]

class P(HTMLParser):
    def __init__(s):
        super().__init__()
        s.items = []; s.skip = 0; s.tag = None; s.buf = ""; s.title = ""; s.desc = ""; s.imgs = []; s.intitle = False
        s.main = False
    def handle_starttag(s, t, a):
        a = dict(a)
        if t in ("script", "style", "noscript", "svg", "nav", "footer", "header", "form"): s.skip += 1
        if t == "title": s.intitle = True
        if t == "meta" and a.get("name") == "description": s.desc = a.get("content", "")
        if t == "img":
            src = a.get("data-src") or a.get("src") or ""
            if src and not src.startswith("data:") and "uploads" in src:
                s.imgs.append({"src": src, "alt": a.get("alt", "")})
        if t in ("h1", "h2", "h3", "h4", "p", "li", "a", "span", "div") and s.skip == 0:
            pass
        if t in ("h1", "h2", "h3", "h4", "p", "li"):
            s.flush(); s.tag = t
    def handle_endtag(s, t):
        if t in ("script", "style", "noscript", "svg", "nav", "footer", "header", "form") and s.skip: s.skip -= 1
        if t == "title": s.intitle = False
        if t in ("h1", "h2", "h3", "h4", "p", "li"): s.flush()
    def handle_data(s, d):
        if s.intitle: s.title += d
        elif s.skip == 0 and s.tag: s.buf += d
        elif s.skip == 0:
            t = re.sub(r"\s+", " ", d).strip()
            if len(t) >= 40: s.items.append(["p", t])
    def flush(s):
        txt = re.sub(r"\s+", " ", s.buf).strip()
        if txt and s.tag: s.items.append([s.tag, txt])
        s.buf = ""; s.tag = None

ctx = ssl.create_default_context()
out = {}
for u in urls:
    try:
        import subprocess
        html = subprocess.run(["curl", "-sL", "-m", "30", "-A", "Mozilla/5.0", u], capture_output=True).stdout.decode("utf-8", "ignore")
        if not html: raise Exception("vacío")
        p = P(); p.feed(html)
        seen = set(); imgs = []
        for i in p.imgs:
            if i["src"] not in seen: seen.add(i["src"]); imgs.append(i)
        out[u] = {"title": p.title.strip(), "desc": p.desc, "items": p.items, "imgs": imgs}
        print("ok", u, len(p.items), len(imgs))
    except Exception as e:
        print("ERR", u, e)
json.dump(out, open(SC + "/crawl.json", "w"), ensure_ascii=False, indent=1)
