"""Magazinele scanate. Pentru a adauga un magazin nou, copiaza un bloc si ajusteaza selectorii CSS.

Selectori (title, link, image, price, old_price): "css" = textul elementului, "css@attr" = atribut, "@attr" = atribut pe card,
"a || b" = primul care exista. {q} = termen cu '+', {qp} = termen cu '%20'.
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
        "id": "dedeman", "name": "Dedeman", "base": "https://www.dedeman.ro", "type": "html",
        "search": "https://www.dedeman.ro/ro/catalogsearch/result/?q={q}",
        "card": "div.product-item",
        "title": "img.product-image-photo@alt || .product-item-link",
        "link": "a.product-item-photo@href",
        "image": "img.product-image-photo@src",
        "price": "[data-price-type=finalPrice]@data-price-amount || .special-price .price || .price",
        "old_price": "[data-price-type=oldPrice]@data-price-amount || .old-price .price",
    },
    {
        "id": "carrefour", "name": "Carrefour", "base": "https://carrefour.ro", "type": "html",
        "search": "https://carrefour.ro/catalogsearch/result/?q={q}",
        "card": "li.product[data-product-id]",
        "title": "img.product-image-photo@alt",
        "link": "a.productItem-image@href",
        "image": "img.product-image-photo@data-src",
        "price": "meta[itemprop=price]@content || .price-final@data-price-amount",
        "old_price": "[data-price-type=oldPrice]@data-price-amount || .old-price .price || .price-old",
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
    {
        "id": "dacris", "name": "Dacris", "base": "https://www.dacris.net", "type": "vtex",
        "search": "https://www.dacris.net/api/catalog_system/pub/products/search?ft={qp}&_from=0&_to=39",
    },
]
