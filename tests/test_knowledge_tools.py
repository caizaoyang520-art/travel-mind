from langchain_core.documents import Document

from travel_mind.tools.knowledge_tools import (
    search_travel_knowledge,
)


def test_search_travel_knowledge_tool(
    monkeypatch,
) -> None:
    received_arguments: dict = {}

    def fake_retrieve(
        city: str,
        query: str,
        limit: int,
    ) -> list[Document]:
        received_arguments.update(
            {
                "city": city,
                "query": query,
                "limit": limit,
            }
        )

        return [
            Document(
                page_content="西湖适合轻松游览。",
                metadata={
                    "city": "杭州",
                    "source": "hangzhou_guide.md",
                    "title": "杭州旅行规划知识",
                    "section": "西湖游览",
                },
            )
        ]

    monkeypatch.setattr(
        "travel_mind.tools.knowledge_tools.retrieve_travel_knowledge",
        fake_retrieve,
    )

    result = search_travel_knowledge.invoke(
        {
            "city": "杭州",
            "query": "西湖轻松游览",
            "limit": 2,
        }
    )

    assert received_arguments == {
        "city": "杭州",
        "query": "西湖轻松游览",
        "limit": 2,
    }
    assert "西湖适合轻松游览。" in result
    assert "来源：hangzhou_guide.md" in result
