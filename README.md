# Oferte RO

Site care urmărește prețurile consolelor PlayStation 5 în magazinele online din România, sortate de la cel mai mic preț,
și trimite un email când o consolă scade sub pragul din `config.json` (`alerta.pret_sub`, acum 3500 lei).
Se actualizează automat o dată pe zi, la 03:00 ora României, prin GitHub Actions și e publicat pe GitHub Pages.

## Cum funcționează

- `scraper/scrape.py` caută fiecare termen din `config.json` în fiecare magazin din `scraper/stores.py`
  și salvează rezultatele în `docs/data/oferte.json`. Respectă `robots.txt` și face pauze între cereri.
- Reducerea vine din prețul vechi afișat de magazin. Dacă magazinul nu afișează unul, se folosește cel mai mare preț
  văzut de noi în ultimele 60 de zile (`docs/data/istoric.json`).
- `docs/` e site-ul static: căutare, filtre pe magazin, categorie, reducere și preț, plus comparația „cel mai mic preț pe magazin”.

## Alerta pe email

Pasul „Trimite alerta pe email” din workflow folosește trei secrete (Settings → Secrets and variables → Actions):
`SMTP_USER` (adresa Yahoo), `SMTP_PASS` (o *parolă de aplicație* Yahoo, nu parola contului) și `EMAIL_TO`.
O ofertă e anunțată o singură dată, apoi din nou doar dacă prețul scade și mai mult.

## Urmărește alte produse

Editează lista `cautari` și `filtru` din `config.json` (direct pe GitHub, cu creionul). Scanarea următoare le va include.
Poți porni scanarea manual din tab-ul **Actions → Scanare oferte → Run workflow**.

## Adaugă un magazin

Copiază un bloc din `scraper/stores.py` și ajustează selectorii CSS. Testează fără să salvezi nimic:

```bash
python scraper/scrape.py --magazine emag --cautari "iphone 15"
```

Magazinele pe VTEX (Auchan, Dacris etc.) au tipul `vtex` și nu au nevoie de selectori.

## Limitări

- **Magazine scanate:** eMAG, evoMAG, Carrefour, iTGalaxy, Auchan. Produsele epuizate sunt ignorate.
- **Altex, Media Galaxy, Flanco, Vexio, Trendyol** blochează programele automate, iar **PC Garage și CEL.ro** interzic
  scanarea în `robots.txt`, așa că nu sunt incluse. Google interzice și el căutările automate.
  Varianta corectă pentru aceste magazine sunt feed-urile de produse din rețelele de afiliere (2Performant, Profitshare).
- GitHub poate întârzia rulările programate cu până la o oră.
