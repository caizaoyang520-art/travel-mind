from datetime import timedelta
from itertools import pairwise

from travel_mind.domain.evaluation import (
    IssueSeverity,
    ValidationIssue,
    ValidationReport,
)
from travel_mind.domain.execution import TravelExecutionEvent
from travel_mind.domain.itinerary import TravelPlan
from travel_mind.domain.trip_request import TripRequest


def validate_travel_plan(
    trip_request: TripRequest,
    travel_plan: TravelPlan,
    previous_travel_plan: TravelPlan | None = None,
    execution_event: TravelExecutionEvent | None = None,
) -> ValidationReport:
    """检查行程中的日期、预算、费用和时间冲突。"""

    issues: list[ValidationIssue] = []

    expected_dates = [
        trip_request.start_date + timedelta(days=index)
        for index in range(trip_request.trip_days)
    ]
    actual_dates = [day.date for day in travel_plan.days]

    if actual_dates != expected_dates:
        issues.append(
            ValidationIssue(
                code="date_coverage",
                severity=IssueSeverity.ERROR,
                message="行程日期没有完整覆盖用户要求的旅行日期",
            )
        )

    if previous_travel_plan is not None and execution_event is not None:
        previous_days = {day.date: day for day in previous_travel_plan.days}
        updated_days = {day.date: day for day in travel_plan.days}

        for day_date, previous_day in previous_days.items():
            if day_date >= execution_event.affected_date:
                continue

            updated_day = updated_days.get(day_date)

            if updated_day != previous_day:
                issues.append(
                    ValidationIssue(
                        code="completed_day_changed",
                        severity=IssueSeverity.ERROR,
                        message=(
                            f"{day_date.isoformat()} 的已完成行程在动态重新规划中被修改"
                        ),
                        day=day_date,
                    )
                )

        if execution_event.occurred_time is not None:
            affected_date = execution_event.affected_date
            previous_day = previous_days.get(affected_date)
            updated_day = updated_days.get(affected_date)

            if previous_day is not None and updated_day is not None:
                previous_completed_activities = [
                    activity
                    for activity in previous_day.activities
                    if (activity.end_time <= execution_event.occurred_time)
                ]

                updated_completed_activities = [
                    activity
                    for activity in updated_day.activities
                    if (activity.end_time <= execution_event.occurred_time)
                ]

                if updated_completed_activities != previous_completed_activities:
                    issues.append(
                        ValidationIssue(
                            code="completed_activities_changed",
                            severity=IssueSeverity.ERROR,
                            message=(
                                f"{affected_date.isoformat()} "
                                f"{execution_event.occurred_time.isoformat()} "
                                "之前已完成的活动被修改"
                            ),
                            day=affected_date,
                        )
                    )

    if travel_plan.start_city != trip_request.start_city:
        issues.append(
            ValidationIssue(
                code="start_city_mismatch",
                severity=IssueSeverity.ERROR,
                message="行程中的出发城市与用户需求不一致",
            )
        )

    if travel_plan.end_city != trip_request.end_city:
        issues.append(
            ValidationIssue(
                code="end_city_mismatch",
                severity=IssueSeverity.ERROR,
                message="行程中的目的地城市与用户需求不一致",
            )
        )

    if travel_plan.total_estimated_cost > trip_request.budget:
        issues.append(
            ValidationIssue(
                code="budget_exceeded",
                severity=IssueSeverity.ERROR,
                message=(
                    f"预计费用 {travel_plan.total_estimated_cost:.2f} 元，"
                    f"超过预算 {trip_request.budget:.2f} 元"
                ),
            )
        )

    for day_plan in travel_plan.days:
        activities = sorted(
            day_plan.activities,
            key=lambda activity: activity.start_time,
        )

        for previous, current in pairwise(activities):
            if current.start_time < previous.end_time:
                issues.append(
                    ValidationIssue(
                        code="activity_time_conflict",
                        severity=IssueSeverity.ERROR,
                        message=f"“{previous.title}”与“{current.title}”存在时间冲突",
                        day=day_plan.date,
                    )
                )

        calculated_daily_cost = sum(
            activity.estimated_cost for activity in day_plan.activities
        )

        if abs(calculated_daily_cost - day_plan.estimated_daily_cost) > 1:
            issues.append(
                ValidationIssue(
                    code="daily_cost_mismatch",
                    severity=IssueSeverity.WARNING,
                    message=(
                        f"活动费用合计为 {calculated_daily_cost:.2f} 元，"
                        f"但当天总费用填写为 "
                        f"{day_plan.estimated_daily_cost:.2f} 元"
                    ),
                    day=day_plan.date,
                )
            )

    calculated_total_cost = sum(day.estimated_daily_cost for day in travel_plan.days)

    if abs(calculated_total_cost - travel_plan.total_estimated_cost) > 1:
        issues.append(
            ValidationIssue(
                code="total_cost_mismatch",
                severity=IssueSeverity.WARNING,
                message=(
                    f"每日费用合计为 {calculated_total_cost:.2f} 元，"
                    f"但行程总费用填写为 "
                    f"{travel_plan.total_estimated_cost:.2f} 元"
                ),
            )
        )

    passed = not any(issue.severity == IssueSeverity.ERROR for issue in issues)

    return ValidationReport(
        passed=passed,
        issues=issues,
    )
