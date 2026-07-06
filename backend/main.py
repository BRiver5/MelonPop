"""MelonPop backend: anonymous-device game session storage and stats."""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import schemas
from database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MelonPop API", version="1.0.0")

# Expo dev server / device apps; no credentials are used so wildcard is safe.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_or_create_device(db: Session, device_uuid: str) -> models.Device:
    device = (
        db.query(models.Device)
        .filter(models.Device.device_uuid == device_uuid)
        .first()
    )
    if device is None:
        device = models.Device(device_uuid=device_uuid)
        db.add(device)
        db.commit()
        db.refresh(device)
    return device


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/devices/register", response_model=schemas.DeviceOut)
def register_device(payload: schemas.DeviceRegisterIn, db: Session = Depends(get_db)):
    return _get_or_create_device(db, payload.device_uuid)


@app.post("/sessions", response_model=schemas.SessionCreatedOut)
def create_session(payload: schemas.SessionIn, db: Session = Depends(get_db)):
    _get_or_create_device(db, payload.device_uuid)

    session = models.GameSession(
        device_uuid=payload.device_uuid,
        score=payload.score,
        highest_tier_reached=payload.highest_tier_reached,
        fruits_merged=payload.fruits_merged,
        duration_seconds=payload.duration_seconds,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    best_score = (
        db.query(func.max(models.GameSession.score))
        .filter(models.GameSession.device_uuid == payload.device_uuid)
        .scalar()
        or 0
    )
    return schemas.SessionCreatedOut(
        session=schemas.SessionOut.model_validate(session),
        best_score=best_score,
    )


@app.get("/sessions/{device_uuid}", response_model=schemas.SessionListOut)
def list_sessions(device_uuid: str, limit: int = 50, db: Session = Depends(get_db)):
    limit = max(1, min(limit, 500))
    sessions = (
        db.query(models.GameSession)
        .filter(models.GameSession.device_uuid == device_uuid)
        .order_by(models.GameSession.played_at.desc(), models.GameSession.id.desc())
        .limit(limit)
        .all()
    )
    return schemas.SessionListOut(
        sessions=[schemas.SessionOut.model_validate(s) for s in sessions]
    )


@app.get("/stats/{device_uuid}", response_model=schemas.StatsOut)
def get_stats(device_uuid: str, db: Session = Depends(get_db)):
    base_query = db.query(models.GameSession).filter(
        models.GameSession.device_uuid == device_uuid
    )

    totals = (
        db.query(
            func.max(models.GameSession.score),
            func.count(models.GameSession.id),
            func.coalesce(func.sum(models.GameSession.fruits_merged), 0),
        )
        .filter(models.GameSession.device_uuid == device_uuid)
        .one()
    )
    best_score = totals[0] or 0
    total_games = totals[1]
    total_fruits_merged = totals[2]

    tier_rows = (
        db.query(
            models.GameSession.highest_tier_reached,
            func.count(models.GameSession.id),
        )
        .filter(models.GameSession.device_uuid == device_uuid)
        .group_by(models.GameSession.highest_tier_reached)
        .all()
    )
    tier_distribution = {int(tier): int(count) for tier, count in tier_rows}

    # Games per day over the last 14 days (inclusive of today), zero-filled.
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=13)
    day_rows = (
        db.query(
            func.date(models.GameSession.played_at),
            func.count(models.GameSession.id),
        )
        .filter(
            models.GameSession.device_uuid == device_uuid,
            func.date(models.GameSession.played_at) >= start.isoformat(),
        )
        .group_by(func.date(models.GameSession.played_at))
        .all()
    )
    counts_by_day = {str(day): int(count) for day, count in day_rows}
    games_per_day = {
        (start + timedelta(days=i)).isoformat(): counts_by_day.get(
            (start + timedelta(days=i)).isoformat(), 0
        )
        for i in range(14)
    }

    def moving_average(n: int):
        scores = [
            row.score
            for row in base_query.order_by(
                models.GameSession.played_at.desc(), models.GameSession.id.desc()
            )
            .limit(n)
            .all()
        ]
        if not scores:
            return None
        return round(sum(scores) / len(scores), 1)

    return schemas.StatsOut(
        best_score=best_score,
        total_games=total_games,
        total_fruits_merged=total_fruits_merged,
        tier_distribution=tier_distribution,
        games_per_day=games_per_day,
        moving_average=schemas.MovingAverageOut(
            last_7=moving_average(7), last_30=moving_average(30)
        ),
    )


@app.delete("/devices/{device_uuid}/reset", response_model=schemas.ResetOut)
def reset_device(device_uuid: str, db: Session = Depends(get_db)):
    device = (
        db.query(models.Device)
        .filter(models.Device.device_uuid == device_uuid)
        .first()
    )
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    deleted = (
        db.query(models.GameSession)
        .filter(models.GameSession.device_uuid == device_uuid)
        .delete()
    )
    db.commit()
    return schemas.ResetOut(device_uuid=device_uuid, sessions_deleted=deleted)
