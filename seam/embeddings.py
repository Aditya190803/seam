from __future__ import annotations

import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from .config import SeamConfig

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*|[0-9]+")
CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
LOCAL_DIMENSIONS = 128


def tokenize(text: str) -> list[str]:
    normalized = text.replace("_", " ").replace("-", " ").replace("/", " ")
    tokens: list[str] = []
    for raw in TOKEN_RE.findall(normalized):
        for part in CAMEL_RE.sub(" ", raw).split():
            lowered = part.lower()
            if len(lowered) > 1:
                tokens.append(lowered)
    return tokens


def normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    return sum(a[i] * b[i] for i in range(length))


class EmbeddingProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def embed_many(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]


class LocalHashEmbeddingProvider(EmbeddingProvider):
    name = "local"

    def __init__(self, model: str = "seam-local-hash-v1", dimensions: int = LOCAL_DIMENSIONS) -> None:
        self.model = model
        self.dimensions = dimensions

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = tokenize(text)
        if not tokens:
            return vector

        features: list[str] = []
        features.extend(tokens)
        features.extend(f"{left}:{right}" for left, right in zip(tokens, tokens[1:]))

        for token in features:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.5 if ":" in token else 1.0
            vector[bucket] += sign * weight
        return normalize(vector)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    name = "openai"

    def __init__(self, model: str, *, api_key_env: str = "OPENAI_API_KEY", base_url: str | None = None) -> None:
        self.model = model
        self.api_key_env = api_key_env
        self.base_url = base_url

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency exists in normal install
            raise RuntimeError("openai package is required for OpenAI embeddings") from exc

        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"Set {self.api_key_env} to use OpenAI-compatible embeddings")
        client = OpenAI(api_key=api_key, base_url=self.base_url)
        response = client.embeddings.create(model=self.model, input=texts)
        ordered = sorted(response.data, key=lambda item: item.index)
        return [list(item.embedding) for item in ordered]


class OllamaEmbeddingProvider(EmbeddingProvider):
    name = "ollama"

    def __init__(self, model: str, *, base_url: str | None = None) -> None:
        self.model = model
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        payload = json.dumps({"model": self.model, "prompt": text}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Unable to reach Ollama at {self.base_url}: {exc}") from exc
        return list(data["embedding"])


def create_embedder(config: SeamConfig) -> EmbeddingProvider:
    provider = config.embedding_provider.lower()
    model = config.embedding_model
    if provider == "local":
        return LocalHashEmbeddingProvider(model=model)
    if provider == "openai":
        return OpenAIEmbeddingProvider(
            model=model or "text-embedding-3-small",
            api_key_env=config.openai_api_key_env,
            base_url=None,
        )
    if provider == "custom":
        return OpenAIEmbeddingProvider(
            model=model,
            api_key_env=config.openai_api_key_env,
            base_url=config.embedding_base_url,
        )
    if provider == "ollama":
        return OllamaEmbeddingProvider(model=model or "nomic-embed-text", base_url=config.embedding_base_url)
    raise ValueError(f"Unknown embedding provider '{config.embedding_provider}'")


def batch(iterable: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(iterable), size):
        yield iterable[index : index + size]
