"""
Agent 6: UMBRELLA-EVO Configuration
Configurable observation time-frames (24h, 48h, 1w, 2w, 1m) and learning parameters.
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ObservationTimeFrame(str, Enum):
    HOURS_24 = "24h"
    HOURS_48 = "48h"
    WEEK_1 = "1w"
    WEEKS_2 = "2w"
    MONTH_1 = "1m"


class EVOConfig(BaseModel):
    time_frame: ObservationTimeFrame = Field(
        default=ObservationTimeFrame.HOURS_24,
        description="Observation time window for evaluating backend stress patterns"
    )
    saturation_threshold_pct: float = Field(
        default=80.0,
        description="Pool/resource saturation percentage that triggers proactive refactoring"
    )
    min_events_trigger: int = Field(
        default=1,
        description="Minimum historical stress events required in the time window to formulate proposals"
    )
    target_scaled_pool_size: int = Field(
        default=20,
        description="Proactively proposed baseline pool size"
    )
    target_scaled_overflow: int = Field(
        default=10,
        description="Proactively proposed baseline max overflow"
    )
    learning_rate_alpha: float = Field(
        default=0.25,
        ge=0.01,
        le=1.0,
        description="Q-learning rate"
    )
    discount_factor_gamma: float = Field(
        default=0.90,
        ge=0.0,
        le=1.0,
        description="Reinforcement learning discount factor"
    )
    auto_evolution_mode: bool = Field(
        default=False,
        description="Whether proactive refactoring proposals require Human-in-the-Loop review"
    )

    @classmethod
    def get_time_frame_seconds(cls, time_frame: ObservationTimeFrame) -> int:
        """Returns the window duration in seconds."""
        mapping = {
            ObservationTimeFrame.HOURS_24: 24 * 3600,
            ObservationTimeFrame.HOURS_48: 48 * 3600,
            ObservationTimeFrame.WEEK_1: 7 * 24 * 3600,
            ObservationTimeFrame.WEEKS_2: 14 * 24 * 3600,
            ObservationTimeFrame.MONTH_1: 30 * 24 * 3600,
        }
        return mapping.get(time_frame, 24 * 3600)
