import os
import re
from datetime import datetime

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import models, services
from .database import Base, engine, get_db
from .qrcode_utils import generate_qr_png
from .seed import seed as seed_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

Base.metadata.create_all(bind=engine)
seed_db()

app = FastAPI(title="Materialwirtschaft Draht")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.globals["now"] = datetime.utcnow

ARTIKELNUMMER_RE = re.compile(r"^DR-")
AUFTRAGSNUMMER_RE = re.compile(r"^A-\d+$")


def render(request: Request, template: str, context: dict, status_code: int = 200):
    context["request"] = request
    return templates.TemplateResponse(template, context, status_code=status_code)


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    anzahl_artikel = db.query(models.Material).filter(models.Material.aktiv.is_(True)).count()
    offene_auftraege = (
        db.query(models.Auftrag)
        .filter(models.Auftrag.status.in_(["offen", "in_arbeit"]))
        .order_by(models.Auftrag.erstellt_am.desc())
        .all()
    )
    unterbestand = (
        db.query(models.Material)
        .filter(models.Material.aktiv.is_(True))
        .filter(models.Material.bestand_kg < models.Material.mindestbestand_kg)
        .order_by(models.Material.bestand_kg.asc())
        .all()
    )
    letzte_bewegungen = (
        db.query(models.Bewegung)
        .order_by(models.Bewegung.zeitstempel.desc())
        .limit(15)
        .all()
    )
    return render(request, "dashboard.html", {
        "anzahl_artikel": anzahl_artikel,
        "offene_auftraege": offene_auftraege,
        "unterbestand": unterbestand,
        "letzte_bewegungen": letzte_bewegungen,
    })


# --------------------------------------------------------------------------
# Materialien (Artikelstamm)
# --------------------------------------------------------------------------

@app.get("/materialien", response_class=HTMLResponse)
def materialien_liste(
    request: Request,
    q: str = "",
    legierung: str = "",
    nur_unterbestand: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(models.Material).filter(models.Material.aktiv.is_(True))
    if q:
        muster = f"%{q.strip()}%"
        query = query.filter(
            or_(
                models.Material.artikelnummer.ilike(muster),
                models.Material.legierung.ilike(muster),
                models.Material.legierung_bezeichnung.ilike(muster),
            )
        )
    if legierung:
        query = query.filter(models.Material.legierung == legierung)
    if nur_unterbestand:
        query = query.filter(models.Material.bestand_kg < models.Material.mindestbestand_kg)

    materialien = query.order_by(
        models.Material.legierung.asc(), models.Material.durchmesser_mm.asc()
    ).all()

    alle_legierungen = [
        row[0]
        for row in db.query(models.Material.legierung).distinct().order_by(models.Material.legierung).all()
    ]

    return render(request, "materialien_liste.html", {
        "materialien": materialien,
        "q": q,
        "legierung": legierung,
        "nur_unterbestand": nur_unterbestand,
        "alle_legierungen": alle_legierungen,
    })


@app.get("/materialien/neu", response_class=HTMLResponse)
def material_neu_formular(request: Request):
    return render(request, "material_neu.html", {"fehler": None, "werte": {}})


@app.post("/materialien/neu")
def material_neu_speichern(
    request: Request,
    durchmesser_mm: float = Form(...),
    legierung: str = Form(...),
    legierung_bezeichnung: str = Form(...),
    bestand_kg: float = Form(0.0),
    mindestbestand_kg: float = Form(0.0),
    lagerplatz: str = Form(""),
    db: Session = Depends(get_db),
):
    legierung = legierung.strip().upper()
    nummer = f"DR-{durchmesser_mm:.2f}-{legierung}"
    vorhanden = db.query(models.Material).filter(models.Material.artikelnummer == nummer).first()
    if vorhanden:
        return render(request, "material_neu.html", {
            "fehler": f"Artikel {nummer} existiert bereits.",
            "werte": {
                "durchmesser_mm": durchmesser_mm, "legierung": legierung,
                "legierung_bezeichnung": legierung_bezeichnung, "bestand_kg": bestand_kg,
                "mindestbestand_kg": mindestbestand_kg, "lagerplatz": lagerplatz,
            },
        }, status_code=400)

    material = models.Material(
        artikelnummer=nummer,
        durchmesser_mm=durchmesser_mm,
        legierung=legierung,
        legierung_bezeichnung=legierung_bezeichnung.strip() or legierung,
        bestand_kg=bestand_kg,
        mindestbestand_kg=mindestbestand_kg,
        lagerplatz=lagerplatz.strip() or None,
        aktiv=True,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return RedirectResponse(f"/materialien/{material.id}", status_code=303)


@app.get("/materialien/{material_id}", response_class=HTMLResponse)
def material_detail(request: Request, material_id: int, db: Session = Depends(get_db)):
    material = db.get(models.Material, material_id)
    if not material:
        return render(request, "fehler.html", {"meldung": "Artikel nicht gefunden."}, status_code=404)
    bewegungen = (
        db.query(models.Bewegung)
        .filter(models.Bewegung.material_id == material_id)
        .order_by(models.Bewegung.zeitstempel.desc())
        .limit(50)
        .all()
    )
    offene_auftraege = (
        db.query(models.Auftrag)
        .filter(models.Auftrag.material_id == material_id)
        .filter(models.Auftrag.status.in_(["offen", "in_arbeit"]))
        .all()
    )
    mitarbeiter = db.query(models.Mitarbeiter).filter(models.Mitarbeiter.aktiv.is_(True)).order_by(models.Mitarbeiter.name).all()
    return render(request, "material_detail.html", {
        "material": material,
        "bewegungen": bewegungen,
        "offene_auftraege": offene_auftraege,
        "mitarbeiter": mitarbeiter,
        "fehler": request.query_params.get("fehler"),
    })


@app.get("/materialien/{material_id}/qr.png")
def material_qr(material_id: int, db: Session = Depends(get_db)):
    material = db.get(models.Material, material_id)
    if not material:
        return Response(status_code=404)
    png = generate_qr_png(material.artikelnummer)
    return Response(content=png, media_type="image/png")


@app.get("/materialien/{material_id}/etikett", response_class=HTMLResponse)
def material_etikett(request: Request, material_id: int, db: Session = Depends(get_db)):
    material = db.get(models.Material, material_id)
    if not material:
        return render(request, "fehler.html", {"meldung": "Artikel nicht gefunden."}, status_code=404)
    return render(request, "material_etikett.html", {"material": material})


@app.post("/materialien/{material_id}/wareneingang")
def material_wareneingang(
    material_id: int,
    menge_kg: float = Form(...),
    mitarbeiter: str = Form(...),
    notiz: str = Form(""),
    db: Session = Depends(get_db),
):
    material = db.get(models.Material, material_id)
    if not material:
        return render_fehler_redirect(material_id, "Artikel nicht gefunden.")
    try:
        services.buche_eingang(db, material, menge_kg, mitarbeiter, notiz or None)
    except services.BuchungsFehler as exc:
        return RedirectResponse(f"/materialien/{material_id}?fehler={exc}", status_code=303)
    return RedirectResponse(f"/materialien/{material_id}", status_code=303)


@app.post("/materialien/{material_id}/ausbuchen")
def material_ausbuchen(
    material_id: int,
    menge_kg: float = Form(...),
    mitarbeiter: str = Form(...),
    notiz: str = Form(""),
    erlaube_negativ: bool = Form(False),
    quelle: str = Form("manuell"),
    db: Session = Depends(get_db),
):
    material = db.get(models.Material, material_id)
    if not material:
        return RedirectResponse("/materialien", status_code=303)
    try:
        services.buche_ausgang(
            db, material, menge_kg, mitarbeiter,
            quelle=quelle if quelle in ("scan_artikel", "manuell") else "manuell",
            auftrag=None, notiz=notiz or None,
            erlaube_negativ=erlaube_negativ,
        )
    except services.BuchungsFehler as exc:
        return RedirectResponse(f"/materialien/{material_id}?fehler={exc}", status_code=303)
    return RedirectResponse(f"/materialien/{material_id}", status_code=303)


@app.post("/materialien/{material_id}/korrektur")
def material_korrektur(
    material_id: int,
    neuer_bestand_kg: float = Form(...),
    mitarbeiter: str = Form(...),
    notiz: str = Form(""),
    db: Session = Depends(get_db),
):
    material = db.get(models.Material, material_id)
    if not material:
        return RedirectResponse("/materialien", status_code=303)
    try:
        services.korrektur(db, material, neuer_bestand_kg, mitarbeiter, notiz or None)
    except services.BuchungsFehler as exc:
        return RedirectResponse(f"/materialien/{material_id}?fehler={exc}", status_code=303)
    return RedirectResponse(f"/materialien/{material_id}", status_code=303)


def render_fehler_redirect(material_id: int, meldung: str):
    return RedirectResponse(f"/materialien/{material_id}?fehler={meldung}", status_code=303)


# --------------------------------------------------------------------------
# Aufträge
# --------------------------------------------------------------------------

@app.get("/auftraege", response_class=HTMLResponse)
def auftraege_liste(request: Request, status: str = "", db: Session = Depends(get_db)):
    query = db.query(models.Auftrag)
    if status:
        query = query.filter(models.Auftrag.status == status)
    auftraege = query.order_by(models.Auftrag.erstellt_am.desc()).all()
    return render(request, "auftraege_liste.html", {"auftraege": auftraege, "status": status})


@app.get("/auftraege/neu", response_class=HTMLResponse)
def auftrag_neu_formular(request: Request, db: Session = Depends(get_db)):
    materialien = (
        db.query(models.Material)
        .filter(models.Material.aktiv.is_(True))
        .order_by(models.Material.legierung, models.Material.durchmesser_mm)
        .all()
    )
    mitarbeiter = db.query(models.Mitarbeiter).filter(models.Mitarbeiter.aktiv.is_(True)).order_by(models.Mitarbeiter.name).all()
    return render(request, "auftrag_neu.html", {
        "materialien": materialien, "mitarbeiter": mitarbeiter, "fehler": None, "werte": {},
    })


@app.post("/auftraege/neu")
def auftrag_neu_speichern(
    request: Request,
    material_id: int = Form(...),
    bedarf_kg: float = Form(...),
    bezeichnung: str = Form(""),
    erstellt_von: str = Form(""),
    db: Session = Depends(get_db),
):
    material = db.get(models.Material, material_id)
    if not material:
        materialien = db.query(models.Material).order_by(models.Material.legierung, models.Material.durchmesser_mm).all()
        mitarbeiter = db.query(models.Mitarbeiter).order_by(models.Mitarbeiter.name).all()
        return render(request, "auftrag_neu.html", {
            "materialien": materialien, "mitarbeiter": mitarbeiter,
            "fehler": "Bitte einen gültigen Artikel wählen.", "werte": {},
        }, status_code=400)

    nummer = services.generiere_auftragsnummer(db)
    auftrag = models.Auftrag(
        auftragsnummer=nummer,
        material_id=material.id,
        bedarf_kg=bedarf_kg,
        gebucht_kg=0.0,
        status="offen",
        bezeichnung=bezeichnung.strip() or None,
        erstellt_von=erstellt_von.strip() or None,
    )
    db.add(auftrag)
    db.commit()
    db.refresh(auftrag)
    return RedirectResponse(f"/auftraege/{auftrag.id}", status_code=303)


@app.get("/auftraege/{auftrag_id}", response_class=HTMLResponse)
def auftrag_detail(request: Request, auftrag_id: int, db: Session = Depends(get_db)):
    auftrag = db.get(models.Auftrag, auftrag_id)
    if not auftrag:
        return render(request, "fehler.html", {"meldung": "Auftrag nicht gefunden."}, status_code=404)
    bewegungen = (
        db.query(models.Bewegung)
        .filter(models.Bewegung.auftrag_id == auftrag_id)
        .order_by(models.Bewegung.zeitstempel.desc())
        .all()
    )
    mitarbeiter = db.query(models.Mitarbeiter).filter(models.Mitarbeiter.aktiv.is_(True)).order_by(models.Mitarbeiter.name).all()
    return render(request, "auftrag_detail.html", {
        "auftrag": auftrag, "bewegungen": bewegungen, "mitarbeiter": mitarbeiter,
        "fehler": request.query_params.get("fehler"),
    })


@app.get("/auftraege/{auftrag_id}/qr.png")
def auftrag_qr(auftrag_id: int, db: Session = Depends(get_db)):
    auftrag = db.get(models.Auftrag, auftrag_id)
    if not auftrag:
        return Response(status_code=404)
    png = generate_qr_png(auftrag.auftragsnummer)
    return Response(content=png, media_type="image/png")


@app.get("/auftraege/{auftrag_id}/laufzettel", response_class=HTMLResponse)
def auftrag_laufzettel(request: Request, auftrag_id: int, db: Session = Depends(get_db)):
    auftrag = db.get(models.Auftrag, auftrag_id)
    if not auftrag:
        return render(request, "fehler.html", {"meldung": "Auftrag nicht gefunden."}, status_code=404)
    return render(request, "auftrag_laufzettel.html", {"auftrag": auftrag})


@app.post("/auftraege/{auftrag_id}/buchen")
def auftrag_buchen(
    auftrag_id: int,
    menge_kg: float = Form(...),
    mitarbeiter: str = Form(...),
    notiz: str = Form(""),
    erlaube_negativ: bool = Form(False),
    quelle: str = Form("manuell"),
    db: Session = Depends(get_db),
):
    auftrag = db.get(models.Auftrag, auftrag_id)
    if not auftrag:
        return RedirectResponse("/auftraege", status_code=303)
    if auftrag.status in ("erledigt", "storniert"):
        return RedirectResponse(f"/auftraege/{auftrag_id}?fehler=Auftrag ist bereits abgeschlossen.", status_code=303)
    material = auftrag.material
    try:
        services.buche_ausgang(
            db, material, menge_kg, mitarbeiter,
            quelle=quelle if quelle in ("scan_auftrag", "manuell") else "manuell",
            auftrag=auftrag, notiz=notiz or None, erlaube_negativ=erlaube_negativ,
        )
    except services.BuchungsFehler as exc:
        return RedirectResponse(f"/auftraege/{auftrag_id}?fehler={exc}", status_code=303)
    return RedirectResponse(f"/auftraege/{auftrag_id}?gebucht=1", status_code=303)


@app.post("/auftraege/{auftrag_id}/stornieren")
def auftrag_stornieren(auftrag_id: int, db: Session = Depends(get_db)):
    auftrag = db.get(models.Auftrag, auftrag_id)
    if auftrag and auftrag.status not in ("erledigt",):
        auftrag.status = "storniert"
        db.commit()
    return RedirectResponse(f"/auftraege/{auftrag_id}", status_code=303)


# --------------------------------------------------------------------------
# Scan-Station
# --------------------------------------------------------------------------

@app.get("/scan", response_class=HTMLResponse)
def scan_start(request: Request):
    return render(request, "scan.html", {"fehler": None})


@app.post("/scan", response_class=HTMLResponse)
def scan_verarbeiten(request: Request, code: str = Form(...), db: Session = Depends(get_db)):
    code = code.strip()

    if AUFTRAGSNUMMER_RE.match(code):
        auftrag = db.query(models.Auftrag).filter(models.Auftrag.auftragsnummer == code).first()
        if not auftrag:
            return render(request, "scan.html", {"fehler": f"Auftrag '{code}' wurde nicht gefunden."})
        if auftrag.status in ("erledigt", "storniert"):
            return render(request, "scan.html", {
                "fehler": f"Auftrag {code} ist bereits abgeschlossen bzw. storniert."
            })
        mitarbeiter = db.query(models.Mitarbeiter).filter(models.Mitarbeiter.aktiv.is_(True)).order_by(models.Mitarbeiter.name).all()
        return render(request, "scan_auftrag.html", {"auftrag": auftrag, "mitarbeiter": mitarbeiter})

    if ARTIKELNUMMER_RE.match(code):
        material = db.query(models.Material).filter(models.Material.artikelnummer == code).first()
        if not material:
            return render(request, "scan.html", {"fehler": f"Artikel '{code}' wurde nicht gefunden."})
        mitarbeiter = db.query(models.Mitarbeiter).filter(models.Mitarbeiter.aktiv.is_(True)).order_by(models.Mitarbeiter.name).all()
        offene_auftraege = (
            db.query(models.Auftrag)
            .filter(models.Auftrag.material_id == material.id)
            .filter(models.Auftrag.status.in_(["offen", "in_arbeit"]))
            .all()
        )
        return render(request, "scan_artikel.html", {
            "material": material, "mitarbeiter": mitarbeiter, "offene_auftraege": offene_auftraege,
        })

    return render(request, "scan.html", {"fehler": f"Code '{code}' wurde nicht erkannt (weder Auftrag noch Artikel)."})


# --------------------------------------------------------------------------
# Bewegungshistorie
# --------------------------------------------------------------------------

@app.get("/bewegungen", response_class=HTMLResponse)
def bewegungen_liste(
    request: Request,
    typ: str = "",
    mitarbeiter: str = "",
    db: Session = Depends(get_db),
):
    query = db.query(models.Bewegung)
    if typ:
        query = query.filter(models.Bewegung.typ == typ)
    if mitarbeiter:
        query = query.filter(models.Bewegung.mitarbeiter == mitarbeiter)
    bewegungen = query.order_by(models.Bewegung.zeitstempel.desc()).limit(300).all()
    alle_mitarbeiter = [
        row[0] for row in db.query(models.Bewegung.mitarbeiter).distinct().order_by(models.Bewegung.mitarbeiter).all()
    ]
    return render(request, "bewegungen.html", {
        "bewegungen": bewegungen, "typ": typ, "mitarbeiter": mitarbeiter, "alle_mitarbeiter": alle_mitarbeiter,
    })


# --------------------------------------------------------------------------
# Mitarbeiter
# --------------------------------------------------------------------------

@app.get("/mitarbeiter", response_class=HTMLResponse)
def mitarbeiter_liste(request: Request, db: Session = Depends(get_db)):
    mitarbeiter = db.query(models.Mitarbeiter).order_by(models.Mitarbeiter.name).all()
    return render(request, "mitarbeiter.html", {"mitarbeiter": mitarbeiter, "fehler": None})


@app.post("/mitarbeiter/neu")
def mitarbeiter_neu(name: str = Form(...), kuerzel: str = Form(""), db: Session = Depends(get_db)):
    name = name.strip()
    if name:
        vorhanden = db.query(models.Mitarbeiter).filter(models.Mitarbeiter.name == name).first()
        if not vorhanden:
            db.add(models.Mitarbeiter(name=name, kuerzel=kuerzel.strip() or None, aktiv=True))
            db.commit()
    return RedirectResponse("/mitarbeiter", status_code=303)


@app.post("/mitarbeiter/{mitarbeiter_id}/deaktivieren")
def mitarbeiter_deaktivieren(mitarbeiter_id: int, db: Session = Depends(get_db)):
    m = db.get(models.Mitarbeiter, mitarbeiter_id)
    if m:
        m.aktiv = not m.aktiv
        db.commit()
    return RedirectResponse("/mitarbeiter", status_code=303)
