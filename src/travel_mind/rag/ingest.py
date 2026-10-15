from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from travel_mind.rag.vector_store import get_vector_store

PROJECT_ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"
CITY_BY_FILENAME = {
    "hangzhou_guide.md": "杭州",
}


def load_knowledge_documents() -> list[Document]:
    """加载并切分知识库中的 Markdown 文档。"""

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "title"),
            ("##", "section"),
        ],
        strip_headers=False,
    )

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
        separators=[
            "\n\n",
            "\n",
            "。",
            "；",
            "，",
            "",
        ],
    )

    documents: list[Document] = []

    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        city = CITY_BY_FILENAME.get(path.name)

        if city is None:
            raise ValueError(f"没有配置知识文档所属城市：{path.name}")

        markdown_text = path.read_text(encoding="utf-8")

        header_documents = header_splitter.split_text(markdown_text)

        chunks = text_splitter.split_documents(header_documents)

        for chunk in chunks:
            chunk.metadata.update(
                {
                    "city": city,
                    "source": path.name,
                    "source_path": str(path.relative_to(PROJECT_ROOT)),
                    "document_type": "travel_guide",
                }
            )

        documents.extend(chunks)

    return documents


def ingest_knowledge() -> None:
    """将知识文档转换成向量并保存到 pgvector。"""

    documents = load_knowledge_documents()

    if not documents:
        raise RuntimeError(f"知识库目录中没有 Markdown 文档：{KNOWLEDGE_DIR}")

    ids = [
        str(
            uuid5(
                NAMESPACE_URL,
                (f"{document.metadata['source']}:{index}"),
            )
        )
        for index, document in enumerate(documents)
    ]

    vector_store = get_vector_store()

    vector_store.add_documents(
        documents=documents,
        ids=ids,
    )

    print(f"成功写入 {len(documents)} 个知识片段。")


if __name__ == "__main__":
    ingest_knowledge()
