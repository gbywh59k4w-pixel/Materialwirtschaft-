from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from .database import Base


class Material(Base):
    __tablename__ = "materialien"

    id = Column(Integer, primary_key=True, index=True)
    artikelnummer = Column(String, unique=True, index=True, nullable=False)
    durchmesser_mm = Column(Float, nullable=False)
    legierung = Column(String, nullable=False, index=True)
    legierung_bezeichnung = Column(String, nullable=False)
    bestand_kg = Column(Float, nullable=False, default=0.0)
    mindestbestand_kg = Column(Float, nullable=False, default=0.0)
    lagerplatz = Column(String, nullable=True)
    aktiv = Column(Boolean, nullable=False, default=True)
    erstellt_am = Column(DateTime, default=datetime.utcnow)

    auftraege = relationship("Auftrag", back_populates="material")
    bewegungen = relationship("Bewegung", back_populates="material")

    @property
    def unterbestand(self) -> bool:
        return self.bestand_kg < self.mindestbestand_kg


class Auftrag(Base):
    __tablename__ = "auftraege"

    id = Column(Integer, primary_key=True, index=True)
    auftragsnummer = Column(String, unique=True, index=True, nullable=False)
    material_id = Column(Integer, ForeignKey("materialien.id"), nullable=False)
    bedarf_kg = Column(Float, nullable=False)
    gebucht_kg = Column(Float, nullable=False, default=0.0)
    status = Column(String, nullable=False, default="offen")  # offen, in_arbeit, erledigt, storniert
    bezeichnung = Column(String, nullable=True)
    erstellt_von = Column(String, nullable=True)
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    abgeschlossen_am = Column(DateTime, nullable=True)

    material = relationship("Material", back_populates="auftraege")
    bewegungen = relationship("Bewegung", back_populates="auftrag")

    @property
    def rest_kg(self) -> float:
        return max(self.bedarf_kg - self.gebucht_kg, 0.0)

    @property
    def fortschritt_prozent(self) -> float:
        if self.bedarf_kg <= 0:
            return 100.0
        return min(100.0, round(self.gebucht_kg / self.bedarf_kg * 100, 1))


class Bewegung(Base):
    __tablename__ = "bewegungen"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materialien.id"), nullable=False)
    auftrag_id = Column(Integer, ForeignKey("auftraege.id"), nullable=True)
    menge_kg = Column(Float, nullable=False)  # positiv = Eingang, negativ = Ausgang
    typ = Column(String, nullable=False)  # Ausgang, Eingang, Korrektur
    mitarbeiter = Column(String, nullable=False)
    quelle = Column(String, nullable=False)  # scan_auftrag, scan_artikel, manuell, wareneingang, korrektur
    bestand_nach_kg = Column(Float, nullable=False)
    notiz = Column(String, nullable=True)
    zeitstempel = Column(DateTime, default=datetime.utcnow, index=True)

    material = relationship("Material", back_populates="bewegungen")
    auftrag = relationship("Auftrag", back_populates="bewegungen")


class Mitarbeiter(Base):
    __tablename__ = "mitarbeiter"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    kuerzel = Column(String, nullable=True)
    aktiv = Column(Boolean, nullable=False, default=True)
