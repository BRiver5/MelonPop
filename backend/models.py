from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    device_uuid = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow)


class GameSession(Base):
    __tablename__ = "game_sessions"

    id = Column(Integer, primary_key=True)
    device_uuid = Column(
        String, ForeignKey("devices.device_uuid"), nullable=False, index=True
    )
    score = Column(Integer, nullable=False)
    highest_tier_reached = Column(Integer, nullable=False)  # 1-10, 11 = watermelon
    fruits_merged = Column(Integer, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    played_at = Column(DateTime, default=utcnow, index=True)
