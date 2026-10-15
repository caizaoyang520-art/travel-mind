from datetime import date, time

from travel_mind.domain.execution import (
    TravelEventType,
    TravelExecutionEvent,
)
from travel_mind.domain.itinerary import (
    ActivityType,
    DayPlan,
    ItineraryActivity,
    TravelPlan,
)
from travel_mind.domain.trip_request import TripRequest
from travel_mind.validators.itinerary import validate_travel_plan


def build_activity(title: str) -> ItineraryActivity:
    return ItineraryActivity(
        start_time=time(9, 0),
        end_time=time(10, 0),
        title=title,
        activity_type=ActivityType.ATTRACTION,
        location="杭州",
        description="测试活动",
        estimated_cost=100,
    )


def build_plan() -> TravelPlan:
    return TravelPlan(
        start_city="上海",
        end_city="杭州",
        summary="测试行程",
        days=[
            DayPlan(
                date=date(2026, 10, 20),
                theme="西湖游览",
                activities=[build_activity("游览西湖")],
                estimated_daily_cost=100,
            ),
            DayPlan(
                date=date(2026, 10, 21),
                theme="城市游览",
                activities=[build_activity("参观博物馆")],
                estimated_daily_cost=100,
            ),
        ],
        total_estimated_cost=200,
    )


def test_replan_rejects_changed_completed_day() -> None:
    trip_request = TripRequest(
        start_city="上海",
        end_city="杭州",
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 21),
        travelers=2,
        budget=3000,
    )

    previous_plan = build_plan()
    updated_plan = previous_plan.model_copy(deep=True)

    # 错误地修改事件发生前已经完成的行程
    updated_plan.days[0].theme = "被修改的行程"

    event = TravelExecutionEvent(
        event_type=TravelEventType.WEATHER_CHANGE,
        description="杭州突降暴雨",
        affected_date=date(2026, 10, 21),
        occurred_time=time(14, 0),
        current_location="杭州市西湖区",
    )

    report = validate_travel_plan(
        trip_request=trip_request,
        travel_plan=updated_plan,
        previous_travel_plan=previous_plan,
        execution_event=event,
    )

    assert report.passed is False
    assert "completed_day_changed" in {issue.code for issue in report.issues}


def test_replan_rejects_changed_completed_activity() -> None:
    trip_request = TripRequest(
        start_city="上海",
        end_city="杭州",
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 21),
        travelers=2,
        budget=3000,
    )

    previous_plan = build_plan()
    updated_plan = previous_plan.model_copy(deep=True)

    # 修改事件发生当天14:00之前已经完成的活动
    updated_plan.days[1].activities[0].title = "被修改的活动"

    event = TravelExecutionEvent(
        event_type=TravelEventType.WEATHER_CHANGE,
        description="杭州突降暴雨",
        affected_date=date(2026, 10, 21),
        occurred_time=time(14, 0),
        current_location="杭州市西湖区",
    )

    report = validate_travel_plan(
        trip_request=trip_request,
        travel_plan=updated_plan,
        previous_travel_plan=previous_plan,
        execution_event=event,
    )

    assert report.passed is False
    assert "completed_activities_changed" in {issue.code for issue in report.issues}


def test_replan_allows_changing_future_activity() -> None:
    trip_request = TripRequest(
        start_city="上海",
        end_city="杭州",
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 21),
        travelers=2,
        budget=3000,
    )

    previous_plan = build_plan()
    previous_plan.days[1].activities.append(
        ItineraryActivity(
            start_time=time(15, 0),
            end_time=time(16, 0),
            title="下午游览景点",
            activity_type=ActivityType.ATTRACTION,
            location="杭州",
            description="下午活动",
            estimated_cost=100,
        )
    )
    previous_plan.days[1].estimated_daily_cost = 200
    previous_plan.total_estimated_cost = 300

    updated_plan = previous_plan.model_copy(deep=True)

    # 14:00之后的活动允许重新规划
    updated_plan.days[1].activities[1].title = "调整后的下午活动"

    event = TravelExecutionEvent(
        event_type=TravelEventType.WEATHER_CHANGE,
        description="杭州突降暴雨",
        affected_date=date(2026, 10, 21),
        occurred_time=time(14, 0),
        current_location="杭州市西湖区",
    )

    report = validate_travel_plan(
        trip_request=trip_request,
        travel_plan=updated_plan,
        previous_travel_plan=previous_plan,
        execution_event=event,
    )

    assert report.passed is True
    assert "completed_activities_changed" not in {issue.code for issue in report.issues}


def test_plan_rejects_budget_exceeded() -> None:
    trip_request = TripRequest(
        start_city="上海",
        end_city="杭州",
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 21),
        travelers=2,
        budget=150,
    )

    travel_plan = build_plan()

    report = validate_travel_plan(
        trip_request=trip_request,
        travel_plan=travel_plan,
    )

    assert report.passed is False
    assert "budget_exceeded" in {issue.code for issue in report.issues}


def test_plan_rejects_activity_time_conflict() -> None:
    trip_request = TripRequest(
        start_city="上海",
        end_city="杭州",
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 21),
        travelers=2,
        budget=3000,
    )

    travel_plan = build_plan()
    travel_plan.days[0].activities.append(
        ItineraryActivity(
            start_time=time(9, 30),
            end_time=time(11, 0),
            title="时间冲突活动",
            activity_type=ActivityType.ATTRACTION,
            location="杭州",
            description="与前一个活动时间重叠",
            estimated_cost=50,
        )
    )
    travel_plan.days[0].estimated_daily_cost = 150
    travel_plan.total_estimated_cost = 250

    report = validate_travel_plan(
        trip_request=trip_request,
        travel_plan=travel_plan,
    )

    assert report.passed is False
    assert "activity_time_conflict" in {issue.code for issue in report.issues}
