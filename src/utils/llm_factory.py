"""LLM factory — returns a LangChain Runnable (str → str) for the configured provider.

Supported providers (set llm.provider in agent_config.yaml or AGENT_LLM_PROVIDER env var):
  ollama        Local Ollama — default; no credentials required
  anthropic     Anthropic API — set AGENT_ANTHROPIC_API_KEY
  vertex_ai     GCP Vertex AI — set GOOGLE_CLOUD_PROJECT + GOOGLE_APPLICATION_CREDENTIALS
  bedrock       AWS Bedrock   — set AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY + AWS_REGION
  azure_openai  Azure OpenAI  — set AGENT_AZURE_OPENAI_KEY + AGENT_AZURE_OPENAI_ENDPOINT +
                                    AGENT_AZURE_OPENAI_DEPLOYMENT

All providers return a Runnable that accepts a plain string prompt and returns a plain
string response. Caller code never needs to know which provider is active.
"""

import os
import logging
from typing import TYPE_CHECKING

from langchain_core.output_parsers import StrOutputParser

if TYPE_CHECKING:
    from langchain_core.runnables import Runnable
    from utils.config_loader import AppConfig

logger = logging.getLogger(__name__)


def build_llm(config: "AppConfig") -> "Runnable":
    """Return a Runnable[str, str] for the configured LLM provider.

    Usage:
        llm = build_llm(config)
        response: str = llm.invoke("your prompt here")
    """
    provider = os.getenv("AGENT_LLM_PROVIDER", config.llm.provider).lower()
    logger.info("Building LLM for provider: %s", provider)

    if provider == "ollama":
        return _build_ollama(config)
    elif provider == "anthropic":
        return _build_anthropic(config)
    elif provider == "vertex_ai":
        return _build_vertexai(config)
    elif provider == "bedrock":
        return _build_bedrock(config)
    elif provider == "azure_openai":
        return _build_azure_openai(config)
    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. "
            f"Valid options: ollama | anthropic | vertex_ai | bedrock | azure_openai"
        )


# ── provider builders ──────────────────────────────────────────────────────────

class _OllamaNoThinkRunnable:
    """Calls the Ollama /api/chat endpoint directly with think=false.

    langchain_ollama v1.0.1 does not forward a `think` parameter, so we bypass
    it for the health-check enrichment path where latency matters.
    """

    def __init__(self, base_url: str, model: str, temperature: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._model    = model
        self._temperature = temperature

    def invoke(self, prompt: str) -> str:
        import requests
        resp = requests.post(
            f"{self._base_url}/api/chat",
            json={
                "model":    self._model,
                "messages": [{"role": "user", "content": prompt}],
                "stream":   False,
                "think":    False,
                "options":  {"temperature": self._temperature},
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


def _build_ollama(config: "AppConfig") -> "Runnable":
    cfg      = config.llm.ollama
    base_url = os.getenv("AGENT_OLLAMA_URL",   cfg.base_url)
    model    = os.getenv("AGENT_OLLAMA_MODEL",  cfg.model)
    logger.info("Ollama: %s  model=%s", base_url, model)
    return _OllamaNoThinkRunnable(base_url, model, cfg.temperature)


def _build_anthropic(config: "AppConfig") -> "Runnable":
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise ImportError(
            "langchain-anthropic is required. Run: pip install langchain-anthropic"
        )

    api_key = os.getenv("AGENT_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "Anthropic API key not found. Set AGENT_ANTHROPIC_API_KEY environment variable."
        )

    cfg = config.llm.anthropic
    llm = ChatAnthropic(
        model=cfg.model,
        temperature=cfg.temperature,
        api_key=api_key,
    )
    logger.info("Anthropic: model=%s", cfg.model)
    return llm | StrOutputParser()


def _build_azure_openai(config: "AppConfig") -> "Runnable":
    try:
        from langchain_openai import AzureChatOpenAI
    except ImportError:
        raise ImportError(
            "langchain-openai is required. Run: pip install langchain-openai"
        )

    api_key = os.getenv("AGENT_AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "Azure OpenAI API key not found. Set AGENT_AZURE_OPENAI_KEY environment variable."
        )

    cfg = config.llm.azure_openai
    endpoint   = os.getenv("AGENT_AZURE_OPENAI_ENDPOINT",   cfg.endpoint)
    deployment = os.getenv("AGENT_AZURE_OPENAI_DEPLOYMENT", cfg.deployment)

    if not endpoint or not deployment:
        raise ValueError(
            "Azure OpenAI requires AGENT_AZURE_OPENAI_ENDPOINT and "
            "AGENT_AZURE_OPENAI_DEPLOYMENT environment variables."
        )

    llm = AzureChatOpenAI(
        azure_endpoint=endpoint,
        azure_deployment=deployment,
        api_version=cfg.api_version,
        temperature=cfg.temperature,
        api_key=api_key,
    )
    logger.info("Azure OpenAI: endpoint=%s  deployment=%s", endpoint, deployment)
    return llm | StrOutputParser()


def _build_vertexai(config: "AppConfig") -> "Runnable":
    try:
        from langchain_google_vertexai import ChatVertexAI
    except ImportError:
        raise ImportError(
            "langchain-google-vertexai is required. Run: pip install langchain-google-vertexai"
        )

    cfg = config.llm.vertex_ai
    project  = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("VERTEXAI_PROJECT") or cfg.project
    location = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("VERTEXAI_LOCATION") or cfg.location

    if not project:
        raise ValueError(
            "Vertex AI requires GOOGLE_CLOUD_PROJECT environment variable."
        )

    llm = ChatVertexAI(
        model=cfg.model,
        project=project,
        location=location,
        temperature=cfg.temperature,
    )
    logger.info("Vertex AI: project=%s  location=%s  model=%s", project, location, cfg.model)
    return llm | StrOutputParser()


def _build_bedrock(config: "AppConfig") -> "Runnable":
    try:
        from langchain_aws import ChatBedrock
    except ImportError:
        raise ImportError(
            "langchain-aws is required. Run: pip install langchain-aws"
        )

    cfg = config.llm.bedrock
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or cfg.region

    llm = ChatBedrock(
        model_id=cfg.model_id,
        region_name=region,
        model_kwargs={"temperature": cfg.temperature},
    )
    logger.info("Bedrock: model_id=%s  region=%s", cfg.model_id, region)
    return llm | StrOutputParser()
