from langchain_core.documents import Document

from travel_mind.rag.retriever import (
    format_knowledge_context,
    retrieve_travel_knowledge,
)


class FakeVectorStore:
    def __init__(self) -> None:
        self.received_arguments: dict = {}

    def similarity_search(
        self,
        **kwargs,
    ) -> list[Document]:
        self.received_arguments = kwargs
        return [
            Document(
                page_content="西湖适合轻松游览。",
                metadata={
                    "city": "杭州",
                },
            )
        ]


def test_retrieval_rejects_empty_city_or_query() -> None:
    assert (
        retrieve_travel_knowledge(
            city="",
            query="西湖",
        )
        == []
    )

    assert (
        retrieve_travel_knowledge(
            city="杭州",
            query="   ",
        )
        == []
    )


def test_retrieval_strips_input_and_limits_results(
    monkeypatch,
) -> None:
    vector_store = FakeVectorStore()

    monkeypatch.setattr(
        "travel_mind.rag.retriever.get_vector_store",
        lambda: vector_store,
    )

    documents = retrieve_travel_knowledge(
        city="  杭州  ",
        query="  西湖轻松游览  ",
        limit=100,
    )

    assert len(documents) == 1
    assert vector_store.received_arguments == {
        "query": "西湖轻松游览",
        "k": 10,
        "filter": {
            "city": "杭州",
        },
    }


def test_format_empty_knowledge_context() -> None:
    result = format_knowledge_context([])

    assert result == "没有检索到相关旅行知识。"


def test_format_knowledge_documents() -> None:
    documents = [
        Document(
            page_content="西湖适合安排半天到一天游览。",
            metadata={
                "city": "杭州",
                "source": "hangzhou_guide.md",
                "title": "杭州旅行规划知识",
                "section": "西湖游览",
            },
        )
    ]

    result = format_knowledge_context(documents)

    assert "[知识 1]" in result
    assert "城市：杭州" in result
    assert "来源：hangzhou_guide.md" in result
    assert "标题：杭州旅行规划知识" in result
    assert "章节：西湖游览" in result
    assert "西湖适合安排半天到一天游览。" in result
