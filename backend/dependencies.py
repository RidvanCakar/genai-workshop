"""Dependency Injection — somut LLMClient seçimi BURADA yapılır.

routes.py somut sınıfı (GeminiClient) bilmez; sadece soyut LLMClient'a
bağımlıdır. Provider değiştirmek = bu dosyada tek satır (Dependency Inversion).
Offline/test için GeminiClient yerine MockClient döndürmen yeterli.
"""

from __future__ import annotations

from ai_service.llm_client import GeminiClient, LLMClient


def get_llm_client() -> LLMClient:
    return GeminiClient()
    # Offline / API key olmadan denemek için:
    # from ai_service.llm_client import MockClient
    # return MockClient()
