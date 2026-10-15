from datetime import date
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from travel_mind.api.routes import router
from travel_mind.domain.trip_request import TripRequest


class FakeTravelGraph:
    async def ainvoke(
        self,
        input_data: dict,
        config: dict,
    ) -> dict:
        return {
            "next_step": "ask_user",
            "clarification_question": "你计划哪天出发？",
            "error": None,
        }


def test_create_plan_returns_clarification_question() -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.travel_graph = FakeTravelGraph()

    client = TestClient(app)

    response = client.post(
        "/api/v1/travel/plans",
        json={
            "message": "我想从上海去杭州旅行",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "needs_clarification"
    assert body["clarification_question"] == "你计划哪天出发？"
    assert body["thread_id"]


def test_create_plan_rejects_empty_message() -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.travel_graph = FakeTravelGraph()

    client = TestClient(app)

    response = client.post(
        "/api/v1/travel/plans",
        json={
            "message": "",
        },
    )

    assert response.status_code == 422


class FailingTravelGraph:
    async def ainvoke(
        self,
        input_data: dict,
        config: dict,
    ) -> dict:
        raise RuntimeError("模拟工作流错误")


def test_create_plan_returns_500_when_workflow_fails() -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.travel_graph = FailingTravelGraph()

    client = TestClient(app)

    response = client.post(
        "/api/v1/travel/plans",
        json={
            "message": "从上海去杭州旅行三天",
        },
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "旅行规划工作流执行失败。",
    }


class MissingPlanGraph:
    async def aget_state(
        self,
        config: dict,
    ) -> SimpleNamespace:
        return SimpleNamespace(values={})


def test_get_missing_plan_returns_404() -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.travel_graph = MissingPlanGraph()

    client = TestClient(app)

    response = client.get(
        "/api/v1/travel/plans/not-found",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "没有找到对应的旅行规划记录。",
    }


class ExistingPlanGraph:
    async def aget_state(
        self,
        config: dict,
    ) -> SimpleNamespace:
        trip_request = TripRequest(
            start_city="上海",
            end_city="杭州",
            start_date=date(2026, 10, 20),
            end_date=date(2026, 10, 22),
            travelers=2,
            budget=3000,
        )

        return SimpleNamespace(
            values={
                "next_step": "approved",
                "trip_request": trip_request,
                "travel_plan": object(),
            }
        )


def test_event_date_must_be_inside_trip_dates() -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.travel_graph = ExistingPlanGraph()

    client = TestClient(app)

    response = client.post(
        "/api/v1/travel/plans/thread-1/events",
        json={
            "event_type": "weather_change",
            "description": "杭州突降暴雨",
            "affected_date": "2026-10-25",
            "occurred_time": "14:00:00",
            "current_location": "杭州市西湖区",
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "事件影响日期不在旅行日期范围内。",
    }


class UnfinishedPlanGraph:
    async def aget_state(
        self,
        config: dict,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            values={
                "next_step": "ask_user",
                "clarification_question": "请补充旅行日期",
            }
        )


def test_event_requires_completed_plan() -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.travel_graph = UnfinishedPlanGraph()

    client = TestClient(app)

    response = client.post(
        "/api/v1/travel/plans/thread-1/events",
        json={
            "event_type": "weather_change",
            "description": "杭州突降暴雨",
            "affected_date": "2026-10-21",
            "occurred_time": "14:00:00",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "只有已经完成的旅行计划才能上报事件。",
    }


class CompletedPlanGraph:
    async def ainvoke(
        self,
        input_data: dict,
        config: dict,
    ) -> dict:
        return {
            "next_step": "approved",
            "trip_request": {
                "start_city": "上海",
                "end_city": "杭州",
                "start_date": "2026-10-20",
                "end_date": "2026-10-20",
                "travelers": 2,
                "budget": 3000,
            },
            "travel_plan": {
                "start_city": "上海",
                "end_city": "杭州",
                "summary": "杭州一日游",
                "days": [
                    {
                        "date": "2026-10-20",
                        "theme": "西湖游览",
                        "activities": [
                            {
                                "start_time": "09:00:00",
                                "end_time": "11:00:00",
                                "title": "游览西湖",
                                "activity_type": "attraction",
                                "location": "西湖",
                                "description": "游览西湖景区",
                                "estimated_cost": 0,
                            }
                        ],
                        "estimated_daily_cost": 0,
                    }
                ],
                "total_estimated_cost": 0,
            },
            "validation_report": {
                "passed": True,
                "issues": [],
            },
            "error": None,
        }


def test_create_plan_returns_completed_plan() -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.travel_graph = CompletedPlanGraph()

    client = TestClient(app)

    response = client.post(
        "/api/v1/travel/plans",
        json={
            "message": "从上海去杭州一日游",
            "thread_id": "thread-1",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["thread_id"] == "thread-1"
    assert body["status"] == "completed"
    assert body["trip_request"]["end_city"] == "杭州"
    assert body["travel_plan"]["summary"] == "杭州一日游"
    assert body["validation_report"]["passed"] is True


class StoredCompletedPlanGraph(CompletedPlanGraph):
    async def aget_state(
        self,
        config: dict,
    ) -> SimpleNamespace:
        result = await self.ainvoke(
            input_data={},
            config=config,
        )
        return SimpleNamespace(values=result)


def test_get_completed_plan() -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.travel_graph = StoredCompletedPlanGraph()

    client = TestClient(app)

    response = client.get(
        "/api/v1/travel/plans/thread-1",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["thread_id"] == "thread-1"
    assert body["status"] == "completed"
    assert body["travel_plan"]["summary"] == "杭州一日游"
    assert body["validation_report"]["passed"] is True


class StoredClarificationGraph(FakeTravelGraph):
    async def aget_state(
        self,
        config: dict,
    ) -> SimpleNamespace:
        result = await self.ainvoke(
            input_data={},
            config=config,
        )
        return SimpleNamespace(values=result)


def test_get_plan_needing_clarification() -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.travel_graph = StoredClarificationGraph()

    client = TestClient(app)

    response = client.get(
        "/api/v1/travel/plans/thread-1",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "needs_clarification"
    assert body["clarification_question"] == "你计划哪天出发？"
    assert body["travel_plan"] is None


class DeletablePlanGraph:
    async def aget_state(
        self,
        config: dict,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            values={
                "next_step": "approved",
            }
        )


class FakeCheckpointer:
    def __init__(self) -> None:
        self.deleted_thread_id: str | None = None

    async def adelete_thread(
        self,
        thread_id: str,
    ) -> None:
        self.deleted_thread_id = thread_id


def test_delete_travel_plan() -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.travel_graph = DeletablePlanGraph()

    checkpointer = FakeCheckpointer()
    app.state.travel_checkpointer = checkpointer

    client = TestClient(app)

    response = client.delete(
        "/api/v1/travel/plans/thread-1",
    )

    assert response.status_code == 200
    assert response.json() == {
        "thread_id": "thread-1",
        "status": "deleted",
    }
    assert checkpointer.deleted_thread_id == "thread-1"


class SuccessfulEventGraph(ExistingPlanGraph):
    def __init__(self) -> None:
        self.last_input: dict | None = None

    async def ainvoke(
        self,
        input_data: dict,
        config: dict,
    ) -> dict:
        self.last_input = input_data

        return await CompletedPlanGraph().ainvoke(
            input_data=input_data,
            config=config,
        )


def test_event_triggers_replan() -> None:
    app = FastAPI()
    app.include_router(router)

    graph = SuccessfulEventGraph()
    app.state.travel_graph = graph

    client = TestClient(app)

    response = client.post(
        "/api/v1/travel/plans/thread-1/events",
        json={
            "event_type": "weather_change",
            "description": "杭州突降暴雨",
            "affected_date": "2026-10-21",
            "occurred_time": "14:00:00",
            "current_location": "杭州市西湖区",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    assert graph.last_input is not None
    assert graph.last_input["operation"] == "replan"
    assert graph.last_input["execution_event"].description == "杭州突降暴雨"
    assert graph.last_input["previous_travel_plan"] is not None


class MissingHistoryGraph:
    async def aget_state_history(
        self,
        config: dict,
        limit: int,
    ):
        if False:
            yield None


def test_missing_history_returns_404() -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.travel_graph = MissingHistoryGraph()

    client = TestClient(app)

    response = client.get(
        "/api/v1/travel/plans/thread-1/history",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "没有找到对应的旅行规划记录。",
    }


class ExistingHistoryGraph:
    async def aget_state_history(
        self,
        config: dict,
        limit: int,
    ):
        state = await CompletedPlanGraph().ainvoke(
            input_data={},
            config=config,
        )
        state["operation"] = "plan"

        yield SimpleNamespace(
            values=state,
            next=(),
            config={
                "configurable": {
                    "checkpoint_id": "checkpoint-1",
                }
            },
            created_at=None,
        )


def test_get_travel_plan_history() -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.travel_graph = ExistingHistoryGraph()

    client = TestClient(app)

    response = client.get(
        "/api/v1/travel/plans/thread-1/history",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["thread_id"] == "thread-1"
    assert len(body["versions"]) == 1
    assert body["versions"][0]["version"] == 1
    assert body["versions"][0]["checkpoint_id"] == "checkpoint-1"
    assert body["versions"][0]["operation"] == "plan"
