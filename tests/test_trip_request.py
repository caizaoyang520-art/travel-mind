from datetime import date

import pytest
from pydantic import ValidationError

from travel_mind.domain.trip_request import TripRequest, TripRequestDraft


def test_trip_days_includes_start_and_end_dates() -> None:
    trip_request = TripRequest(
        start_city="上海",
        end_city="杭州",
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 22),
        travelers=2,
        budget=3000,
    )

    assert trip_request.trip_days == 3


def test_end_date_cannot_be_before_start_date() -> None:
    with pytest.raises(
        ValidationError,
        match="结束日期不能早于开始日期",
    ):
        TripRequest(
            start_city="上海",
            end_city="杭州",
            start_date=date(2026, 10, 22),
            end_date=date(2026, 10, 20),
            travelers=2,
            budget=3000,
        )


def test_trip_cannot_exceed_seven_days() -> None:
    with pytest.raises(
        ValidationError,
        match="第一版最多支持7天行程",
    ):
        TripRequest(
            start_city="上海",
            end_city="杭州",
            start_date=date(2026, 10, 20),
            end_date=date(2026, 10, 27),
            travelers=2,
            budget=3000,
        )


def test_trip_request_draft_reports_missing_fields() -> None:
    draft = TripRequestDraft(
        start_city="上海",
        end_city="杭州",
    )

    assert draft.missing_fields == [
        "start_date",
        "end_date",
        "travelers",
        "budget",
    ]
