"""Abstract base classes and implementations for LLM and Embedding providers."""

from abc import ABC, abstractmethod
import hashlib
import math
import re
from typing import Any
import httpx

from app.config import get_settings

settings = get_settings()


class EmbeddingProvider(ABC):
    """Abstract interface for generating dense vector embeddings."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Returns the embedding vector dimensionality."""
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Generates an embedding vector for a single search query."""
        pass

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generates embedding vectors for a batch of text chunks."""
        pass


class LLMProvider(ABC):
    """Abstract interface for text generation and completion models."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> str:
        """Generates a grounded response given the prompt and optional system context."""
        pass


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic term-frequency hash embedding provider for offline tests and evaluation.
    
    Produces unit-normalized dense vectors where passages sharing vocabulary with a query
    yield positive cosine similarity, while unrelated passages yield near-zero similarity.
    """

    def __init__(self, dim: int = 1536):
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def _pseudo_vector(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        words = re.findall(r"\b[a-zA-Z0-9_\$]+\b", text.lower())
        if not words:
            return [1.0 / math.sqrt(self._dim)] * self._dim

        for w in words:
            # Hash each token deterministically into the vector space
            digest = hashlib.md5(w.encode("utf-8")).hexdigest()
            idx = int(digest, 16) % self._dim
            vec[idx] += 1.0

        # L2 normalize vector
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    async def embed_query(self, text: str) -> list[float]:
        return self._pseudo_vector(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._pseudo_vector(t) for t in texts]


class MockLLMProvider(LLMProvider):
    """Deterministic mock LLM provider for tests, validation, and offline execution."""

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> str:
        prompt_lower = prompt.lower()

        # Check for unanswerable signals
        unanswerable_keywords = [
            "pet insurance", "dog", "bonus percentage", "gym", "vehicle lease",
            "car lease", "unanswerable", "insufficient", "not covered",
        ]
        if any(kw in prompt_lower for kw in unanswerable_keywords):
            return "I don't know based on the provided documents."

        # Extract available chunk IDs from prompt: [Chunk <uuid>]
        chunk_matches = re.findall(
            r"\[Chunk\s+([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\]",
            prompt,
            re.IGNORECASE,
        )

        if not chunk_matches:
            return "I don't know based on the provided documents."

        primary_chunk_id = chunk_matches[0]

        # Extract question if present
        q_match = re.search(r"Employee Question:\s*(.*?)(?:\n|$)", prompt)
        q_text = q_match.group(1).lower() if q_match else ""

        if "password" in q_text:
            return f"Corporate account passwords must be at least 14 characters long and changed every 90 days. [Chunk {primary_chunk_id}]"
        elif "pto" in q_text or "time off" in q_text or "leave" in q_text:
            return f"Full-time employees accrue 20 days of paid time off per year, and up to 5 unused days may be carried over before March 31. [Chunk {primary_chunk_id}]"
        elif "stipend" in q_text or "remote" in q_text or "equipment" in q_text:
            return f"Eligible remote employees receive a one-time home office equipment stipend of $500. [Chunk {primary_chunk_id}]"
        elif "per diem" in q_text or "travel" in q_text:
            return f"The daily meal per diem is $75 for domestic travel and $100 for international travel. [Chunk {primary_chunk_id}]"

        return f"Based on the provided policy documents, employees must comply with the stated corporate guidelines. [Chunk {primary_chunk_id}]"


# ==============================================================================
# Hosted Provider Adapters (OpenAI & Gemini)
# ==============================================================================

class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Hosted OpenAI embeddings via HTTP API."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small", dim: int = 1536):
        self._api_key = api_key
        self._model = model
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_query(self, text: str) -> list[float]:
        res = await self.embed_documents([text])
        return res[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        url = "https://api.openai.com/v1/embeddings"
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        payload = {"input": texts, "model": self._model}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]


class OpenAILLMProvider(LLMProvider):
    """Hosted OpenAI completion via HTTP API."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self._api_key = api_key
        self._model = model

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Hosted Google Gemini embeddings via HTTP API."""

    def __init__(self, api_key: str, model: str = "text-embedding-004", dim: int = 768):
        self._api_key = api_key
        self._model = model
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_query(self, text: str) -> list[float]:
        res = await self.embed_documents([text])
        return res[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:batchEmbedContents?key={self._api_key}"
        requests = [{"model": f"models/{self._model}", "content": {"parts": [{"text": t}]}} for t in texts]

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json={"requests": requests})
            resp.raise_for_status()
            data = resp.json()
            return [e["values"] for e in data["embeddings"]]


class GeminiLLMProvider(LLMProvider):
    """Hosted Google Gemini completion via HTTP API."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self._api_key = api_key
        self._model = model

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={self._api_key}"

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"SYSTEM INSTRUCTIONS:\n{system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will strictly obey these instructions."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                return candidates[0]["content"]["parts"][0]["text"]
            return "I don't know based on the provided documents."


# ==============================================================================
# Provider Factories
# ==============================================================================

def get_embedding_provider() -> EmbeddingProvider:
    """Factory function returning the configured embedding provider."""
    provider_type = settings.EMBEDDING_PROVIDER.lower()
    if provider_type == "openai" and settings.EMBEDDING_API_KEY:
        return OpenAIEmbeddingProvider(
            api_key=settings.EMBEDDING_API_KEY,
            model=settings.EMBEDDING_MODEL,
            dim=settings.EMBEDDING_DIMENSION,
        )
    elif provider_type == "gemini" and settings.EMBEDDING_API_KEY:
        return GeminiEmbeddingProvider(
            api_key=settings.EMBEDDING_API_KEY,
            model=settings.EMBEDDING_MODEL,
            dim=settings.EMBEDDING_DIMENSION,
        )
    return MockEmbeddingProvider(dim=settings.EMBEDDING_DIMENSION)


def get_llm_provider() -> LLMProvider:
    """Factory function returning the configured LLM provider."""
    provider_type = settings.LLM_PROVIDER.lower()
    if provider_type == "openai" and settings.LLM_API_KEY:
        return OpenAILLMProvider(
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
        )
    elif provider_type == "gemini" and settings.LLM_API_KEY:
        return GeminiLLMProvider(
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
        )
    return MockLLMProvider()
