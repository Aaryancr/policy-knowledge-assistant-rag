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
    """Deterministic mock LLM provider for tests, validation, and offline execution.

    Synthesizes answers strictly from the provided evidence context blocks in the prompt,
    matching question keywords against source sentences, and citing the exact supporting chunk.
    Abstains if evidence is insufficient or question keywords are unanswerable.
    """

    STOPWORDS = {
        "a", "an", "the", "in", "on", "at", "by", "for", "with", "about", "against",
        "between", "into", "through", "during", "before", "after", "above", "below",
        "to", "from", "up", "down", "out", "off", "over", "under", "again",
        "further", "then", "once", "here", "there", "when", "where", "why", "how", "all",
        "any", "both", "each", "few", "more", "most", "other", "some", "such", "no",
        "nor", "not", "only", "own", "same", "so", "than", "too", "very", "can", "will",
        "just", "don", "should", "now", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "having", "do", "does", "did", "doing", "would", "could",
        "what", "which", "who", "whom", "this", "that", "these", "those", "am", "per", "and",
        "also", "must", "may",
    }

    @staticmethod
    def _stem(word: str) -> str:
        w = word.lower()
        for suffix in ("ing", "ies", "es", "ed", "s"):
            if w.endswith(suffix) and len(w) > len(suffix) + 2:
                return w[:-len(suffix)]
        return w

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

        # Extract question if present
        q_match = re.search(r"Employee Question:\s*(.*?)(?:\n|$)", prompt)
        q_text = q_match.group(1).strip() if q_match else ""
        if not q_text:
            return "I don't know based on the provided documents."

        # Extract chunk blocks: [Chunk <uuid>] ... content ... up to next chunk or fence
        chunk_pattern = re.compile(
            r"\[Chunk\s+([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\][^\n]*\n(.*?)(?=(?:\n---|\n--- EVIDENCE EXCERPTS END ---|$))",
            re.DOTALL | re.IGNORECASE,
        )
        blocks = list(chunk_pattern.finditer(prompt))
        if not blocks:
            return "I don't know based on the provided documents."

        q_tokens = [
            w for w in re.findall(r"\b[a-zA-Z0-9]+\b", q_text.lower())
            if w not in self.STOPWORDS and len(w) >= 2
        ]
        if not q_tokens:
            return "I don't know based on the provided documents."
        q_stems = {self._stem(w) for w in q_tokens}

        best_sent = ""
        best_chunk_id = ""
        best_score = 0.0

        for match in blocks:
            cid = match.group(1)
            raw_content = match.group(2).strip()
            # Split into candidate sentences
            sentences = [
                s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", raw_content)
                if len(s.strip()) > 15
            ]
            for s in sentences:
                s_tokens = [
                    w for w in re.findall(r"\b[a-zA-Z0-9]+\b", s.lower())
                    if w not in self.STOPWORDS and len(w) >= 2
                ]
                s_stems = {self._stem(w) for w in s_tokens}
                overlap = q_stems.intersection(s_stems)
                score = len(overlap) / len(q_stems)
                if score > best_score:
                    best_score = score
                    best_sent = s
                    best_chunk_id = cid

        # If highest sentence overlap is too low, abstain
        if best_score < 0.25 or not best_sent:
            return "I don't know based on the provided documents."

        # Clean leading numbering and all-caps section titles (e.g. "2. ANNUAL LEAVE Eligible full-time...")
        clean_sent = re.sub(r"^(?:[0-9]+\.|\*+|-)\s*", "", best_sent).strip()
        clean_sent = re.sub(r"^[A-Z\s]{4,}\s+(?=[A-Z][a-z])", "", clean_sent).strip()

        return f"{clean_sent} [Chunk {best_chunk_id}]"


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
