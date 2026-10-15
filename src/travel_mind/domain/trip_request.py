from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class TravelPace(StrEnum):
    RELAXED = "relaxed"
    BALANCED = "balanced"
    INTENSIVE = "intensive"


class TripRequest(BaseModel):
    start_city: str = Field(
        min_length=1,
        description="出发城市",
    )
    end_city: str = Field(
        min_length=1,
        description="目的地城市",
    )
    start_date: date = Field(
        description="旅行开始日期",
    )
    end_date: date = Field(
        description="旅行结束日期",
    )
    travelers: int = Field(
        ge=1,
        le=20,
        description="旅行人数",
    )
    budget: float = Field(
        gt=0,
        description="旅行总预算，单位为人民币元",
    )
    preferences: list[str] = Field(
        default_factory=list,
        description="用户旅行偏好，例如自然风景、美食、历史文化",
    )
    pace: TravelPace = Field(
        default=TravelPace.BALANCED,
        description="旅行节奏",
    )
    special_requirements: list[str] = Field(
        default_factory=list,
        description="特殊要求，例如老人同行、避免爬山",
    )

    @model_validator(mode="after")
    def validate_trip_dates(self) -> "TripRequest":
        if self.end_date < self.start_date:
            raise ValueError("结束日期不能早于开始日期")

        if self.trip_days > 7:
            raise ValueError("第一版最多支持7天行程")

        return self

    @property
    def trip_days(self) -> int:
        return (self.end_date - self.start_date).days + 1


class TripRequestDraft(BaseModel):
    """Supervisor 从用户对话中提取的旅行需求草稿。"""

    start_city: str | None = Field(default=None, description="出发城市")
    end_city: str | None = Field(default=None, description="目的地城市")
    start_date: date | None = Field(default=None, description="旅行开始日期")
    end_date: date | None = Field(default=None, description="旅行结束日期")
    travelers: int | None = Field(default=None, ge=1, le=20, description="旅行人数")
    budget: float | None = Field(
        default=None, gt=0, description="旅行总预算，单位为人民币元"
    )
    preferences: list[str] = Field(
        default_factory=list, description="旅行偏好，例如自然风景、美食、历史文化"
    )
    pace: TravelPace = Field(default=TravelPace.BALANCED, description="旅行节奏")
    special_requirements: list[str] = Field(
        default_factory=list, description="特殊要求，例如老人同行、避免爬山"
    )

    @property
    def missing_fields(self) -> list[str]:
        """返回生成旅行计划前仍需用户补充的字段。"""

        required_fields = [
            "start_city",
            "end_city",
            "start_date",
            "end_date",
            "travelers",
            "budget",
        ]

        return [
            field_name
            for field_name in required_fields
            if getattr(self, field_name) is None
        ]
