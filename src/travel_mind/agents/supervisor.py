from datetime import date
from typing import cast

from langchain_core.messages import HumanMessage, SystemMessage

from travel_mind.domain.trip_request import TripRequest, TripRequestDraft
from travel_mind.llm import get_chat_model

SYSTEM_PROMPT = """
你是 TravelMind 的旅行需求分析 Agent。
你的任务是从用户消息中提取旅行需求。

当前日期：{current_date}

提取规则：
1. start_city 表示出发城市。
2. end_city 表示目的地城市。
3. 不要编造用户没有提供的信息，缺失字段保持为 null。
4. 如果用户提供开始日期和旅行天数，可以计算结束日期。
5. budget 表示整个行程的人民币总预算。
6. “不想太赶”“轻松一点”对应 relaxed。
7. “正常安排”“适中”对应 balanced。
8. “多玩一些”“行程紧凑”对应 intensive。
9. preferences 保存美食、自然风景、历史文化等旅行偏好。
10. special_requirements 保存老人同行、儿童同行、避免爬山等特殊要求。
"""


def extract_trip_request(user_message: str) -> TripRequestDraft:
    structured_model = get_chat_model().with_structured_output(
        TripRequestDraft,
        method="function_calling",
    )

    result = structured_model.invoke(
        [
            SystemMessage(
                content=SYSTEM_PROMPT.format(
                    current_date=date.today().isoformat(),
                )
            ),
            HumanMessage(content=user_message),
        ]
    )

    return cast(TripRequestDraft, result)


FIELD_QUESTIONS = {
    "start_city": "你从哪个城市出发",
    "end_city": "你想去哪个城市",
    "start_date": "你计划哪天出发",
    "end_date": "你计划哪天结束行程",
    "travelers": "这次旅行一共有几个人",
    "budget": "整个行程的总预算大约是多少元",
}


def build_clarification_question(draft: TripRequestDraft) -> str | None:
    """根据缺失字段生成需要向用户提出的问题。"""

    if not draft.missing_fields:
        return None

    questions = [FIELD_QUESTIONS[field_name] for field_name in draft.missing_fields]

    return "为了帮你制定行程，还需要确认：" + "；".join(questions) + "。"


def finalize_trip_request(draft: TripRequestDraft) -> TripRequest:
    """将完整的需求草稿转换为正式旅行需求。"""

    if draft.missing_fields:
        missing = ", ".join(draft.missing_fields)
        raise ValueError(f"旅行需求不完整，缺少字段：{missing}")

    return TripRequest.model_validate(draft.model_dump())
