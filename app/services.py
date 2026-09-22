"""Geschäftslogik für Bestandsbuchungen (Ausgang, Eingang, Korrektur)."""
from datetime import datetime

from sqlalchemy.orm import Session

from . import models


class BuchungsFehler(Exception):
    """Wird ausgelöst, wenn eine Buchung fachlich nicht zulässig ist (z.B. Bestand reicht nicht)."""


def generiere_auftragsnummer(db: Session) -> str:
    anzahl = db.query(models.Auftrag).count()
    kandidat_nr = anzahl + 1
    while True:
        nummer = f"A-{kandidat_nr:06d}"
        vorhanden = (
            db.query(models.Auftrag)
            .filter(models.Auftrag.auftragsnummer == nummer)
            .first()
        )
        if not vorhanden:
            return nummer
        kandidat_nr += 1


def _aktualisiere_auftragsstatus(auftrag: models.Auftrag) -> None:
    if auftrag.status == "storniert":
        return
    if auftrag.gebucht_kg >= auftrag.bedarf_kg - 1e-6:
        auftrag.status = "erledigt"
        if auftrag.abgeschlossen_am is None:
            auftrag.abgeschlossen_am = datetime.utcnow()
    elif auftrag.gebucht_kg > 0:
        auftrag.status = "in_arbeit"
    else:
        auftrag.status = "offen"


def buche_ausgang(
    db: Session,
    material: models.Material,
    menge_kg: float,
    mitarbeiter: str,
    quelle: str,
    auftrag: "models.Auftrag | None" = None,
    notiz: str | None = None,
    erlaube_negativ: bool = False,
) -> models.Bewegung:
    if menge_kg <= 0:
        raise BuchungsFehler("Die Menge muss größer als 0 kg sein.")
    if not mitarbeiter or not mitarbeiter.strip():
        raise BuchungsFehler("Bitte einen Mitarbeiter angeben.")
    if not erlaube_negativ and material.bestand_kg - menge_kg < -1e-6:
        raise BuchungsFehler(
            f"Bestand reicht nicht aus: verfügbar {material.bestand_kg:.1f} kg, "
            f"angefordert {menge_kg:.1f} kg."
        )

    material.bestand_kg = round(material.bestand_kg - menge_kg, 3)

    if auftrag is not None:
        auftrag.gebucht_kg = round(auftrag.gebucht_kg + menge_kg, 3)
        _aktualisiere_auftragsstatus(auftrag)

    bewegung = models.Bewegung(
        material_id=material.id,
        auftrag_id=auftrag.id if auftrag is not None else None,
        menge_kg=-menge_kg,
        typ="Ausgang",
        mitarbeiter=mitarbeiter.strip(),
        quelle=quelle,
        bestand_nach_kg=material.bestand_kg,
        notiz=notiz,
    )
    db.add(bewegung)
    db.commit()
    db.refresh(bewegung)
    return bewegung


def buche_eingang(
    db: Session,
    material: models.Material,
    menge_kg: float,
    mitarbeiter: str,
    notiz: str | None = None,
) -> models.Bewegung:
    if menge_kg <= 0:
        raise BuchungsFehler("Die Menge muss größer als 0 kg sein.")
    if not mitarbeiter or not mitarbeiter.strip():
        raise BuchungsFehler("Bitte einen Mitarbeiter angeben.")

    material.bestand_kg = round(material.bestand_kg + menge_kg, 3)

    bewegung = models.Bewegung(
        material_id=material.id,
        auftrag_id=None,
        menge_kg=menge_kg,
        typ="Eingang",
        mitarbeiter=mitarbeiter.strip(),
        quelle="wareneingang",
        bestand_nach_kg=material.bestand_kg,
        notiz=notiz,
    )
    db.add(bewegung)
    db.commit()
    db.refresh(bewegung)
    return bewegung


def korrektur(
    db: Session,
    material: models.Material,
    neuer_bestand_kg: float,
    mitarbeiter: str,
    notiz: str | None = None,
) -> models.Bewegung:
    if neuer_bestand_kg < 0:
        raise BuchungsFehler("Der Bestand kann nicht negativ sein.")
    if not mitarbeiter or not mitarbeiter.strip():
        raise BuchungsFehler("Bitte einen Mitarbeiter angeben.")

    differenz = round(neuer_bestand_kg - material.bestand_kg, 3)
    material.bestand_kg = round(neuer_bestand_kg, 3)

    bewegung = models.Bewegung(
        material_id=material.id,
        auftrag_id=None,
        menge_kg=differenz,
        typ="Korrektur",
        mitarbeiter=mitarbeiter.strip(),
        quelle="korrektur",
        bestand_nach_kg=material.bestand_kg,
        notiz=notiz,
    )
    db.add(bewegung)
    db.commit()
    db.refresh(bewegung)
    return bewegung
