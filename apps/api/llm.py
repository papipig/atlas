from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    def enrich(self, item: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class DryrunLLMProvider(LLMProvider):
    """Deterministic local provider for fixtures, tests and offline operation."""

    def enrich(self, item: dict[str, Any]) -> dict[str, Any]:
        title = str(item.get("title") or "Sans titre")
        text = str(item.get("cleaned_content") or item.get("payload_json") or "")
        content = f"{title}. {text}".strip(". ")

        words = re.findall(r"[\wÀ-ÿ-]{4,}", content.lower())
        stop_words = {"avec", "dans", "pour", "une", "des", "les", "the", "and", "for", "from", "that"}
        counts: dict[str, int] = {}
        for word in words:
            if word not in stop_words:
                counts[word] = counts.get(word, 0) + 1
        tags = [word for word, _ in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:5]]

        actors: list[str] = []
        known_actors = ("France", "Europe", "European Union", "NATO", "United States", "China", "Russia")
        for actor in known_actors:
            if actor.lower() in content.lower():
                actors.append(actor)

        return {
            "summary": content[:360],
            "tags": tags,
            "actors": actors,
            "model_provider": "dryrun",
            "model_name": "deterministic-local-v1",
            "prompt_version": "briefing-v1",
        }


def get_llm_provider() -> LLMProvider:
    return DryrunLLMProvider()
