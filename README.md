# Casa Mar y Sol – Spain Holiday Home Site + Booking (Flask)

Complete marketing site + reserveringssysteem:
- Home (hero, highlights, reviews, CTA)
- Foto's (gallery + lightbox)
- Faciliteiten
- Omgeving (kaart placeholder)
- Contact (flash bevestiging)
- Beschikbaarheid (kalender + boekingsaanvraag)
- Meertalig: NL / EN / ES (via /lang/<code>)
- SEO: OpenGraph + JSON-LD + sitemap.xml + robots.txt
- Deploy: Dockerfile, Procfile, render.yaml

## Snel starten (lokaal)
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Ga naar http://127.0.0.1:5000

## Admin
De eerste geregistreerde gebruiker krijgt admin-rechten en kan naar `/admin/bookings`.

## Aanpassen
- Teksten/taal: in `app.py` (STRINGS dict)
- Foto's: vervang SVG's in `static/img/` door eigen beelden
- Kleuren/stijl: `static/css/brand.css` en `static/css/theme_airbnb.css`
