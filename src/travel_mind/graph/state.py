from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from travel_mind.domain.evaluation import ValidationReport
from travel_mind.domain.execution import TravelExecutionEvent
from travel_mind.domain.itinerary import TravelPlan
from travel_mind.domain.trip_request import TripRequest, TripRequestDraft

WorkflowRoute = Literal[
    "ask_user",
    "plan",
    "approved",
    "revise",
    "failed",
]
WorkflowOperation = Literal[
    "plan",
    "replan",
]


class TravelState(TypedDict, total=False):
    """TravelMind 工作流中所有节点共享的状态。"""

    messages: Annotated[list[AnyMessage], add_messages]

    operation: WorkflowOperation
    execution_event: TravelExecutionEvent | None

    trip_draft: TripRequestDraft | None
    trip_request: TripRequest | None
    travel_plan: TravelPlan | None
    previous_travel_plan: TravelPlan | None
    validation_report: ValidationReport | None

    clarification_question: str | None
    next_step: WorkflowRoute
    revision_count: int
    research_rounds: int

    error: str | None
