from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, Response, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
import calendar, os, smtplib, ssl, json

from models import db, User, Booking
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- i18n (simple) ---
LANGS = ["nl", "en", "es"]
STRINGS = {
  "nl": {
    "brand": "Casa Mar y Sol",
    "tagline": "Zonnig vakantiehuis aan de Costa",
    "cta_book": "Bekijk beschikbaarheid",
    "nav_home": "Home",
    "nav_gallery": "Foto's",
    "nav_amen": "Faciliteiten",
    "nav_area": "Omgeving",
    "nav_contact": "Contact",
    "nav_availability": "Beschikbaarheid",
    "hero_sub": "Een lichte, ruime casa met dakterras, privé-parking en op loopafstand van het strand.",
    "amen_title": "Faciliteiten",
    "amen_list": ["3 slaapkamers (6p)", "2 badkamers", "Volledig uitgeruste keuken", "Airco & snelle Wi‑Fi", "Privé-parking", "Dakterras met BBQ"],
    "area_title": "Ontdek de omgeving",
    "reviews_title": "Ervaringen van gasten",
    "contact_title": "Contact",
    "contact_note": "Stel je vraag of informeer naar speciale wensen. We reageren meestal dezelfde dag.",
    "form_name": "Naam",
    "form_email": "E‑mail",
    "form_msg": "Bericht",
    "form_send": "Versturen",
    "foot_small": "© Casa Mar y Sol – Alle rechten voorbehouden",
    "avail_title": "Beschikbaarheid & reserveren",
  },
  "en": {
    "brand": "Casa Mar y Sol",
    "tagline": "Sunny holiday home by the coast",
    "cta_book": "Check availability",
    "nav_home": "Home",
    "nav_gallery": "Photos",
    "nav_amen": "Amenities",
    "nav_area": "Area",
    "nav_contact": "Contact",
    "nav_availability": "Availability",
    "hero_sub": "Bright and spacious casa with rooftop terrace, private parking and a short walk to the beach.",
    "amen_title": "Amenities",
    "amen_list": ["3 bedrooms (sleeps 6)", "2 bathrooms", "Fully equipped kitchen", "Air‑conditioning & fast Wi‑Fi", "Private parking", "Rooftop terrace with BBQ"],
    "area_title": "Explore the area",
    "reviews_title": "Guest reviews",
    "contact_title": "Contact",
    "contact_note": "Ask anything or tell us your wishes. We typically reply the same day.",
    "form_name": "Name",
    "form_email": "Email",
    "form_msg": "Message",
    "form_send": "Send",
    "foot_small": "© Casa Mar y Sol – All rights reserved",
    "avail_title": "Availability & booking",
  },
  "es": {
    "brand": "Casa Mar y Sol",
    "tagline": "Casa vacacional soleada cerca de la costa",
    "cta_book": "Ver disponibilidad",
    "nav_home": "Inicio",
    "nav_gallery": "Fotos",
    "nav_amen": "Servicios",
    "nav_area": "Zona",
    "nav_contact": "Contacto",
    "nav_availability": "Disponibilidad",
    "hero_sub": "Casa luminosa y amplia con azotea, parking privado y a pocos minutos de la playa.",
    "amen_title": "Servicios",
    "amen_list": ["3 dormitorios (6 pax)", "2 baños", "Cocina totalmente equipada", "Aire acondicionado y Wi‑Fi rápido", "Parking privado", "Azotea con barbacoa"],
    "area_title": "Descubre la zona",
    "reviews_title": "Opiniones de huéspedes",
    "contact_title": "Contacto",
    "contact_note": "Pregúntanos lo que quieras o comenta tus preferencias. Suelenos responder el mismo día.",
    "form_name": "Nombre",
    "form_email": "Email",
    "form_msg": "Mensaje",
    "form_send": "Enviar",
    "foot_small": "© Casa Mar y Sol – Todos los derechos reservados",
    "avail_title": "Disponibilidad y reserva",
  }
}

def t(key):
    lang = session.get("lang", "nl")
    return STRINGS.get(lang, STRINGS["nl"]).get(key, key)

@app.context_processor
def inject_globals():
    return dict(t=t, current_lang=session.get("lang", "nl"), langs=LANGS, config=app.config)

@app.route("/lang/<code>")
def set_lang(code):
    if code not in LANGS:
        abort(404)
    session["lang"] = code
    return redirect(request.referrer or url_for("home"))

# ---- Auth/models helpers & queries ----
from flask_login import user_loaded_from_cookie
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

def overlap_exists(start_date: date, end_date: date) -> bool:
    from models import Booking
    conflict = Booking.query.filter(
        Booking.status == "approved",
        Booking.start_date <= end_date,
        Booking.end_date >= start_date
    ).first()
    return conflict is not None

def nights_in_range(a_start: date, a_end: date, b_start: date, b_end: date) -> int:
    start = max(a_start, b_start); end = min(a_end, b_end)
    return 0 if start > end else (end - start).days + 1

def user_nights_in_month(user_id: int, year: int, month: int) -> int:
    from models import Booking
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    total = 0
    bookings = Booking.query.filter_by(user_id=user_id, status="approved").all()
    for b in bookings:
        total += nights_in_range(b.start_date, b.end_date, month_start, month_end)
    return total

# ---- Booking JSON + ICS (reuse from previous version) ----
from flask import jsonify
@app.route('/reserve/calendar.json')
def calendar_feed():
    events = []
    all_bookings = Booking.query.filter(Booking.status == "approved").all()
    for b in all_bookings:
        end_excl = b.end_date + timedelta(days=1)
        color = b.user.color if b.user and b.user.color else "#FF385C"
        events.append({
            "id": b.id,
            "title": f"{b.user.name if b.user else 'Reservering'}",
            "start": b.start_date.isoformat(),
            "end": end_excl.isoformat(),
            "allDay": True,
            "backgroundColor": color,
            "borderColor": color
        })
    return jsonify(events)

@app.route('/reserve/calendar.ics')
def calendar_ics():
    from models import Booking
    lines = ["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//CasaMarYSol//NL//EN"]
    bookings = Booking.query.filter(Booking.status == "approved").all()
    for b in bookings:
        dtstart = b.start_date.strftime("%Y%m%d")
        dtend = (b.end_date + timedelta(days=1)).strftime("%Y%m%d")
        summary = f"{b.user.name if b.user else 'Reservering'}"
        uid = f"booking-{b.id}@casamarysol"
        lines += ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
                  f"DTSTART;VALUE=DATE:{dtstart}", f"DTEND;VALUE=DATE:{dtend}", f"SUMMARY:{summary}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    ics = "\r\n".join(lines)
    return Response(ics, mimetype='text/calendar')

# ---- Marketing pages ----

@app.route("/")
def home():
    return render_template("home.html", reviews=[
        {"name": "Sanne", "stars": 5, "text": "Heerlijk huis met fijn dakterras. Strand en winkels om de hoek!"},
        {"name": "Miguel", "stars": 5, "text": "Muy cómodo y limpio. Comunicación perfecta."},
        {"name": "Laura", "stars": 4, "text": "Ruime kamers en top locatie. We komen graag terug."}
    ])

@app.route("/gallery")
def gallery():
    imgs = [f"/static/img/photo_{i}.svg" for i in range(1,10)]
    return render_template("gallery.html", images=imgs)

@app.route("/amenities")
def amenities():
    return render_template("amenities.html")

@app.route("/area")
def area():
    return render_template("area.html")

@app.route("/contact", methods=["GET","POST"])
def contact():
    if request.method == "POST":
        # In real deploy, integrate email service; here we just flash success.
        flash("Je bericht is verzonden. We nemen snel contact met je op.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")

# ---- Booking UI & auth (under /reserve) ----
from flask_login import login_required

@app.route("/reserve")
def availability():
    return render_template("availability.html")

@app.route("/register", methods=['GET','POST'])
def register():
    from models import User, db
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        color = request.form.get('color') or "#FF385C"
        if not name or not email or not password:
            flash('Vul alle velden in.', 'danger'); return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('E-mailadres is al geregistreerd.', 'warning'); return redirect(url_for('register'))
        user = User(name=name, email=email, password_hash=generate_password_hash(password), color=color)
        if User.query.count() == 0: user.is_admin = True
        db.session.add(user); db.session.commit()
        flash('Account aangemaakt. Je kunt nu inloggen.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route("/login", methods=['GET','POST'])
def login():
    from models import User
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash('Onjuiste inloggegevens.', 'danger'); return redirect(url_for('login'))
        login_user(user); flash('Welkom terug!', 'success'); return redirect(url_for('availability'))
    return render_template('login.html')

@app.route("/logout")
@login_required
def logout():
    logout_user(); flash('Je bent uitgelogd.', 'info')
    return redirect(url_for('home'))

@app.route('/reserve/book', methods=['POST'])
@login_required
def book():
    from models import Booking, db
    try:
        start_str = request.form.get('start_date'); end_str = request.form.get('end_date')
        note = request.form.get('note','').strip()
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
    except Exception:
        flash('Ongeldige data.', 'danger'); return redirect(url_for('availability'))
    if start_date > end_date:
        flash('Startdatum mag niet na einddatum liggen.', 'warning'); return redirect(url_for('availability'))
    latest_allowed = add_months(date.today(), app.config['ADVANCE_BOOKING_MONTHS'])
    if start_date > latest_allowed:
        flash(f'Maximaal {app.config["ADVANCE_BOOKING_MONTHS"]} maanden vooruit boeken.', 'warning'); return redirect(url_for('availability'))
    if overlap_exists(start_date, end_date):
        flash('Deze periode overlapt met een bestaande (goedgekeurde) reservering.', 'danger'); return redirect(url_for('availability'))
    # per-maand limieten t.o.v. approved nachten
    check_date = date(start_date.year, start_date.month, 1)
    while check_date <= end_date:
        y, m = check_date.year, check_date.month
        from calendar import monthrange
        month_start = date(y,m,1); month_end = date(y,m,monthrange(y,m)[1])
        from_user = user_nights_in_month(current_user.id, y, m)
        add_n = nights_in_range(start_date, end_date, month_start, month_end)
        if from_user + add_n > app.config['MAX_NIGHTS_PER_MONTH']:
            flash(f'Max {app.config["MAX_NIGHTS_PER_MONTH"]} nachten in {y}-{m:02d}.', 'warning'); return redirect(url_for('availability'))
        check_date = date(y+1,1,1) if m==12 else date(y,m+1,1)
    b = Booking(user_id=current_user.id, start_date=start_date, end_date=end_date, note=note, status="pending")
    db.session.add(b); db.session.commit()
    flash('Aanvraag verstuurd. Wacht op goedkeuring door admin.', 'success')
    return redirect(url_for('availability'))

# Admin
from flask_login import login_required
from functools import wraps

def require_admin():
    if not current_user.is_authenticated or not current_user.is_admin: abort(403)

@app.route('/admin/bookings')
@login_required
def admin_bookings():
    require_admin()
    pend = Booking.query.filter_by(status="pending").order_by(Booking.created_at.asc()).all()
    appr = Booking.query.filter_by(status="approved").order_by(Booking.start_date.asc()).all()
    decl = Booking.query.filter_by(status="declined").order_by(Booking.start_date.desc()).all()
    return render_template('admin_bookings.html', pending=pend, approved=appr, declined=decl)

@app.route('/admin/bookings/<int:bid>/approve', methods=['POST'])
@login_required
def approve_booking(bid):
    require_admin()
    b = Booking.query.get_or_404(bid); b.status = "approved"; db.session.commit()
    flash('Reservering goedgekeurd.', 'success'); return redirect(url_for('admin_bookings'))

@app.route('/admin/bookings/<int:bid>/decline', methods=['POST'])
@login_required
def decline_booking(bid):
    require_admin()
    b = Booking.query.get_or_404(bid); b.status = "declined"; db.session.commit()
    flash('Reservering afgewezen.', 'info'); return redirect(url_for('admin_bookings'))

# SEO: robots + sitemap
@app.route('/robots.txt')
def robots():
    return Response("User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n", mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap():
    pages = ['/', '/gallery', '/amenities', '/area', '/contact', '/reserve']
    xml = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    now = datetime.utcnow().strftime('%Y-%m-%d')
    for p in pages:
        xml += [f"<url><loc>{{}}</loc><lastmod>{now}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>".format(request.url_root.rstrip('/') + p)]
    xml.append('</urlset>')
    return Response("\n".join(xml), mimetype='application/xml')

# Health
@app.route('/health')
def health(): return {"status":"ok"}

# DB init
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
