from typing import cast

from langchain_core.messages import HumanMessage, SystemMessage

from travel_mind.domain.execution import TravelExecutionEvent
from travel_mind.domain.itinerary import TravelPlan
from travel_mind.domain.trip_request import TripRequest
from travel_mind.llm import get_chat_model

SYSTEM_PROMPT = """
你是 TravelMind 的旅行规划 Agent。
请根据用户的旅行需求生成详细、可执行的旅行计划。

规划规则：
1. 行程日期必须覆盖用户要求的全部日期。
2. 每天的活动时间不能互相冲突。
3. 安排景点之间的交通时间，避免行程过度紧凑。
4. 预计总花费不能超过用户预算。
5. relaxed 表示每天安排较少活动，并保留休息时间。
6. balanced 表示活动数量适中。
7. intensive 表示安排更多活动，但仍需保证可执行。
8. 有老人或儿童同行时，减少长时间步行和高强度活动。
9. 优先使用“工具查询结果”中的天气、景点和路线资料。
10. 使用某项工具数据时，在活动的 source_refs 中记录工具名称。
11. POI 数据来源填写 amap:search_city_pois。
12. 天气数据来源填写 amap:get_city_weather。
13. 步行路线数据来源填写 amap:get_walking_route。
14. 工具没有返回的信息不得描述成实时查询结果。
15. 票价和营业时间如果没有可靠数据，需要提醒用户出发前核实。
16. 使用知识库资料时，在活动的 source_refs 中填写 rag:search_travel_knowledge。
"""


def generate_travel_plan(
    trip_request: TripRequest,
    revision_feedback: list[str] | None = None,
    tool_context: list[str] | None = None,
    current_plan: TravelPlan | None = None,
    execution_event: TravelExecutionEvent | None = None,
) -> TravelPlan:
    """生成行程，并根据校验反馈修改上一版问题。"""

    structured_model = get_chat_model().with_structured_output(
        TravelPlan,
        method="function_calling",
    )

    if revision_feedback:
        feedback_text = "\n".join(f"- {message}" for message in revision_feedback)
    else:
        feedback_text = "无，这是第一次生成行程。"
    if tool_context:
        tool_context_text = "\n\n".join(tool_context)
    else:
        tool_context_text = "没有可用的工具查询结果。"

    if current_plan is not None and execution_event is not None:
        replan_context = (
            "这是旅行途中的动态重新规划。\n"
            "当前完整行程：\n"
            f"{current_plan.model_dump_json(indent=2)}\n\n"
            "发生的事件：\n"
            f"{execution_event.model_dump_json(indent=2)}\n\n"
            "重新规划规则：\n"
            "1. 必须返回包含全部日期的完整行程。\n"
            "2. affected_date 之前的每日行程必须原样保留。\n"
            "3. 如果填写了 occurred_time，事件当天在该时间之前"
            "已经结束的活动必须原样保留。\n"
            "4. 只调整事件影响范围内及其之后的活动。\n"
            "5. 新行程仍需满足预算、节奏和用户偏好。\n"
            "6. notices 中说明事件及本次调整内容。"
        )
    else:
        replan_context = "这是首次规划，不存在需要保留的旧行程。"

    result = structured_model.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    "请根据下面的旅行需求生成行程：\n"
                    f"{trip_request.model_dump_json(indent=2)}\n\n"
                    "工具查询结果：\n"
                    f"{tool_context_text}\n\n"
                    "动态重新规划上下文：\n"
                    f"{replan_context}\n\n"
                    "上一版行程的校验反馈：\n"
                    f"{feedback_text}\n\n"
                    "如果存在校验问题，请在新行程中修正。"
                )
            ),
        ]
    )

    return cast(TravelPlan, result)
