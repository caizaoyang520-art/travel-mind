from langchain_core.tools import tool

from travel_mind.rag.retriever import (
    format_knowledge_context,
    retrieve_travel_knowledge,
)


@tool
def search_travel_knowledge(
    city: str,
    query: str,
    limit: int = 4,
) -> str:
    """
    从指定城市的 TravelMind 旅行知识库中检索资料。

    city 是目的地城市，例如“杭州”。
    query 应包含旅行偏好和特殊要求，
    例如“老人轻松旅行注意事项”。
    """

    documents = retrieve_travel_knowledge(
        city=city,
        query=query,
        limit=limit,
    )

    return format_knowledge_context(documents)


KNOWLEDGE_TOOLS = [
    search_travel_knowledge,
]
