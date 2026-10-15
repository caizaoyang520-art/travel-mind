import pytest
from langchain_core.messages import AIMessage

from travel_mind.graph.workflow import (
    route_after_evaluator,
    route_after_research,
    route_after_supervisor,
    route_start,
)


def test_normal_plan_starts_with_supervisor() -> None:
    state = {
        "operation": "plan",
    }

    assert route_start(state) == "supervisor"


def test_replan_starts_with_research() -> None:
    state = {
        "operation": "replan",
    }

    assert route_start(state) == "planner_research"


def test_research_routes_to_planner_without_tool_call() -> None:
    state = {
        "messages": [
            AIMessage(content="资料查询完成"),
        ],
    }

    assert route_after_research(state) == "planner"


def test_research_routes_to_tools_with_tool_call() -> None:
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_travel_knowledge",
                        "args": {"query": "杭州旅行"},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            ),
        ],
    }

    assert route_after_research(state) == "tools"


@pytest.mark.parametrize(
    ("next_step", "expected"),
    [
        ("approved", "approved"),
        ("revise", "revise"),
        ("failed", "failed"),
    ],
)
def test_evaluator_accepts_valid_routes(
    next_step: str,
    expected: str,
) -> None:
    state = {
        "next_step": next_step,
    }

    assert route_after_evaluator(state) == expected


def test_evaluator_rejects_invalid_route() -> None:
    state = {
        "next_step": "unknown",
    }

    with pytest.raises(
        ValueError,
        match="无效的 Evaluator 路由",
    ):
        route_after_evaluator(state)


def test_supervisor_routes_to_ask_user() -> None:
    state = {
        "next_step": "ask_user",
    }

    assert route_after_supervisor(state) == "ask_user"


def test_supervisor_routes_to_plan() -> None:
    state = {
        "next_step": "plan",
    }

    assert route_after_supervisor(state) == "plan"
