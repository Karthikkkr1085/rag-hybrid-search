import json
import os
from typing import Any

from openai import APIError, OpenAI

from src.utils.logging_config import logger


class LLM:
    """OpenAI-compatible provider client; request keys are never persisted or logged."""

    PROVIDERS = {
        "groq": (
            "https://api.groq.com/openai/v1",
            "GROQ_API_KEY",
            "llama-3.3-70b-versatile",
        ),
        "openai": (None, "OPENAI_API_KEY", "gpt-4o-mini"),
        "gemini": (
            "https://generativelanguage.googleapis.com/v1beta/openai/",
            "GOOGLE_API_KEY",
            "gemini-3.5-flash-lite",
        ),
        "ollama": ("http://127.0.0.1:11434/v1", "OLLAMA_API_KEY", "llama3.2"),
    }

    def __init__(self):
        # CHAT_MODEL remains the developer-controlled default for Groq only.
        # A selected provider always receives that provider's model default.
        self.default_groq_model = os.getenv("CHAT_MODEL", self.PROVIDERS["groq"][2])

    def _client(self, provider: str | None) -> tuple[OpenAI, str]:
        """Create an OpenAI-compatible client for the chosen provider.

        API keys are always read from environment variables mapped in PROVIDERS.
        The frontend must not send API keys — they are managed server-side only.
        """
        name = (provider or "groq").lower()
        if name not in self.PROVIDERS:
            raise ValueError("Unsupported AI provider.")
        base_url, env_key, default_model = self.PROVIDERS[name]
        # Always read the key from the environment for security reasons.
        key = os.getenv(env_key)
        if not key and name != "ollama":
            # Provide a clear, actionable error message for missing keys.
            raise ValueError(
                f"{name.title()} API key not found. Please configure {env_key} in the .env file."
            )
        if name == "groq":
            default_model = self.default_groq_model
        client = OpenAI(api_key=key or "", base_url=base_url)
        logger.info(
            "Configured LLM client for provider=%s base_url=%s default_model=%s key_env=%s",
            name,
            base_url,
            default_model,
            env_key,
        )
        return client, default_model

    def test_connection(
        self, provider: str | None, model: str | None = None
    ) -> dict[str, Any]:
        """Validate the exact model/key combination used by chat.

        This method reads the API key from environment variables only. If the
        provider's environment variable is missing, a ValueError with a clear
        message is raised so the frontend can display it.
        """
        client, default_model = self._client(provider)
        selected_model = model or default_model
        payload = {
            "model": selected_model,
            "messages": [{"role": "user", "content": "Reply with OK."}],
            "max_tokens": 1,
            "temperature": 0,
        }
        logger.info(
            "Testing provider connection: provider=%s model=%s",
            (provider or "groq").lower(),
            selected_model,
        )
        logger.info("Provider request payload: %s", json.dumps(payload, indent=2))
        try:
            resp = client.chat.completions.create(**payload)
            logger.info(
                "Provider connection succeeded for provider=%s model=%s",
                (provider or "groq").lower(),
                selected_model,
            )
        except APIError as error:
            response = getattr(error, "http_response", None)
            if response is not None:
                logger.error(
                    "Provider connection failed: status=%s body=%s",
                    response.status_code,
                    response.text,
                )
            logger.exception(
                "Provider connection failed for provider=%s",
                (provider or "groq").lower(),
            )
            raise
        return {"provider": (provider or "groq").lower(), "model": selected_model}

    def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 512,
        model: str | None = None,
        provider: str | None = None,
    ) -> dict[str, Any]:
        # Note: api_key is intentionally not accepted; keys come from environment variables.
        client, default_model = self._client(provider)
        selected_model = model or default_model
        payload = {
            "model": selected_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant. Answer only using the provided context.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        logger.info(
            "Generating response: provider=%s model=%s max_tokens=%s",
            (provider or "groq").lower(),
            selected_model,
            max_tokens,
        )
        logger.info(
            "Provider streaming request payload: %s", json.dumps(payload, indent=2)
        )

        print("=" * 60)
        print("TEST CONNECTION")
        print("Provider :", provider)
        print("Selected Model :", selected_model)
        print("Payload Model :", payload["model"])
        print("=" * 60)

        try:
            response = client.chat.completions.create(**payload)
            usage = getattr(response, "usage", None)

            usage_data = {
                "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                "completion_tokens": getattr(usage, "completion_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            }
        except APIError as error:
            response = getattr(error, "http_response", None)
            if response is not None:
                logger.error(
                    "LLM generation failed: status=%s body=%s",
                    response.status_code,
                    response.text,
                )
            logger.exception(
                "LLM generation failed for provider=%s model=%s",
                (provider or "groq").lower(),
                selected_model,
            )
            raise
        # Log a summary of the successful response for diagnostics
        try:
            choice_count = len(getattr(response, "choices", []))
        except Exception:
            choice_count = 0
        logger.info(
            "LLM generation succeeded: provider=%s model=%s choices=%s",
            (provider or "groq").lower(),
            selected_model,
            choice_count,
        )
        content = getattr(response.choices[0].message, "content", None) or ""
        logger.info("LLM generation response content length=%s", len(content))
        logger.info("Token Usage: %s", usage_data)

        return {
            "content": content.strip(),
            "usage": usage_data,
            "provider": (provider or "groq").lower(),
            "model": selected_model,
        }

    def stream(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 512,
        model: str | None = None,
        provider: str | None = None,
    ):
        # Note: api_key intentionally omitted. Keys are read from env vars.
        client, default_model = self._client(provider)
        selected_model = model or default_model
        payload = {
            "model": selected_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant. Answer only using the provided context.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        logger.info(
            "Streaming response: provider=%s model=%s max_tokens=%s",
            (provider or "groq").lower(),
            selected_model,
            max_tokens,
        )
        logger.info(
            "Provider streaming request payload: %s", json.dumps(payload, indent=2)
        )
        try:
            response = client.chat.completions.create(**payload)
            logger.info(
                "LLM streaming request opened: provider=%s model=%s",
                (provider or "groq").lower(),
                selected_model,
            )
        except APIError as error:
            response = getattr(error, "http_response", None)
            if response is not None:
                logger.error(
                    "LLM streaming request failed: status=%s body=%s",
                    response.status_code,
                    response.text,
                )
            logger.exception(
                "LLM streaming request failed for provider=%s model=%s",
                (provider or "groq").lower(),
                selected_model,
            )
            raise
        # Stream may yield chunks that don't contain delta.content. Be robust.
        for chunk in response:
            try:
                delta = getattr(chunk.choices[0].delta, "content", None)
            except Exception:
                delta = None
            if delta:
                yield delta
