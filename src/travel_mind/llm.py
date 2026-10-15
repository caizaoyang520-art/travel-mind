from functools import lru_cache

from langchain_openai import ChatOpenAI

from travel_mind.config import get_settings


@lru_cache
def get_chat_model() -> ChatOpenAI:
    settings = get_settings()

    return ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key.get_secret_value(),
        base_url=settings.deepseek_base_url,
        temperature=0,
        timeout=60,
        max_retries=2,
        extra_body={
            "thinking": {
                "type": "disabled",
            }
        },
    )
