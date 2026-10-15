from typing import Literal

from langchain_core.messages import AIMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from travel_mind.graph.nodes import (
    evaluator_node,
    planner_node,
    planner_research_node,
    supervisor_node,
)
from travel_mind.graph.state import TravelState
from travel_mind.tools.research_tools import RESEARCH_TOOLS


def route_after_supervisor(
    state: TravelState,
) -> Literal["ask_user", "plan"]:
    """根据 Supervisor 的判断选择下一条路径。"""

    return state["next_step"]


def route_start(
    state: TravelState,
) -> Literal["supervisor", "planner_research"]:
    """根据操作类型选择普通规划或事件重规划。"""

    if state.get("operation") == "replan":
        return "planner_research"

    return "supervisor"


def route_after_research(
    state: TravelState,
) -> Literal["tools", "planner"]:
    """判断模型要调用工具，还是已经完成资料查询。"""

    messages = state.get("messages", [])

    if not messages:
        return "planner"

    last_message = messages[-1]

    if isinstance(last_message, AIMessage) and bool(last_message.tool_calls):
        return "tools"

    return "planner"


def route_after_evaluator(
    state: TravelState,
) -> Literal["approved", "revise", "failed"]:
    route = state["next_step"]

    if route not in {"approved", "revise", "failed"}:
        raise ValueError(f"无效的 Evaluator 路由：{route}")

    return route


workflow = StateGraph(TravelState)

workflow.add_node("supervisor", supervisor_node)
workflow.add_node("planner_research", planner_research_node)
workflow.add_node(
    "tools",
    ToolNode(
        RESEARCH_TOOLS,
        handle_tool_errors=True,
        messages_key="messages",
    ),
)
workflow.add_node("planner", planner_node)
workflow.add_node("evaluator", evaluator_node)


workflow.add_conditional_edges(
    START,
    route_start,
    {
        "supervisor": "supervisor",
        "planner_research": "planner_research",
    },
)
workflow.add_conditional_edges(
    "supervisor",
    route_after_supervisor,
    {
        "ask_user": END,
        "plan": "planner_research",
    },
)
workflow.add_conditional_edges(
    "planner_research",
    route_after_research,
    {
        "tools": "tools",
        "planner": "planner",
    },
)
workflow.add_edge("tools", "planner_research")
workflow.add_edge("planner", "evaluator")
workflow.add_conditional_edges(
    "evaluator",
    route_after_evaluator,
    {
        "approved": END,
        "revise": "planner",
        "failed": END,
    },
)


def build_travel_graph(
    checkpointer: BaseCheckpointSaver,
):
    """使用指定的检查点存储编译旅行规划工作流。"""

    return workflow.compile(
        checkpointer=checkpointer,
    )
