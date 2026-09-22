"""
Befüllt die Datenbank mit einem realistischen Artikelstamm für einen
Drahtverarbeiter: ca. 160 Artikel aus Kombinationen von Durchmesser
und Legierung, dazu Beispiel-Mitarbeiter und ein paar Beispielaufträge.

Aufruf: python -m app.seed
"""
import random
from datetime import datetime, timedelta

from .database import Base, SessionLocal, engine
from .models import Auftrag, Bewegung, Material, Mitarbeiter

# (Legierungs-Code, Klartext-Bezeichnung, Liste der lieferbaren Durchmesser in mm)
LEGIERUNGEN = [
    ("C4C", "Kohlenstoffstahl C4C (EN 10016, weich)",
     [0.10, 0.12, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.80, 1.00, 1.20, 1.50, 2.00, 3.00, 4.00, 4.90]),
    ("C9D", "Kohlenstoffstahl C9D (EN 10016)",
     [0.20, 0.30, 0.40, 0.50, 0.60, 0.80, 1.00, 1.20, 1.50, 2.00, 2.50, 3.00, 4.00, 4.90]),
    ("C15D", "Kohlenstoffstahl C15D",
     [0.30, 0.40, 0.50, 0.70, 0.90, 1.20, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00, 4.90, 5.50]),
    ("C22C", "Kohlenstoffstahl C22C (einsatzfähig)",
     [0.50, 0.80, 1.00, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00, 4.50, 5.00, 6.00]),
    ("C35C", "Vergütungsstahl C35C",
     [1.00, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00, 4.50, 5.00, 6.00, 7.00, 8.00]),
    ("C45C", "Vergütungsstahl C45C",
     [1.50, 2.00, 2.50, 3.00, 3.50, 4.00, 4.50, 4.90, 5.00, 6.00, 7.00, 8.00, 10.00]),
    ("C60D", "Federstahl C60D",
     [0.50, 0.80, 1.00, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00, 5.00, 6.00]),
    ("C72D", "Federstahl C72D (hochfest)",
     [0.30, 0.50, 0.80, 1.00, 1.50, 2.00, 2.50, 3.00, 4.00, 5.00]),
    ("C75D", "Federstahl C75D",
     [0.40, 0.60, 0.80, 1.00, 1.50, 2.00, 2.50, 3.00, 4.00, 5.00, 6.00]),
    ("1.4301", "Edelstahl 1.4301 (V2A)",
     [0.20, 0.30, 0.50, 0.80, 1.00, 1.50, 2.00, 2.50, 3.00, 4.00, 5.00, 6.00]),
    ("1.4401", "Edelstahl 1.4401 (V4A)",
     [0.50, 0.80, 1.00, 1.50, 2.00, 3.00, 4.00, 5.00]),
    ("1.4310", "Federstahl 1.4310 (nichtrostend)",
     [0.20, 0.30, 0.40, 0.50, 0.80, 1.00, 1.50, 2.00]),
    ("CuSn6", "Bronze CuSn6",
     [0.30, 0.50, 0.80, 1.00, 1.50, 2.00]),
    ("CuZn37", "Messing CuZn37",
     [0.30, 0.50, 0.80, 1.00, 1.50, 2.00]),
    ("AlMg3", "Aluminium AlMg3",
     [0.80, 1.00, 1.50, 2.00, 3.00, 4.00]),
]


def artikelnummer(durchmesser_mm: float, legierung: str) -> str:
    return f"DR-{durchmesser_mm:.2f}-{legierung}"


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Material).count() > 0:
            print("Datenbank enthält bereits Artikel – Seed wird übersprungen.")
            return

        random.seed(42)
        materialien = []
        for code, bezeichnung, durchmesser_liste in LEGIERUNGEN:
            for d in durchmesser_liste:
                bestand = round(random.uniform(80, 1800), 1)
                mindestbestand = round(bestand * random.uniform(0.10, 0.25), 1)
                m = Material(
                    artikelnummer=artikelnummer(d, code),
                    durchmesser_mm=d,
                    legierung=code,
                    legierung_bezeichnung=bezeichnung,
                    bestand_kg=bestand,
                    mindestbestand_kg=mindestbestand,
                    lagerplatz=f"L{random.randint(1, 9)}-{random.randint(1, 40):02d}",
                    aktiv=True,
                )
                materialien.append(m)
        db.add_all(materialien)
        db.flush()

        mitarbeiter = [
            Mitarbeiter(name="Anna Berger", kuerzel="ABE"),
            Mitarbeiter(name="Markus Weiß", kuerzel="MWE"),
            Mitarbeiter(name="Fatima Yildiz", kuerzel="FYI"),
            Mitarbeiter(name="Thomas Gruber", kuerzel="TGR"),
            Mitarbeiter(name="Lena Hofer", kuerzel="LHO"),
        ]
        db.add_all(mitarbeiter)

        # Beispielauftrag: 500 kg von 4,90 mm C4C-Draht (falls in Liste vorhanden,
        # sonst nächstliegenden Artikel nehmen)
        beispiel_material = (
            db.query(Material)
            .filter(Material.legierung == "C4C")
            .order_by(Material.durchmesser_mm.desc())
            .first()
        )
        beispiel_material_49 = (
            db.query(Material).filter(Material.artikelnummer == "DR-4.90-C4C").first()
        )
        ziel_material = beispiel_material_49 or beispiel_material

        beispielauftraege = []
        if ziel_material:
            beispielauftraege.append(
                Auftrag(
                    auftragsnummer="A-000001",
                    material_id=ziel_material.id,
                    bedarf_kg=500.0,
                    gebucht_kg=0.0,
                    status="offen",
                    bezeichnung="Fertigungsauftrag Federnproduktion Linie 2",
                    erstellt_von="Anna Berger",
                )
            )

        weitere = (
            db.query(Material)
            .filter(Material.id != (ziel_material.id if ziel_material else -1))
            .limit(3)
            .all()
        )
        for i, mat in enumerate(weitere, start=2):
            beispielauftraege.append(
                Auftrag(
                    auftragsnummer=f"A-{i:06d}",
                    material_id=mat.id,
                    bedarf_kg=round(random.uniform(50, 400), 1),
                    gebucht_kg=0.0,
                    status="offen",
                    bezeichnung=f"Fertigungsauftrag {i}",
                    erstellt_von="Markus Weiß",
                )
            )
        db.add_all(beispielauftraege)

        db.commit()
        print(f"Seed abgeschlossen: {len(materialien)} Artikel, "
              f"{len(mitarbeiter)} Mitarbeiter, {len(beispielauftraege)} Beispielaufträge.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
