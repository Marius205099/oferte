"""Magazinele scanate. Pentru a adauga un magazin nou, copiaza un bloc si ajusteaza.

Tipuri:
- "html":  pagina de cautare a magazinului; selectori CSS (title, link, image, price, old_price):
           "css" = textul elementului, "css@attr" = atribut, "@attr" = atribut pe card, "a || b" = primul care exista.
           {q} = termen cu '+', {qp} = termen cu '%20'.
- "vtex":  API-ul public de cautare al magazinelor pe platforma VTEX (Auchan, Kaufland etc.).
- "pages": cand robots.txt interzice cautarea: linkurile de produs se iau din paginile "listing"
           (o categorie sau un sitemap .xml) si se pastreaza cele care se potrivesc cu "link_regex";
           pretul se citeste din pagina fiecarui produs.
Robots.txt e verificat automat la fiecare cerere; magazinele care il interzic sunt sarite.

Nu se pot scana (blocheaza programele automate): Altex, Media Galaxy, Flanco, Vexio, Trendyol, Okazii.
Interzic scanarea in robots.txt: PC Garage, CEL.ro.
"""

STORES = [
    {
        "id": "emag", "name": "eMAG", "base": "https://www.emag.ro", "type": "html",
        "search": "https://www.emag.ro/search/{q}",
        "card": "div.card-item[data-name]",
        "title": "@data-name",
        "link": "@data-url",
        "image": "img@src",
        "price": ".product-new-price",
        "old_price": ".product-old-price s || .rrp-lp30d s || .product-old-price",
    },
    {
        "id": "evomag", "name": "evoMAG", "base": "https://www.evomag.ro", "type": "pages",
        "listing": [
            "https://www.evomag.ro/componente-pc-gaming-gaming-console/filtru/platforma:playstation+5",
            "https://www.evomag.ro/componente-pc-gaming-gaming-console/filtru/platforma:playstation+5+pro",
        ],
        "link_regex": r"/componente-pc-gaming-gaming-console/.+\.html$",
    },
    {
        # cautarea (/catalogsearch) e interzisa in robots.txt; folosim sitemap-ul public de produse
        "id": "carrefour", "name": "Carrefour", "base": "https://carrefour.ro", "type": "pages",
        "listing": [
            "https://carrefour.ro/pub/sitemap/sitemap_001.xml",
            "https://carrefour.ro/pub/sitemap/sitemap_002.xml",
        ],
        "link_regex": r"/produse/consola-[^/]*(playstation-5|ps5)",
    },
    {
        "id": "itgalaxy", "name": "iTGalaxy", "base": "https://www.itgalaxy.ro", "type": "html",
        "search": "https://www.itgalaxy.ro/cauta/?q={q}",
        "card": "div.product-item",
        "title": "h2.name a@title",
        "link": "h2.name a@href",
        "image": "img@src",
        "price": ".price",
        "old_price": ".old-price",
    },
    {
        "id": "auchan", "name": "Auchan", "base": "https://www.auchan.ro", "type": "vtex",
        "search": "https://www.auchan.ro/api/catalog_system/pub/products/search?ft={qp}&_from=0&_to=39",
    },
]
