from types import SimpleNamespace

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)

from travel_mind.domain.evaluation import (
    IssueSeverity,
    ValidationIssue,
    ValidationReport,
)
from travel_mind.domain.trip_request import (
    TripRequest,
    TripRequestDraft,
)
from travel_mind.graph.nodes import (
    evaluator_node,
    planner_node,
    planner_research_node,
    supervisor_node,
)


def test_supervisor_asks_for_message_when_none_exists() -> None:
    result = supervisor_node(
        {
            "messages": [],
        }
    )

    assert result["next_step"] == "ask_user"
    assert result["error"] == "没有找到用户消息"
    assert isinstance(result["messages"][0], AIMessage)


def test_planner_fails_without_trip_request() -> None:
    result = planner_node(
        {
            "messages": [],
        }
    )

    assert result["travel_plan"] is None
    assert result["error"] == "无法生成行程：旅行需求尚未完整。"
    assert isinstance(result["messages"][0], AIMessage)


def test_evaluator_fails_without_required_data() -> None:
    result = evaluator_node({})

    assert result["next_step"] == "failed"
    assert result["validation_report"] is None
    assert result["error"] == "无法评估行程：缺少旅行需求或旅行计划。"
    assert isinstance(result["messages"][0], AIMessage)


def test_supervisor_asks_for_missing_information(
    monkeypatch,
) -> None:
    def fake_extract_trip_request(
        user_message: str,
    ) -> TripRequestDraft:
        return TripRequestDraft(
            start_city="上海",
            end_city="杭州",
        )

    monkeypatch.setattr(
        "travel_mind.graph.nodes.extract_trip_request",
        fake_extract_trip_request,
    )

    result = supervisor_node(
        {
            "messages": [HumanMessage(content="我想从上海去杭州旅行")],
        }
    )

    assert result["next_step"] == "ask_user"
    assert result["trip_request"] is None
    assert result["clarification_question"] is not None
    assert result["error"] is None


def test_supervisor_creates_complete_trip_request(
    monkeypatch,
) -> None:
    def fake_extract_trip_request(
        user_message: str,
    ) -> TripRequestDraft:
        return TripRequestDraft(
            start_city="上海",
            end_city="杭州",
            start_date="2026-10-20",
            end_date="2026-10-22",
            travelers=2,
            budget=3000,
        )

    monkeypatch.setattr(
        "travel_mind.graph.nodes.extract_trip_request",
        fake_extract_trip_request,
    )

    result = supervisor_node(
        {
            "messages": [HumanMessage(content="从上海去杭州旅行三天")],
        }
    )

    assert result["next_step"] == "plan"
    assert result["trip_request"].end_city == "杭州"
    assert result["trip_request"].trip_days == 3
    assert result["revision_count"] == 0
    assert result["research_rounds"] == 0
    assert result["error"] is None


def test_research_fails_without_trip_request() -> None:
    result = planner_research_node(
        {
            "messages": [],
        }
    )

    assert result["error"] == ("无法查询旅行资料：旅行需求尚未完整。")
    assert isinstance(result["messages"][0], AIMessage)


def test_research_stops_after_maximum_rounds() -> None:
    trip_request = TripRequest(
        start_city="上海",
        end_city="杭州",
        start_date="2026-10-20",
        end_date="2026-10-22",
        travelers=2,
        budget=3000,
    )

    result = planner_research_node(
        {
            "trip_request": trip_request,
            "research_rounds": 4,
            "messages": [],
        }
    )

    assert result["error"] is None
    assert result["messages"][0].content == ("资料查询达到最大轮数，开始生成行程。")


def build_failed_report() -> ValidationReport:
    return ValidationReport(
        passed=False,
        issues=[
            ValidationIssue(
                code="budget_exceeded",
                severity=IssueSeverity.ERROR,
                message="行程费用超过预算",
            )
        ],
    )


def test_evaluator_approves_valid_plan(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "travel_mind.graph.nodes.validate_travel_plan",
        lambda **kwargs: ValidationReport(
            passed=True,
            issues=[],
        ),
    )

    result = evaluator_node(
        {
            "trip_request": object(),
            "travel_plan": object(),
            "revision_count": 0,
        }
    )

    assert result["next_step"] == "approved"
    assert result["validation_report"].passed is True
    assert result["error"] is None


def test_evaluator_requests_revision(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "travel_mind.graph.nodes.validate_travel_plan",
        lambda **kwargs: build_failed_report(),
    )

    result = evaluator_node(
        {
            "trip_request": object(),
            "travel_plan": object(),
            "revision_count": 0,
        }
    )

    assert result["next_step"] == "revise"
    assert result["revision_count"] == 1
    assert result["validation_report"].passed is False


def test_evaluator_fails_after_maximum_revisions(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "travel_mind.graph.nodes.validate_travel_plan",
        lambda **kwargs: build_failed_report(),
    )

    result = evaluator_node(
        {
            "trip_request": object(),
            "travel_plan": object(),
            "revision_count": 2,
        }
    )

    assert result["next_step"] == "failed"
    assert result["validation_report"].passed is False
    assert "达到最大修改次数" in result["messages"][0].content


def test_planner_uses_only_current_run_tool_messages(
    monkeypatch,
) -> None:
    captured_arguments: dict = {}

    def fake_generate_travel_plan(
        **kwargs,
    ) -> SimpleNamespace:
        captured_arguments.update(kwargs)
        return SimpleNamespace(
            summary="测试行程生成完成",
        )

    monkeypatch.setattr(
        "travel_mind.graph.nodes.generate_travel_plan",
        fake_generate_travel_plan,
    )

    result = planner_node(
        {
            "operation": "plan",
            "trip_request": object(),
            "messages": [
                ToolMessage(
                    content="旧的工具资料",
                    tool_call_id="old-call",
                    name="old_tool",
                ),
                HumanMessage(
                    content="请重新规划行程",
                ),
                ToolMessage(
                    content="当前工具资料",
                    tool_call_id="new-call",
                    name="new_tool",
                ),
            ],
        }
    )

    assert captured_arguments["tool_context"] == [
        "工具名称：new_tool\n返回结果：当前工具资料"
    ]
    assert captured_arguments["current_plan"] is None
    assert captured_arguments["execution_event"] is None

    assert result["travel_plan"].summary == "测试行程生成完成"
    assert result["validation_report"] is None
    assert result["error"] is None


def test_replan_passes_previous_plan_and_event_to_planner(
    monkeypatch,
) -> None:
    captured_arguments: dict = {}

    def fake_generate_travel_plan(
        **kwargs,
    ) -> SimpleNamespace:
        captured_arguments.update(kwargs)
        return SimpleNamespace(
            summary="动态重规划完成",
        )

    monkeypatch.setattr(
        "travel_mind.graph.nodes.generate_travel_plan",
        fake_generate_travel_plan,
    )

    previous_plan = object()
    current_plan = object()
    execution_event = object()

    result = planner_node(
        {
            "operation": "replan",
            "trip_request": object(),
            "previous_travel_plan": previous_plan,
            "travel_plan": current_plan,
            "execution_event": execution_event,
            "validation_report": build_failed_report(),
            "messages": [
                HumanMessage(
                    content="杭州突降暴雨，请重新规划",
                )
            ],
        }
    )

    assert captured_arguments["current_plan"] is previous_plan
    assert captured_arguments["execution_event"] is execution_event
    assert captured_arguments["revision_feedback"] == ["行程费用超过预算"]
    assert result["travel_plan"].summary == "动态重规划完成"


def test_research_node_invokes_bound_model(
    monkeypatch,
) -> None:
    class FakeResearchModel:
        def __init__(self) -> None:
            self.received_messages: list = []

        def bind_tools(
            self,
            tools: list,
        ) -> "FakeResearchModel":
            return self

        def invoke(
            self,
            messages: list,
        ) -> AIMessage:
            self.received_messages = messages
            return AIMessage(
                content="资料收集完成",
            )

    fake_model = FakeResearchModel()

    monkeypatch.setattr(
        "travel_mind.graph.nodes.get_chat_model",
        lambda: fake_model,
    )

    trip_request = TripRequest(
        start_city="上海",
        end_city="杭州",
        start_date="2026-10-20",
        end_date="2026-10-22",
        travelers=2,
        budget=3000,
    )

    result = planner_research_node(
        {
            "operation": "plan",
            "trip_request": trip_request,
            "research_rounds": 0,
            "messages": [
                HumanMessage(
                    content="从上海去杭州旅行三天",
                )
            ],
        }
    )

    assert result["research_rounds"] == 1
    assert result["error"] is None
    assert result["messages"][0].content == "资料收集完成"
    assert len(fake_model.received_messages) == 2
