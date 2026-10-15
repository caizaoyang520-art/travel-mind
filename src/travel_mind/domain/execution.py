from datetime import date, time
from enum import StrEnum

from pydantic import BaseModel, Field


class TravelEventType(StrEnum):
    """旅行途中可能触发重新规划的事件类型。"""

    WEATHER_CHANGE = "weather_change"
    ATTRACTION_CLOSED = "attraction_closed"
    TRANSPORT_DELAY = "transport_delay"
    USER_CHANGE = "user_change"
    OTHER = "other"


class TravelExecutionEvent(BaseModel):
    """旅行途中发生、需要调整后续行程的事件。"""

    event_type: TravelEventType = Field(
        description="事件类型",
    )
    description: str = Field(
        min_length=1,
        max_length=1000,
        description="事件的具体情况",
    )
    affected_date: date = Field(
        description="事件影响的行程日期",
    )
    occurred_time: time | None = Field(
        default=None,
        description="事件发生时间；不填写时重新规划当天全部行程",
    )
    current_location: str | None = Field(
        default=None,
        max_length=100,
        description="用户当前所在位置",
    )
