"""Maps a project's RagConfig to a LangChain chat model instance.

This is the "bring any LLM API key" abstraction: adding a provider means
adding one branch here, not touching the ingestion or retrieval code.
"""
from langchain_core.language_models import BaseChatModel

from app.core.crypto import decrypt_secret
from app.models.rag_config import RagConfig


def get_chat_model(config: RagConfig) -> BaseChatModel:
    api_key = decrypt_secret(config.api_key_encrypted) if config.api_key_encrypted else None
    params = {"max_new_tokens": config.max_new_tokens, "temperature": config.temperature}

    if config.provider == "ibm_watsonx":
        from langchain_ibm import ChatWatsonx

        region = config.region or "us-south"
        return ChatWatsonx(
            model_id=config.model_id,
            url=config.base_url or f"https://{region}.ml.cloud.ibm.com",
            apikey=api_key,
            project_id=config.project_id_external,
            params=params,
        )

    if config.provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config.model_id,
            api_key=api_key,
            base_url=config.base_url,
            temperature=config.temperature,
            max_tokens=config.max_new_tokens,
        )

    if config.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=config.model_id,
            api_key=api_key,
            temperature=config.temperature,
            max_tokens=config.max_new_tokens,
        )

    if config.provider == "openai_compatible":
        # Any OpenAI-API-compatible endpoint: Groq, Together, self-hosted vLLM/Ollama, etc.
        from langchain_openai import ChatOpenAI

        if not config.base_url:
            raise ValueError("base_url is required for the openai_compatible provider")
        return ChatOpenAI(
            model=config.model_id,
            api_key=api_key or "not-needed",
            base_url=config.base_url,
            temperature=config.temperature,
            max_tokens=config.max_new_tokens,
        )

    raise ValueError(f"Unsupported LLM provider: {config.provider}")
