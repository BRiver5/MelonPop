from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

# A single game can't realistically exceed this; used to reject junk submissions.
MAX_REASONABLE_SCORE = 1_000_000
MAX_REASONABLE_MERGES = 100_000
MAX_REASONABLE_DURATION = 24 * 60 * 60  # one day, in seconds


class DeviceRegisterIn(BaseModel):
    device_uuid: str = Field(min_length=8, max_length=64)


class DeviceOut(BaseModel):
    device_uuid: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionIn(BaseModel):
    device_uuid: str = Field(min_length=8, max_length=64)
    score: int = Field(ge=0, le=MAX_REASONABLE_SCORE)
    highest_tier_reached: int = Field(ge=1, le=11)
    fruits_merged: int = Field(ge=0, le=MAX_REASONABLE_MERGES)
    duration_seconds: int = Field(ge=0, le=MAX_REASONABLE_DURATION)


class SessionOut(BaseModel):
    id: int
    device_uuid: str
    score: int
    highest_tier_reached: int
    fruits_merged: int
    duration_seconds: int
    played_at: datetime

    model_config = {"from_attributes": True}


class SessionCreatedOut(BaseModel):
    session: SessionOut
    best_score: int


class MovingAverageOut(BaseModel):
    last_7: Optional[float]
    last_30: Optional[float]


class StatsOut(BaseModel):
    best_score: int
    total_games: int
    total_fruits_merged: int
    tier_distribution: Dict[int, int]
    games_per_day: Dict[str, int]  # ISO date -> count, last 14 days
    moving_average: MovingAverageOut


class ResetOut(BaseModel):
    device_uuid: str
    sessions_deleted: int


class SessionListOut(BaseModel):
    sessions: List[SessionOut]
