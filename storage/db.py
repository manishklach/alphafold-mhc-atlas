from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine, inspect, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from core.config import get_settings


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CandidateRecord(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="new")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class StructureRecord(Base):
    __tablename__ = "structures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    structure_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class ComparisonRecord(Base):
    __tablename__ = "comparisons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    comparison_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    wt_candidate_id: Mapped[str] = mapped_column(String(255), nullable=False)
    mutant_candidate_id: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class DecisionRecord(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(String(255), nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    priority_label: Mapped[str] = mapped_column(String(32), default="LOW")
    explanation: Mapped[str] = mapped_column(Text, default="")
    flags_json: Mapped[str] = mapped_column(Text, default="[]")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


def init_db(database_url: str | None = None) -> None:
    engine = _get_engine(database_url)
    _reconcile_schema(engine)
    Base.metadata.create_all(bind=engine)


def insert_candidate(
    candidate_id: str,
    metadata: dict[str, Any] | None = None,
    status: str = "new",
    database_url: str | None = None,
) -> dict[str, Any]:
    init_db(database_url)
    session_factory = _get_session_factory(database_url)
    payload = json.dumps(metadata or {}, sort_keys=True)
    with session_factory() as session:
        record = session.scalar(
            select(CandidateRecord).where(CandidateRecord.candidate_id == candidate_id)
        )
        if record is None:
            record = CandidateRecord(candidate_id=candidate_id, status=status, metadata_json=payload)
            session.add(record)
        else:
            record.status = status
            record.metadata_json = payload
        session.commit()
        session.refresh(record)
        return _candidate_to_dict(record)


def get_candidates(database_url: str | None = None) -> list[dict[str, Any]]:
    init_db(database_url)
    session_factory = _get_session_factory(database_url)
    with session_factory() as session:
        records = session.scalars(select(CandidateRecord).order_by(CandidateRecord.id.asc())).all()
        return [_candidate_to_dict(record) for record in records]


def save_decision(
    candidate_id: str,
    priority_score: float,
    priority_label: str,
    explanation: str,
    flags: list[str] | None = None,
    database_url: str | None = None,
) -> dict[str, Any]:
    init_db(database_url)
    session_factory = _get_session_factory(database_url)
    with session_factory() as session:
        record = DecisionRecord(
            candidate_id=candidate_id,
            priority_score=float(priority_score),
            priority_label=priority_label,
            explanation=explanation,
            flags_json=json.dumps(flags or [], sort_keys=True),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return _decision_to_dict(record)


def get_decision_history(candidate_id: str, database_url: str | None = None) -> list[dict[str, Any]]:
    init_db(database_url)
    session_factory = _get_session_factory(database_url)
    with session_factory() as session:
        records = session.scalars(
            select(DecisionRecord)
            .where(DecisionRecord.candidate_id == candidate_id)
            .order_by(DecisionRecord.timestamp.asc(), DecisionRecord.id.asc())
        ).all()
        return [_decision_to_dict(record) for record in records]


def get_decisions(
    candidate_id: str | None = None,
    database_url: str | None = None,
) -> list[dict[str, Any]]:
    init_db(database_url)
    session_factory = _get_session_factory(database_url)
    with session_factory() as session:
        statement = select(DecisionRecord)
        if candidate_id:
            statement = statement.where(DecisionRecord.candidate_id == candidate_id)
        records = session.scalars(
            statement.order_by(DecisionRecord.timestamp.desc(), DecisionRecord.id.desc())
        ).all()
        return [_decision_to_dict(record) for record in records]


def _get_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    if url.startswith("sqlite:///"):
        db_path = Path(url.replace("sqlite:///", "", 1))
        if db_path.parent and str(db_path.parent) != ".":
            db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, future=True)


def _get_session_factory(database_url: str | None = None):
    return sessionmaker(bind=_get_engine(database_url), autoflush=False, autocommit=False, future=True)


def _reconcile_schema(engine) -> None:
    inspector = inspect(engine)
    if "decisions" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("decisions")}
    required_columns = {
        "id",
        "candidate_id",
        "priority_score",
        "priority_label",
        "explanation",
        "flags_json",
        "timestamp",
    }
    if required_columns.issubset(existing_columns):
        return

    with engine.begin() as connection:
        connection.execute(text("DROP TABLE decisions"))


def _candidate_to_dict(record: CandidateRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "candidate_id": record.candidate_id,
        "status": record.status,
        "metadata": json.loads(record.metadata_json or "{}"),
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def _decision_to_dict(record: DecisionRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "candidate_id": record.candidate_id,
        "priority_score": float(record.priority_score),
        "priority_label": record.priority_label,
        "explanation": record.explanation,
        "flags": json.loads(record.flags_json or "[]"),
        "timestamp": record.timestamp.isoformat() if record.timestamp else None,
    }
