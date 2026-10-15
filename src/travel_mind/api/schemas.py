from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from travel_mind.domain.evaluation import ValidationReport
from travel_mind.domain.execution import TravelExecutionEvent
from travel_mind.domain.itinerary import TravelPlan
from travel_mind.domain.trip_request import TripRequest


class TravelPlanRequest(BaseModel):
    """创建旅行计划的 API 请求。"""

    message: str = Field(
        min_length=1,
        max_length=4000,
        description="用户使用自然语言描述的旅行需求",
    )
    thread_id: str | None = Field(
        default=None,
        max_length=100,
        description="会话编号；第一次请求可以不传，后续请求需要传回",
    )


class TravelPlanResponse(BaseModel):
    """旅行规划工作流的 API 响应。"""

    thread_id: str
    status: Literal[
        "needs_clarification",
        "completed",
        "failed",
    ]

    clarification_question: str | None = None
    trip_request: TripRequest | None = None
    travel_plan: TravelPlan | None = None
    validation_report: ValidationReport | None = None
    error: str | None = None


class TravelPlanVersion(BaseModel):
    """旅行计划的一个历史版本。"""

    version: int
    checkpoint_id: str
    created_at: datetime | None = None
    operation: Literal["plan", "replan"] = "plan"
    execution_event: TravelExecutionEvent | None = None
    trip_request: TripRequest
    travel_plan: TravelPlan
    validation_report: ValidationReport


class TravelPlanHistoryResponse(BaseModel):
    """旅行计划的版本历史。"""

    thread_id: str
    versions: list[TravelPlanVersion]


class TravelPlanRevisionRequest(BaseModel):
    """调整已有旅行计划的请求。"""

    instruction: str = Field(
        min_length=1,
        max_length=2000,
        description="用户对已有行程提出的调整要求",
    )


class DeleteTravelPlanResponse(BaseModel):
    """删除旅行规划记录的响应。"""

    thread_id: str
    status: Literal["deleted"]
