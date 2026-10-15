from functools import lru_cache

from langchain_postgres import PGVector

from travel_mind.config import get_settings
from travel_mind.rag.embeddings import get_embeddings


@lru_cache
def get_vector_store() -> PGVector:
    """获取旅行知识库的 pgvector 向量存储。"""

    settings = get_settings()

    return PGVector(
        embeddings=get_embeddings(),
        connection=(settings.database_url.get_secret_value()),
        collection_name=settings.vector_collection_name,
        embedding_length=settings.embedding_dimensions,
        use_jsonb=True,
        create_extension=False,
        pre_delete_collection=False,
    )
