"""Scaneaza magazinele online din Romania si salveaza ofertele in docs/data/.

Rulare:  python scraper/scrape.py
Test:    python scraper/scrape.py --magazine emag --cautari "iphone 15"   (nu salveaza nimic)
Respecta robots.txt pentru fiecare magazin si face pauze intre cereri.
"""
import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote, quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from stores import STORES

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
BOT_NAME = "OferteRoBot"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.5",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}
ISTORIC_ZILE = 60

session = requests.Session()
session.headers.update(HEADERS)
_robots = {}


def parse_robots(text):
    """Grupurile din robots.txt: [{"agents": [...], "rules": [(allow, pattern)]}]."""
    groups, cur, in_agents = [], None, False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, val = (x.strip() for x in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if not in_agents:
                cur = {"agents": [], "rules": []}
                groups.append(cur)
            cur["agents"].append(val.lower())
            in_agents = True
            continue
        in_agents = False
        if key in ("allow", "disallow") and cur is not None and val:
            cur["rules"].append((key == "allow", val))
    return groups


def robots_allows(groups, path):
    """Regula cea mai lunga castiga (cu * si $), ca la Google; urllib.robotparser nu stie wildcard-uri."""
    agent = BOT_NAME.lower()
    mine = [g for g in groups if any(a != "*" and a in agent for a in g["agents"])]
    rules = [r for g in (mine or [g for g in groups if "*" in g["agents"]]) for r in g["rules"]]
    best = None
    for allow, pat in rules:
        rx = "^" + re.escape(pat).replace(r"\*", ".*").replace(r"\$", "$")
        if re.match(rx, path) and (best is None or len(pat) > len(best[1]) or (len(pat) == len(best[1]) and allow)):
            best = (allow, pat)
    return best is None or best[0]


def allowed(url):
    """Verifica robots.txt (cache per domeniu)."""
    parts = urlparse(url)
    base = f"{parts.scheme}://{parts.netloc}"
    if base not in _robots:
        try:
            r = session.get(base + "/robots.txt", timeout=15)
            _robots[base] = parse_robots(r.text) if r.status_code == 200 else []
        except requests.RequestException:
            _robots[base] = []
    return robots_allows(_robots[base], parts.path + ("?" + parts.query if parts.query else ""))


def parse_price(text):
    """'3.664,99 Lei' / '3.664 , 99 Lei' / '3784' / '71.99' -> float."""
    if text is None:
        return None
    t = re.sub(r"[^\d.,]", "", str(text).replace("\xa0", ""))
    if not t:
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif t.count(".") > 1 or re.search(r"\.\d{3}$", t):
        t = t.replace(".", "")
    try:
        v = float(t)
    except ValueError:
        return None
    return v if v > 0 else None


def fetch(url, as_json=False):
    if not allowed(url):
        raise PermissionError("blocat de robots.txt")
    for attempt in range(3):
        try:
            r = session.get(url, timeout=30)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                raise requests.ConnectionError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r.json() if as_json else r.text
        except (requests.ConnectionError, requests.Timeout):
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))


# ---------- extractoare ----------

def _pick(el, spec):
    """spec: 'selector' sau 'selector@attr' sau '@attr' (pe card)."""
    if not spec:
        return None
    for one in spec.split("||"):
        sel, _, attr = one.strip().partition("@")
        node = el.select_one(sel) if sel else el
        if node is None:
            continue
        val = node.get(attr) if attr else node.get_text(" ", strip=True)
        if val:
            return val.strip()
    return None


def extract_html(store, html, base_url):
    s = BeautifulSoup(html, "html.parser")
    out = []
    for card in s.select(store["card"]):
        name = _pick(card, store["title"])
        link = _pick(card, store["link"])
        price = parse_price(_pick(card, store["price"]))
        if not (name and link and price):
            continue
        if re.search(r"stoc epuizat|indisponibil|nu mai este disponibil", card.get_text(" ", strip=True), re.I):
            continue
        old = parse_price(_pick(card, store.get("old_price")))
        img = _pick(card, store.get("image"))
        out.append({
            "nume": re.sub(r"\s+", " ", name),
            "url": urljoin(base_url, link),
            "pret": price,
            # pret vechi de >5x pretul curent = aproape sigur eroare de citire
            "pret_vechi": old if old and price < old < price * 5 else None,
            "imagine": urljoin(base_url, img) if img and not img.startswith("data:") else None,
        })
    return out


def extract_vtex(store, data, base_url):
    out = []
    for p in data:
        try:
            item = p["items"][0]
            offer = item["sellers"][0]["commertialOffer"]
        except (KeyError, IndexError):
            continue
        price = offer.get("Price")
        if not price or not offer.get("AvailableQuantity", 1):
            continue
        old = max(offer.get("ListPrice") or 0, offer.get("PriceWithoutDiscount") or 0)
        cats = p.get("categories") or []
        out.append({
            "nume": p.get("productName"),
            "url": p.get("link"),
            "pret": float(price),
            "pret_vechi": float(old) if old > price else None,
            "imagine": (item.get("images") or [{}])[0].get("imageUrl"),
            "categorie": cats[0].strip("/").split("/")[-1] if cats else None,
        })
    return out


def extract_product_page(html, url):
    """Pagina unui singur produs: JSON-LD Product, apoi meta/atribute de pret uzuale."""
    s = BeautifulSoup(html, "html.parser")
    name = price = img = None
    for sc in s.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(sc.string or "")
        except ValueError:
            continue
        for x in data if isinstance(data, list) else [data]:
            if isinstance(x, dict) and x.get("@type") == "Product":
                offers = x.get("offers") or {}
                offers = offers[0] if isinstance(offers, list) and offers else offers
                name, price = x.get("name"), parse_price(offers.get("price") if isinstance(offers, dict) else None)
                img = x.get("image")[0] if isinstance(x.get("image"), list) else x.get("image")
    name = name or _pick(s, "meta[property='og:title']@content || h1")
    price = price or parse_price(_pick(s, "meta[itemprop=price]@content || [data-price-type=finalPrice]@data-price-amount"
                                          " || [data-price]@data-price"))
    if price is None:
        m = re.search(r'"price"\s*:\s*"?([\d.]+)', html)
        price = parse_price(m.group(1)) if m else None
    if not (name and price):
        return None
    # produsele epuizate raman pe site cu pret, dar nu se pot cumpara (si ar da alerte false)
    stock = _pick(s, "[itemprop=availability]@href || [itemprop=availability]@content") or ""
    if re.search(r"OutOfStock|SoldOut|Discontinued", stock, re.I) or re.search(r'"availability"\s*:\s*"[^"]*OutOfStock', html):
        return None
    old = parse_price(_pick(s, "[data-price-type=oldPrice]@data-price-amount"))
    img = img or _pick(s, "meta[property='og:image']@content")
    return {"nume": re.sub(r"\s+", " ", name).strip(), "url": url, "pret": price,
            "pret_vechi": old if old and price < old < price * 5 else None, "imagine": img}


def product_links(store):
    """Linkurile de produs din paginile de listare sau din sitemap-urile magazinului."""
    rx = re.compile(store["link_regex"], re.I)
    links = []
    for src in store["listing"]:
        text = fetch(src)
        found = re.findall(r"<loc>([^<]+)</loc>", text) if src.endswith(".xml") else re.findall(r'href="([^"]+)"', text)
        for href in found:
            u = urljoin(store["base"], href.replace("&amp;", "&"))
            if rx.search(u) and u not in links:
                links.append(u)
    return links


def scrape_pages(store, pause):
    out = []
    for url in product_links(store):
        try:
            item = extract_product_page(fetch(url), url)
        except (requests.RequestException, PermissionError):
            item = None
        if item:
            out.append(item)
        time.sleep(pause)
    return out


def scrape_store(store, term, limit):
    url = store["search"].format(q=quote_plus(term), qp=quote(term))
    if store["type"] == "vtex":
        items = extract_vtex(store, fetch(url, as_json=True), store["base"])
    else:
        items = extract_html(store, fetch(url), store["base"])
    words = [w for w in re.split(r"\s+", term.lower()) if len(w) > 1]
    # magazinele returneaza si "recomandari"; pastram doar produsele care contin toate cuvintele cautate
    return [i for i in items if all(w in i["nume"].lower() for w in words)][:limit]


# ---------- main ----------

def pid(url):
    return hashlib.md5(url.split("?")[0].encode()).hexdigest()[:12]


def norm(s):
    return unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode()


def passes_filter(name, flt):
    """Filtrul din config.json: incepe_cu / contine_unul / exclude (oricare poate lipsi)."""
    n = norm(name).strip()
    if flt.get("incepe_cu") and not any(n.startswith(norm(w)) for w in flt["incepe_cu"]):
        return False
    if flt.get("contine_unul") and not any(norm(w) in n for w in flt["contine_unul"]):
        return False
    return not any(norm(w) in n for w in flt.get("exclude", []))


def check_alert(produse, prag):
    """Scrie alerta.txt (pentru email) cu produsele sub prag care nu au mai fost anuntate la acest pret."""
    vechi = load_json(DATA / "alerte.json", {})
    sub = {p["id"]: p for p in produse if p["pret"] < prag}
    noi = [p for k, p in sub.items() if k not in vechi or p["pret"] < vechi[k]]
    # tinem minte doar ce e inca sub prag, ca o scadere viitoare sub prag sa fie anuntata din nou
    (DATA / "alerte.json").write_text(json.dumps({k: p["pret"] for k, p in sub.items()}), encoding="utf-8")
    alert_file = ROOT / "alerta.txt"
    if not noi:
        alert_file.unlink(missing_ok=True)
        return
    noi.sort(key=lambda p: p["pret"])
    lines = [f"Am gasit {len(noi)} oferte sub {prag:g} lei:", ""]
    for p in noi:
        lines += [f"{p['pret']:.2f} lei - {p['nume']} ({p['magazin']})", p["url"], ""]
    lines.append("Toate ofertele: https://marius205099.github.io/oferte/")
    subject = f"PS5 sub {prag:g} lei: {noi[0]['pret']:.2f} lei la {noi[0]['magazin']}"
    alert_file.write_text(subject + "\n" + "\n".join(lines), encoding="utf-8")
    print(f"ALERTA: {len(noi)} oferte noi sub {prag:g} lei")


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--magazine", help="lista separata prin virgula (implicit: toate)")
    ap.add_argument("--cautari", help="lista separata prin virgula (implicit: din config.json)")
    args = ap.parse_args()

    cfg = load_json(ROOT / "config.json", {})
    terms = [t.strip() for t in args.cautari.split(",")] if args.cautari else cfg.get("cautari", [])
    limit = cfg.get("rezultate_per_cautare", 30)
    pause = cfg.get("pauza_intre_cereri_sec", 2)
    flt = cfg.get("filtru", {})
    prag = (cfg.get("alerta") or {}).get("pret_sub")
    stores = STORES
    if args.magazine:
        keep = {m.strip() for m in args.magazine.split(",")}
        stores = [s for s in STORES if s["id"] in keep]

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    DATA.mkdir(parents=True, exist_ok=True)
    istoric = load_json(DATA / "istoric.json", {})
    produse, stare = {}, []

    for store in stores:
        ok = err = 0
        last_err = None
        pages = store["type"] == "pages"
        # magazinele "pages" nu au cautare permisa: citim o data paginile de produs gasite in listare/sitemap
        for term in (terms[:1] if pages else terms):
            try:
                items = scrape_pages(store, pause) if pages else scrape_store(store, term, limit)
                ok += 1
            except Exception as e:  # noqa: BLE001 - un magazin picat nu opreste scanarea
                err += 1
                last_err = f"{type(e).__name__}: {e}"[:160]
                items = []
                if isinstance(e, PermissionError):
                    break
            for it in items:
                if not passes_filter(it["nume"], flt):
                    continue
                key = pid(it["url"])
                prev = produse.get(key)
                if prev:
                    if term not in prev["cautari"]:
                        prev["cautari"].append(term)
                    continue
                it.update(id=key, magazin=store["id"], cautari=[term])
                produse[key] = it
            time.sleep(pause)
        found = sum(1 for p in produse.values() if p["magazin"] == store["id"])
        print(f"{store['name']:<14} cautari ok={ok} erori={err} produse={found}" + (f"  ({last_err})" if last_err else ""))
        stare.append({"id": store["id"], "nume": store["name"], "url": store["base"],
                      "produse": found, "erori": err, "ultima_eroare": last_err})

    # istoric preturi + reducere calculata si din istoric (cand magazinul nu afiseaza pretul vechi)
    cutoff = (now - timedelta(days=ISTORIC_ZILE)).strftime("%Y-%m-%d")
    for key, p in produse.items():
        h = [x for x in istoric.get(key, []) if x[0] >= cutoff and x[0] != today]
        h.append([today, p["pret"]])
        istoric[key] = h
        prices = [x[1] for x in h]
        p["pret_minim_60z"] = min(prices)
        p["zile_istoric"] = len(h)
        ref = p["pret_vechi"]
        if not ref and len(h) > 1:
            maxp = max(prices[:-1])
            if maxp > p["pret"] * 1.03:
                ref = maxp
                p["sursa_reducere"] = "istoric"
        p["reducere_pct"] = round((1 - p["pret"] / ref) * 100) if ref else 0
        p["pret_referinta"] = ref
    istoric = {k: v for k, v in istoric.items() if v and v[-1][0] >= cutoff}

    rezultat = {
        "actualizat": now.isoformat(timespec="minutes"),
        "magazine": stare,
        "cautari": terms,
        "alerta_pret": prag,
        "produse": sorted(produse.values(), key=lambda p: p["pret"]),
    }
    if args.magazine or args.cautari:
        for p in rezultat["produse"][:15]:
            print(f"  -{p['reducere_pct']:>2}%  {p['pret']:>9.2f}  {p['magazin']:<9} {p['nume'][:70]}")
        print(f"Test: {len(produse)} produse (nu s-a salvat nimic).")
        return
    if not produse:
        print("Nu s-a gasit niciun produs; datele vechi raman neschimbate.")
        sys.exit(1)
    (DATA / "oferte.json").write_text(json.dumps(rezultat, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (DATA / "istoric.json").write_text(json.dumps(istoric, separators=(",", ":")), encoding="utf-8")
    if prag:
        check_alert(rezultat["produse"], prag)
    reduse = sum(1 for p in produse.values() if p["reducere_pct"] > 0)
    print(f"Total: {len(produse)} produse, {reduse} cu reducere.")


if __name__ == "__main__":
    main()
