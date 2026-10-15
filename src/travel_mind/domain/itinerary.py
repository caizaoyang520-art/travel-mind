from datetime import date as Date
from datetime import time as Time
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class ActivityType(StrEnum):
    ATTRACTION = "attraction"
    DINING = "dining"
    TRANSPORT = "transport"
    REST = "rest"
    OTHER = "other"


class ItineraryActivity(BaseModel):
    start_time: Time = Field(description="活动开始时间")
    end_time: Time = Field(description="活动结束时间")
    title: str = Field(min_length=1, description="活动名称")
    activity_type: ActivityType = Field(description="活动类型")
    location: str = Field(min_length=1, description="活动地点")
    description: str = Field(min_length=1, description="活动说明")
    estimated_cost: float = Field(ge=0, description="预计花费，单位为人民币元")
    transport_to_next: str | None = Field(
        default=None, description="前往下一个地点的交通建议"
    )
    source_refs: list[str] = Field(
        default_factory=list, description="天气、景点或知识库来源编号"
    )

    @model_validator(mode="after")
    def validate_activity_time(self) -> "ItineraryActivity":
        if self.end_time <= self.start_time:
            raise ValueError("活动结束时间必须晚于开始时间")
        return self


class DayPlan(BaseModel):
    date: Date = Field(description="行程日期")
    theme: str = Field(min_length=1, description="当日行程主题")
    activities: list[ItineraryActivity] = Field(
        min_length=1, description="当天活动列表"
    )
    estimated_daily_cost: float = Field(ge=0, description="当天预计总花费")


class TravelPlan(BaseModel):
    start_city: str = Field(min_length=1, description="出发城市")
    end_city: str = Field(min_length=1, description="目的地城市")
    summary: str = Field(min_length=1, description="行程总体说明")
    days: list[DayPlan] = Field(min_length=1, max_length=7, description="每日行程")
    total_estimated_cost: float = Field(ge=0, description="行程预计总花费")
    notices: list[str] = Field(default_factory=list, description="天气、安全和出行提醒")
