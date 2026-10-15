from functools import lru_cache

from langchain_openai import OpenAIEmbeddings

from travel_mind.config import get_settings


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    """获取用于 RAG 检索的云端 Embedding 客户端。"""

    settings = get_settings()

    return OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=(settings.embedding_api_key.get_secret_value()),
        openai_api_base=settings.embedding_base_url,
        check_embedding_ctx_length=False,
        chunk_size=32,
        timeout=60,
        max_retries=2,
    )
