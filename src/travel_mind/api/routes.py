from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import HumanMessage

from travel_mind.api.schemas import (
    DeleteTravelPlanResponse,
    TravelPlanHistoryResponse,
    TravelPlanRequest,
    TravelPlanResponse,
    TravelPlanRevisionRequest,
    TravelPlanVersion,
)
from travel_mind.domain.execution import TravelExecutionEvent

router = APIRouter(
    prefix="/api/v1/travel",
    tags=["旅行规划"],
)


@router.post(
    "/plans",
    response_model=TravelPlanResponse,
)
async def create_travel_plan(
    request: TravelPlanRequest,
    http_request: Request,
) -> TravelPlanResponse:
    """根据用户的自然语言需求创建旅行计划。"""

    travel_graph = http_request.app.state.travel_graph
    thread_id = request.thread_id or str(uuid4())

    try:
        result = await travel_graph.ainvoke(
            {
                "operation": "plan",
                "execution_event": None,
                "previous_travel_plan": None,
                "messages": [HumanMessage(content=request.message)],
            },
            config={
                "configurable": {
                    "thread_id": thread_id,
                },
                "recursion_limit": 30,
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="旅行规划工作流执行失败。",
        ) from exc

    next_step = result.get("next_step")

    if next_step == "ask_user":
        return TravelPlanResponse(
            thread_id=thread_id,
            status="needs_clarification",
            clarification_question=result.get("clarification_question"),
            error=result.get("error"),
        )

    if next_step == "approved":
        return TravelPlanResponse(
            thread_id=thread_id,
            status="completed",
            trip_request=result.get("trip_request"),
            travel_plan=result.get("travel_plan"),
            validation_report=result.get("validation_report"),
            error=None,
        )

    return TravelPlanResponse(
        thread_id=thread_id,
        status="failed",
        trip_request=result.get("trip_request"),
        travel_plan=result.get("travel_plan"),
        validation_report=result.get("validation_report"),
        error=(result.get("error") or "旅行计划未通过最终校验。"),
    )


@router.get(
    "/plans/{thread_id}",
    response_model=TravelPlanResponse,
)
async def get_travel_plan(
    thread_id: str,
    http_request: Request,
) -> TravelPlanResponse:
    """根据会话编号查询最近一次旅行规划状态。"""

    travel_graph = http_request.app.state.travel_graph

    try:
        snapshot = await travel_graph.aget_state(
            {
                "configurable": {
                    "thread_id": thread_id,
                }
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="读取旅行规划记录失败。",
        ) from exc

    state = snapshot.values

    if not state:
        raise HTTPException(
            status_code=404,
            detail="没有找到对应的旅行规划记录。",
        )

    next_step = state.get("next_step")

    if next_step == "ask_user":
        return TravelPlanResponse(
            thread_id=thread_id,
            status="needs_clarification",
            clarification_question=state.get("clarification_question"),
            error=state.get("error"),
        )

    if next_step == "approved":
        return TravelPlanResponse(
            thread_id=thread_id,
            status="completed",
            trip_request=state.get("trip_request"),
            travel_plan=state.get("travel_plan"),
            validation_report=state.get("validation_report"),
            error=None,
        )

    return TravelPlanResponse(
        thread_id=thread_id,
        status="failed",
        trip_request=state.get("trip_request"),
        travel_plan=state.get("travel_plan"),
        validation_report=state.get("validation_report"),
        error=(state.get("error") or "旅行计划尚未完成或未通过校验。"),
    )


@router.get(
    "/plans/{thread_id}/history",
    response_model=TravelPlanHistoryResponse,
)
async def get_travel_plan_history(
    thread_id: str,
    http_request: Request,
) -> TravelPlanHistoryResponse:
    """查询旅行计划所有已通过校验的历史版本。"""

    travel_graph = http_request.app.state.travel_graph
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    snapshots = []
    thread_exists = False

    try:
        async for snapshot in travel_graph.aget_state_history(
            config,
            limit=100,
        ):
            thread_exists = True
            state = snapshot.values

            if (
                state.get("next_step") == "approved"
                and not snapshot.next
                and state.get("trip_request") is not None
                and state.get("travel_plan") is not None
                and state.get("validation_report") is not None
            ):
                snapshots.append(snapshot)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="读取旅行规划版本历史失败。",
        ) from exc

    if not thread_exists:
        raise HTTPException(
            status_code=404,
            detail="没有找到对应的旅行规划记录。",
        )

    snapshots.reverse()

    versions = [
        TravelPlanVersion(
            version=index,
            checkpoint_id=snapshot.config["configurable"]["checkpoint_id"],
            created_at=snapshot.created_at,
            trip_request=snapshot.values["trip_request"],
            operation=snapshot.values.get(
                "operation",
                "plan",
            ),
            execution_event=snapshot.values.get("execution_event"),
            travel_plan=snapshot.values["travel_plan"],
            validation_report=snapshot.values["validation_report"],
        )
        for index, snapshot in enumerate(
            snapshots,
            start=1,
        )
    ]

    return TravelPlanHistoryResponse(
        thread_id=thread_id,
        versions=versions,
    )


@router.post(
    "/plans/{thread_id}/history/{checkpoint_id}/restore",
    response_model=TravelPlanResponse,
)
async def restore_travel_plan_version(
    thread_id: str,
    checkpoint_id: str,
    http_request: Request,
) -> TravelPlanResponse:
    """将旅行计划恢复到指定的历史版本。"""

    travel_graph = http_request.app.state.travel_graph

    target_config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
        }
    }

    try:
        target_snapshot = await travel_graph.aget_state(target_config)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="读取指定历史版本失败。",
        ) from exc

    target_state = target_snapshot.values

    if not target_state:
        raise HTTPException(
            status_code=404,
            detail="没有找到指定的历史版本。",
        )

    if (
        target_state.get("next_step") != "approved"
        or target_snapshot.next
        or target_state.get("trip_request") is None
        or target_state.get("travel_plan") is None
        or target_state.get("validation_report") is None
    ):
        raise HTTPException(
            status_code=409,
            detail="指定检查点不是可恢复的完整行程版本。",
        )

    try:
        restored_config = await travel_graph.aupdate_state(
            target_snapshot.config,
            {
                "next_step": "approved",
                "error": None,
            },
            as_node="evaluator",
        )

        restored_snapshot = await travel_graph.aget_state(restored_config)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="恢复旅行规划版本失败。",
        ) from exc

    restored_state = restored_snapshot.values

    return TravelPlanResponse(
        thread_id=thread_id,
        status="completed",
        trip_request=restored_state.get("trip_request"),
        travel_plan=restored_state.get("travel_plan"),
        validation_report=restored_state.get("validation_report"),
        error=None,
    )


@router.post(
    "/plans/{thread_id}/events",
    response_model=TravelPlanResponse,
)
async def report_travel_event(
    thread_id: str,
    event: TravelExecutionEvent,
    http_request: Request,
) -> TravelPlanResponse:
    """上报旅行途中事件并重新规划剩余行程。"""

    travel_graph = http_request.app.state.travel_graph
    config = {
        "configurable": {
            "thread_id": thread_id,
        },
        "recursion_limit": 30,
    }

    try:
        snapshot = await travel_graph.aget_state(config)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="读取当前旅行规划失败。",
        ) from exc

    state = snapshot.values

    if not state:
        raise HTTPException(
            status_code=404,
            detail="没有找到对应的旅行规划记录。",
        )

    if (
        state.get("next_step") != "approved"
        or state.get("trip_request") is None
        or state.get("travel_plan") is None
    ):
        raise HTTPException(
            status_code=409,
            detail="只有已经完成的旅行计划才能上报事件。",
        )

    trip_request = state["trip_request"]

    if not (trip_request.start_date <= event.affected_date <= trip_request.end_date):
        raise HTTPException(
            status_code=422,
            detail="事件影响日期不在旅行日期范围内。",
        )

    try:
        result = await travel_graph.ainvoke(
            {
                "operation": "replan",
                "execution_event": event,
                "previous_travel_plan": state["travel_plan"],
                "research_rounds": 0,
                "revision_count": 0,
                "validation_report": None,
                "error": None,
                "messages": [
                    HumanMessage(
                        content=(
                            "旅行途中发生事件，需要重新规划"
                            "受影响时间之后的行程：\n"
                            f"{event.model_dump_json(indent=2)}"
                        )
                    )
                ],
            },
            config=config,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="根据旅行事件重新规划失败。",
        ) from exc

    if result.get("next_step") == "approved":
        return TravelPlanResponse(
            thread_id=thread_id,
            status="completed",
            trip_request=result.get("trip_request"),
            travel_plan=result.get("travel_plan"),
            validation_report=result.get("validation_report"),
            error=None,
        )

    return TravelPlanResponse(
        thread_id=thread_id,
        status="failed",
        trip_request=result.get("trip_request"),
        travel_plan=result.get("travel_plan"),
        validation_report=result.get("validation_report"),
        error=(result.get("error") or "事件发生后的新行程未通过校验。"),
    )


@router.post(
    "/plans/{thread_id}/revisions",
    response_model=TravelPlanResponse,
)
async def revise_travel_plan(
    thread_id: str,
    revision: TravelPlanRevisionRequest,
    http_request: Request,
) -> TravelPlanResponse:
    """根据用户要求重新调整已有旅行计划。"""

    travel_graph = http_request.app.state.travel_graph
    config = {
        "configurable": {
            "thread_id": thread_id,
        },
        "recursion_limit": 30,
    }

    try:
        snapshot = await travel_graph.aget_state(config)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="读取原旅行规划记录失败。",
        ) from exc

    if not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail="没有找到对应的旅行规划记录。",
        )

    if snapshot.values.get("next_step") != "approved":
        raise HTTPException(
            status_code=409,
            detail="只有已经完成的旅行计划才能调整。",
        )

    try:
        result = await travel_graph.ainvoke(
            {
                "operation": "plan",
                "execution_event": None,
                "messages": [
                    HumanMessage(
                        content=(
                            "这是对已有行程的调整要求，"
                            "请结合此前的全部旅行需求重新规划：\n"
                            f"{revision.instruction}"
                        )
                    )
                ],
            },
            config=config,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="调整旅行规划失败。",
        ) from exc

    next_step = result.get("next_step")

    if next_step == "ask_user":
        return TravelPlanResponse(
            thread_id=thread_id,
            status="needs_clarification",
            clarification_question=result.get("clarification_question"),
            error=result.get("error"),
        )

    if next_step == "approved":
        return TravelPlanResponse(
            thread_id=thread_id,
            status="completed",
            trip_request=result.get("trip_request"),
            travel_plan=result.get("travel_plan"),
            validation_report=result.get("validation_report"),
            error=None,
        )

    return TravelPlanResponse(
        thread_id=thread_id,
        status="failed",
        trip_request=result.get("trip_request"),
        travel_plan=result.get("travel_plan"),
        validation_report=result.get("validation_report"),
        error=(result.get("error") or "调整后的旅行计划未通过校验。"),
    )


@router.delete(
    "/plans/{thread_id}",
    response_model=DeleteTravelPlanResponse,
)
async def delete_travel_plan(
    thread_id: str,
    http_request: Request,
) -> DeleteTravelPlanResponse:
    """删除指定会话的全部旅行规划记录。"""

    travel_graph = http_request.app.state.travel_graph
    checkpointer = http_request.app.state.travel_checkpointer

    try:
        snapshot = await travel_graph.aget_state(
            {
                "configurable": {
                    "thread_id": thread_id,
                }
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="读取旅行规划记录失败。",
        ) from exc

    if not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail="没有找到对应的旅行规划记录。",
        )

    try:
        await checkpointer.adelete_thread(thread_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="删除旅行规划记录失败。",
        ) from exc

    return DeleteTravelPlanResponse(
        thread_id=thread_id,
        status="deleted",
    )
