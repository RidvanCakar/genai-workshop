"""LLM provider soyutlaması — bu projenin SOLID kalbi.

Bu dosya HAZIR gelir; iskeleti bozmadan kullan. Yeni bir provider eklemek
istersen (OpenAI, Anthropic, yerel model...) yeni bir `LLMClient` alt sınıfı
yazman yeterli — mevcut kod değişmez (Open/Closed + Dependency Inversion).
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod


class LLMClient(ABC):
    """LLM provider soyutlaması — Dependency Inversion'ın merkezi.

    Interface bilerek minimal tutulur (Interface Segregation): sadece `generate`.
    routes.py somut sınıfa değil, bu soyut tipe bağımlıdır.
    """

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        ...


class GeminiClient(LLMClient):
    """Google Gemini (google-genai SDK) ile gerçek üretim.

    NOT: Sadece `google-genai` kullanılır. Eski `google-generativeai`
    (genai.GenerativeModel) KULLANILMAZ — EOL.
    """

    def __init__(self, model: str | None = None):
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY")
        self._client = genai.Client(api_key=api_key)
        self._model = model or os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

    async def generate(self, prompt: str) -> str:
        resp = await self._client.aio.models.generate_content(
            model=self._model,
            contents=prompt,
        )
        if not resp.text:
            raise ValueError("Gemini boş yanıt döndürdü.")
        return resp.text


class MockClient(LLMClient):
    """Offline/test için — API key gerektirmez.

    GeminiClient ile aynı interface'i implement eder (Liskov): biri diğerinin
    yerine sorunsuz geçer. dependencies.py içinde tek satırla aktif edilir.
    """

    async def generate(self, prompt: str) -> str:
        return f"[MOCK] {prompt[:60]}..."
