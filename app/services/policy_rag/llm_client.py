"""Local LLM client provider with timeout, error handling, and test fakes."""

from abc import ABC, abstractmethod
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class LLMClientError(Exception):
    """Base exception for LLM provider errors."""

    pass


class LLMUnavailableError(LLMClientError):
    """Raised when the local LLM daemon is unreachable or timed out."""

    pass


class LLMResponseError(LLMClientError):
    """Raised when the LLM returns a malformed response or non-success code."""

    pass


class BaseLLMClient(ABC):
    """Abstract interface for local language model inference."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier."""
        pass

    @abstractmethod
    def generate_answer(self, prompt: str) -> str:
        """Generate a text completion for the provided prompt."""
        pass


class LocalLLMClient(BaseLLMClient):
    """Client for local LLM engines (Ollama or OpenAI-compatible local servers)."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "llama3",
        timeout_seconds: float = 5.0,
        max_tokens: int = 512,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds
        self._max_tokens = max_tokens

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate_answer(self, prompt: str) -> str:
        """Send prompt to local Ollama daemon and extract generated text.

        Raises:
            LLMUnavailableError: If daemon is not running, connection is refused, or request times out.
            LLMResponseError: If daemon returns HTTP error status or malformed response.
        """
        url = f"{self._base_url}/api/generate"
        payload = {
            "model": self._model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": self._max_tokens,
            },
        }

        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(url, json=payload)
                if response.status_code != 200:
                    raise LLMResponseError(
                        f"Local LLM daemon returned HTTP status {response.status_code}: {response.text}"
                    )
                data = response.json()
                raw_answer = data.get("response", "")
                if not raw_answer:
                    raise LLMResponseError("Local LLM response contained empty answer text.")
                return raw_answer.strip()
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as err:
            raise LLMUnavailableError(
                f"Local LLM daemon at '{self._base_url}' is unreachable: {err}"
            ) from err
        except Exception as err:
            if isinstance(err, (LLMUnavailableError, LLMResponseError)):
                raise
            raise LLMResponseError(f"Unexpected error communicating with local LLM: {err}") from err


class FakeLLMClient(BaseLLMClient):
    """Deterministic, mock LLM client for testing without local model daemons."""

    def __init__(self, response_text: Optional[str] = None, model_name: str = "fake-llm") -> None:
        self._response_text = response_text
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate_answer(self, prompt: str) -> str:
        if self._response_text is not None:
            return self._response_text
        return "Deterministic grounded answer based on retrieved policy context."

