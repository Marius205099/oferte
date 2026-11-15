# Oferte RO

Site care adună reducerile din magazinele online din România și compară prețurile pentru un produs.
Se actualizează automat o dată pe zi, la 03:00 ora României, prin GitHub Actions și e publicat pe GitHub Pages.

## Cum funcționează

- `scraper/scrape.py` caută fiecare termen din `config.json` în fiecare magazin din `scraper/stores.py`
  și salvează rezultatele în `docs/data/oferte.json`. Respectă `robots.txt` și face pauze între cereri.
- Reducerea vine din prețul vechi afișat de magazin. Dacă magazinul nu afișează unul, se folosește cel mai mare preț
  văzut de noi în ultimele 60 de zile (`docs/data/istoric.json`).
- `docs/` e site-ul static: căutare, filtre pe magazin, categorie, reducere și preț, plus comparația „cel mai mic preț pe magazin”.

## Urmărește alte produse

Editează lista `cautari` din `config.json` (direct pe GitHub, cu creionul). Scanarea următoare le va include.
Poți porni scanarea manual din tab-ul **Actions → Scanare oferte → Run workflow**.

## Adaugă un magazin

Copiază un bloc din `scraper/stores.py` și ajustează selectorii CSS. Testează fără să salvezi nimic:

```bash
python scraper/scrape.py --magazine emag --cautari "iphone 15"
```

Magazinele pe VTEX (Auchan, Dacris etc.) au tipul `vtex` și nu au nevoie de selectori.

## Limitări

Multe magazine (Altex, Flanco, PC Garage, Notino, Elefant, Decathlon etc.) blochează roboții sau interzic scanarea
în `robots.txt`, așa că nu sunt incluse. Pentru acoperire completă, varianta corectă sunt feed-urile de produse din
rețelele de afiliere (2Performant, Profitshare), pe care se bazează și comparatoarele mari.
