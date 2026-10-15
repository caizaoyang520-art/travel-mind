from langchain_core.documents import Document

from travel_mind.rag.vector_store import get_vector_store


def retrieve_travel_knowledge(
    city: str,
    query: str,
    limit: int = 4,
) -> list[Document]:
    """在指定城市的知识库中检索旅行资料。"""

    city = city.strip()
    query = query.strip()

    if not city or not query:
        return []

    return get_vector_store().similarity_search(
        query=query,
        k=max(1, min(limit, 10)),
        filter={
            "city": city,
        },
    )


def format_knowledge_context(
    documents: list[Document],
) -> str:
    """将检索结果转换成适合传给大模型的文本。"""

    if not documents:
        return "没有检索到相关旅行知识。"

    sections: list[str] = []

    for index, document in enumerate(
        documents,
        start=1,
    ):
        metadata = document.metadata

        city = metadata.get("city", "未知城市")
        source = metadata.get("source", "未知来源")
        title = metadata.get("title", "")
        section = metadata.get("section", "")

        sections.append(
            f"[知识 {index}]\n"
            f"城市：{city}\n"
            f"来源：{source}\n"
            f"标题：{title}\n"
            f"章节：{section}\n"
            f"内容：{document.page_content}"
        )

    return "\n\n".join(sections)
