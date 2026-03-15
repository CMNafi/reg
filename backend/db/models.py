import os
import json
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean, Text, DateTime, JSON,
    event
)
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./regintel.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


class Firm(Base):
    __tablename__ = "firms"

    crd_number = Column(String, primary_key=True)
    cik = Column(String, nullable=True)
    legal_name = Column(String, nullable=True)
    doing_business_as = Column(String, nullable=True)
    registration_date = Column(String, nullable=True)
    last_adv_date = Column(String, nullable=True)
    last_13f_date = Column(String, nullable=True)
    aum_total = Column(Float, nullable=True)
    aum_discretionary = Column(Float, nullable=True)
    employee_count = Column(Integer, nullable=True)
    employee_count_prior = Column(Integer, nullable=True)
    client_count = Column(Integer, nullable=True)
    private_fund_count = Column(Integer, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True)
    website = Column(String, nullable=True)
    primary_strategy = Column(String, nullable=True)
    ownership_structure = Column(String, nullable=True)
    fee_structure = Column(String, nullable=True)
    drp_count = Column(Integer, default=0)
    has_criminal_drp = Column(Boolean, default=False)
    has_regulatory_drp = Column(Boolean, default=False)
    custodians = Column(JSON, nullable=True)
    auditors = Column(JSON, nullable=True)
    data_source = Column(String, nullable=True)
    data_verified_at = Column(DateTime, nullable=True)
    raw_adv = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    firm_crd = Column(String, nullable=False)
    period_end = Column(String, nullable=True)
    issuer_name = Column(String, nullable=True)
    cusip = Column(String, nullable=True)
    ticker = Column(String, nullable=True)
    market_value = Column(Float, nullable=True)
    shares = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    is_new = Column(Boolean, default=False)
    is_exited = Column(Boolean, default=False)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class HoldingSnapshot(Base):
    __tablename__ = "holding_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    firm_crd = Column(String, nullable=False)
    period_end = Column(String, nullable=True)
    total_value = Column(Float, nullable=True)
    holding_count = Column(Integer, nullable=True)
    top10_concentration = Column(Float, nullable=True)
    largest_position_pct = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Disclosure(Base):
    __tablename__ = "disclosures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    firm_crd = Column(String, nullable=False)
    disclosure_type = Column(String, nullable=True)
    event_date = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class ChangeEvent(Base):
    __tablename__ = "change_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    firm_crd = Column(String, nullable=False)
    filing_date = Column(String, nullable=True)
    field_name = Column(String, nullable=True)
    previous_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    change_type = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    materiality = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class RiskFlag(Base):
    __tablename__ = "risk_flags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    firm_crd = Column(String, nullable=False)
    category = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    why_it_matters = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class KeyPerson(Base):
    __tablename__ = "key_persons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    firm_crd = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, nullable=True)
    ownership_pct = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
