from datetime import date

import pytest

from travel_mind.agents.supervisor import (
    build_clarification_question,
    extract_trip_request,
    finalize_trip_request,
)
from travel_mind.domain.trip_request import TripRequestDraft


def test_builds_question_for_missing_fields() -> None:
    draft = TripRequestDraft(
        start_city="上海",
        end_city="杭州",
    )

    question = build_clarification_question(draft)

    assert question == (
        "为了帮你制定行程，还需要确认："
        "你计划哪天出发；"
        "你计划哪天结束行程；"
        "这次旅行一共有几个人；"
        "整个行程的总预算大约是多少元。"
    )


def test_complete_draft_does_not_need_question() -> None:
    draft = TripRequestDraft(
        start_city="上海",
        end_city="杭州",
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 22),
        travelers=2,
        budget=3000,
    )

    assert build_clarification_question(draft) is None


def test_finalizes_complete_trip_request() -> None:
    draft = TripRequestDraft(
        start_city="上海",
        end_city="杭州",
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 22),
        travelers=2,
        budget=3000,
    )

    trip_request = finalize_trip_request(draft)

    assert trip_request.start_city == "上海"
    assert trip_request.end_city == "杭州"
    assert trip_request.trip_days == 3


def test_incomplete_draft_cannot_be_finalized() -> None:
    draft = TripRequestDraft(
        start_city="上海",
        end_city="杭州",
    )

    with pytest.raises(
        ValueError,
        match="旅行需求不完整",
    ):
        finalize_trip_request(draft)


def test_extract_trip_request_uses_structured_output(
    monkeypatch,
) -> None:
    expected_draft = TripRequestDraft(
        start_city="上海",
        end_city="杭州",
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 22),
        travelers=2,
        budget=3000,
    )

    class FakeStructuredModel:
        def invoke(
            self,
            messages: list,
        ) -> TripRequestDraft:
            assert messages[1].content == ("从上海去杭州旅行三天")
            return expected_draft

    class FakeChatModel:
        def with_structured_output(
            self,
            schema,
            method: str,
        ) -> FakeStructuredModel:
            assert schema is TripRequestDraft
            assert method == "function_calling"
            return FakeStructuredModel()

    monkeypatch.setattr(
        "travel_mind.agents.supervisor.get_chat_model",
        lambda: FakeChatModel(),
    )

    result = extract_trip_request("从上海去杭州旅行三天")

    assert result is expected_draft
