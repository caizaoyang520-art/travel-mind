from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from travel_mind.agents.planner import generate_travel_plan
from travel_mind.agents.supervisor import (
    build_clarification_question,
    extract_trip_request,
    finalize_trip_request,
)
from travel_mind.graph.state import TravelState
from travel_mind.llm import get_chat_model
from travel_mind.tools.research_tools import RESEARCH_TOOLS
from travel_mind.validators.itinerary import validate_travel_plan

MAX_REVISIONS = 2
"""校验失败后最多重新生成几次"""
MAX_RESEARCH_ROUNDS = 4
"""研究阶段最多调用几轮工具"""


def supervisor_node(state: TravelState) -> TravelState:
    """提取用户需求，并决定追问用户还是进入行程规划。"""

    messages = state.get("messages", [])

    user_messages = [
        message.content
        for message in messages
        if isinstance(message, HumanMessage) and isinstance(message.content, str)
    ]

    if not user_messages:
        question = "请先告诉我你的旅行计划。"

        return {
            "clarification_question": question,
            "next_step": "ask_user",
            "messages": [AIMessage(content=question)],
            "error": "没有找到用户消息",
        }

    conversation_text = "\n".join(user_messages)
    draft = extract_trip_request(conversation_text)
    question = build_clarification_question(draft)

    if question is not None:
        return {
            "trip_draft": draft,
            "trip_request": None,
            "clarification_question": question,
            "next_step": "ask_user",
            "messages": [AIMessage(content=question)],
            "error": None,
        }

    trip_request = finalize_trip_request(draft)

    return {
        "travel_plan": None,
        "validation_report": None,
        "revision_count": 0,
        "research_rounds": 0,
        "trip_draft": draft,
        "trip_request": trip_request,
        "clarification_question": None,
        "next_step": "plan",
        "error": None,
    }


def planner_research_node(state: TravelState) -> TravelState:
    """调用高德工具，收集天气、景点和路线资料。"""

    trip_request = state.get("trip_request")

    is_replan = state.get("operation") == "replan"

    execution_event = state.get("execution_event") if is_replan else None

    current_plan = state.get("travel_plan") if is_replan else None

    if trip_request is None:
        error_message = "无法查询旅行资料：旅行需求尚未完整。"

        return {
            "messages": [AIMessage(content=error_message)],
            "error": error_message,
        }

    research_rounds = state.get("research_rounds", 0)

    if research_rounds >= MAX_RESEARCH_ROUNDS:
        return {
            "messages": [AIMessage(content="资料查询达到最大轮数，开始生成行程。")],
            "error": None,
        }

    messages = state.get("messages", [])

    latest_human_index = max(
        (
            index
            for index, message in enumerate(messages)
            if isinstance(message, HumanMessage)
        ),
        default=-1,
    )

    current_run_messages = messages[latest_human_index + 1 :]

    tool_history = [
        message
        for message in current_run_messages
        if isinstance(message, ToolMessage)
        or (isinstance(message, AIMessage) and bool(message.tool_calls))
    ]

    if execution_event is not None:
        event_context = (
            f"旅行途中发生了以下事件：\n{execution_event.model_dump_json(indent=2)}"
        )
    else:
        event_context = "当前没有旅行途中事件。"

    if current_plan is not None:
        current_plan_context = (
            f"当前行程如下：\n{current_plan.model_dump_json(indent=2)}"
        )
    else:
        current_plan_context = "当前没有需要调整的旧行程。"

    research_model = get_chat_model().bind_tools(RESEARCH_TOOLS)

    response = research_model.invoke(
        [
            SystemMessage(
                content=(
                    "你是 TravelMind 的旅行资料查询 Agent。"
                    "首先使用 search_travel_knowledge 查询目的地、"
                    "旅行偏好和特殊要求相关的知识库资料。"
                    "然后使用高德工具查询目的地天气、相关景点"
                    "和必要的步行路线。"
                    "如果发生旅行途中事件，应重点查询不受该事件影响的"
                    "替代景点、最新天气和必要路线。"
                    "不要重复调用参数完全相同的工具。"
                    "获得足够资料后，直接回复“资料收集完成”，"
                    "并且不要继续调用工具。"
                )
            ),
            HumanMessage(
                content=(
                    "旅行需求如下：\n"
                    f"{trip_request.model_dump_json(indent=2)}\n\n"
                    f"{event_context}\n\n"
                    f"{current_plan_context}"
                )
            ),
            *tool_history,
        ]
    )

    return {
        "messages": [response],
        "research_rounds": research_rounds + 1,
        "error": None,
    }


def planner_node(state: TravelState) -> TravelState:
    """生成行程，或者根据 Evaluator 的反馈重新生成。"""

    trip_request = state.get("trip_request")

    if trip_request is None:
        error_message = "无法生成行程：旅行需求尚未完整。"

        return {
            "messages": [AIMessage(content=error_message)],
            "travel_plan": None,
            "error": error_message,
        }
    is_replan = state.get("operation") == "replan"

    current_plan = (
        (state.get("previous_travel_plan") or state.get("travel_plan"))
        if is_replan
        else None
    )

    execution_event = state.get("execution_event") if is_replan else None
    report = state.get("validation_report")
    revision_feedback: list[str] | None = None

    if report is not None and not report.passed:
        revision_feedback = [issue.message for issue in report.issues]

    messages = state.get("messages", [])

    latest_human_index = max(
        (
            index
            for index, message in enumerate(messages)
            if isinstance(message, HumanMessage)
        ),
        default=-1,
    )

    current_run_messages = messages[latest_human_index + 1 :]

    tool_context = [
        (f"工具名称：{message.name}\n返回结果：{message.content}")
        for message in current_run_messages
        if isinstance(message, ToolMessage)
    ]

    travel_plan = generate_travel_plan(
        trip_request=trip_request,
        revision_feedback=revision_feedback,
        tool_context=tool_context,
        current_plan=current_plan,
        execution_event=execution_event,
    )

    return {
        "travel_plan": travel_plan,
        "validation_report": None,
        "messages": [AIMessage(content=travel_plan.summary)],
        "error": None,
    }


def evaluator_node(state: TravelState) -> TravelState:
    """校验行程，并决定通过、修改或结束。"""

    trip_request = state.get("trip_request")
    travel_plan = state.get("travel_plan")

    if trip_request is None or travel_plan is None:
        error_message = "无法评估行程：缺少旅行需求或旅行计划。"

        return {
            "validation_report": None,
            "next_step": "failed",
            "messages": [AIMessage(content=error_message)],
            "error": error_message,
        }

    is_replan = state.get("operation") == "replan"

    report = validate_travel_plan(
        trip_request=trip_request,
        travel_plan=travel_plan,
        previous_travel_plan=(state.get("previous_travel_plan") if is_replan else None),
        execution_event=(state.get("execution_event") if is_replan else None),
    )

    revision_count = state.get("revision_count", 0)

    if report.passed:
        return {
            "validation_report": report,
            "next_step": "approved",
            "messages": [AIMessage(content="行程已通过日期、预算和时间冲突检查。")],
            "error": None,
        }

    issue_messages = [issue.message for issue in report.issues]

    if revision_count < MAX_REVISIONS:
        next_revision = revision_count + 1

        return {
            "validation_report": report,
            "revision_count": next_revision,
            "next_step": "revise",
            "messages": [
                AIMessage(
                    content=(
                        f"第 {next_revision} 次行程校验未通过，"
                        "正在根据以下问题重新规划：" + "；".join(issue_messages)
                    )
                )
            ],
            "error": None,
        }

    return {
        "validation_report": report,
        "next_step": "failed",
        "messages": [
            AIMessage(
                content=(
                    "行程在达到最大修改次数后仍未通过检查：" + "；".join(issue_messages)
                )
            )
        ],
        "error": None,
    }
