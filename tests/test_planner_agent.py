from travel_mind.agents.planner import generate_travel_plan
from travel_mind.domain.itinerary import TravelPlan
from travel_mind.domain.trip_request import TripRequest


class FakeStructuredModel:
    def __init__(self, result: object) -> None:
        self.result = result
        self.received_messages: list = []

    def invoke(
        self,
        messages: list,
    ) -> object:
        self.received_messages = messages
        return self.result


class FakeChatModel:
    def __init__(
        self,
        structured_model: FakeStructuredModel,
    ) -> None:
        self.structured_model = structured_model
        self.schema = None
        self.method = None

    def with_structured_output(
        self,
        schema,
        method: str,
    ) -> FakeStructuredModel:
        self.schema = schema
        self.method = method
        return self.structured_model


def test_generate_first_travel_plan(
    monkeypatch,
) -> None:
    expected_plan = object()
    structured_model = FakeStructuredModel(
        result=expected_plan,
    )
    chat_model = FakeChatModel(structured_model)

    monkeypatch.setattr(
        "travel_mind.agents.planner.get_chat_model",
        lambda: chat_model,
    )

    trip_request = TripRequest(
        start_city="上海",
        end_city="杭州",
        start_date="2026-10-20",
        end_date="2026-10-22",
        travelers=2,
        budget=3000,
    )

    result = generate_travel_plan(
        trip_request=trip_request,
    )

    assert result is expected_plan
    assert chat_model.schema is TravelPlan
    assert chat_model.method == "function_calling"

    prompt = structured_model.received_messages[1].content

    assert "没有可用的工具查询结果" in prompt
    assert "这是首次规划" in prompt
    assert "无，这是第一次生成行程" in prompt


class FakeSerializable:
    def __init__(
        self,
        json_text: str,
    ) -> None:
        self.json_text = json_text

    def model_dump_json(
        self,
        indent: int,
    ) -> str:
        return self.json_text


def test_generate_dynamic_replan_prompt(
    monkeypatch,
) -> None:
    expected_plan = object()
    structured_model = FakeStructuredModel(
        result=expected_plan,
    )
    chat_model = FakeChatModel(structured_model)

    monkeypatch.setattr(
        "travel_mind.agents.planner.get_chat_model",
        lambda: chat_model,
    )

    trip_request = TripRequest(
        start_city="上海",
        end_city="杭州",
        start_date="2026-10-20",
        end_date="2026-10-22",
        travelers=2,
        budget=3000,
    )

    previous_plan = FakeSerializable('{"summary": "原行程"}')
    execution_event = FakeSerializable('{"description": "杭州突降暴雨"}')

    result = generate_travel_plan(
        trip_request=trip_request,
        revision_feedback=[
            "下午活动不适合雨天",
        ],
        tool_context=[
            "工具名称：get_city_weather\n返回结果：暴雨",
        ],
        current_plan=previous_plan,
        execution_event=execution_event,
    )

    assert result is expected_plan

    prompt = structured_model.received_messages[1].content

    assert "原行程" in prompt
    assert "杭州突降暴雨" in prompt
    assert "get_city_weather" in prompt
    assert "下午活动不适合雨天" in prompt
    assert "affected_date 之前的每日行程必须原样保留" in prompt
