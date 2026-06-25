# WikiTLDR — Örnek Proje PRD'si

> **Python 202: Sıfırdan Production'a GenAI Application Workshop** — Eğitmen sahne projesi.
> Bu doküman doğrudan **Claude Code**'a verilerek base repo'nun üretilmesi için hazırlanmıştır. İçerik; sunumda anlatılan Clean Code, SOLID ve Cloud Run deploy başlıklarıyla birebir uyumludur. Katılımcılar bu repo'yu GitHub'dan **boş iskelet (start branch)** olarak klonlayıp kendi seçtikleri use-case'e göre doldurur.

---

## 0. Tek Bakışta

| Alan | Karar |
|---|---|
| Proje adı | **WikiTLDR** |
| Ne yapar? | Bir Wikipedia konusunu çekip Gemini ile (a) sade Türkçe TLDR üretir, (b) sadece o makaleye dayanarak soru-cevap yapar (basit grounding/RAG) |
| Ücretsiz kaynak | **Wikipedia REST/MediaWiki API** (API key gerektirmez, sadece `User-Agent` ister) |
| PyPI kütüphanesi | **`wikipedia-api`** (modül adı `wikipediaapi`, v0.15.0, aktif maintain) |
| LLM | **Gemini** (`google-genai` SDK 2.8.0, free tier) |
| Backend | **FastAPI** (async) |
| Frontend | Statik **HTML + Vanilla JS** (tek sayfa, fetch ile backend'i çağırır) |
| Deploy | **Cloud Run** (`gcloud run deploy --source .`, bölge `us-central1`) |
| Maliyet | **$0** (Gemini free tier + Cloud Run free tier) |

### Neden bu kombinasyon? (sunumla bağ)
- **Sıfır setup friction:** Wikipedia API key istemez → workshop'ta "key alalım, billing açalım" kaybı yaşanmaz, herkes 5 dakikada koşar.
- **Güçlü demo etkisi:** Uzun ansiklopedik metin → 3 cümle TLDR + makaleye sadık soru-cevap. Bu, production RAG sistemlerinin minyatür hâlidir; senior'a "grounding", junior'a "AI özetliyor" olarak aynı anda hitap eder.
- **"Ücretsiz kaynak + PyPI kütüphanesi + Gemini" üçlüsünü** en temiz gösteren örnek.

---

## 1. Requirement Summary

**Business Goal:** Katılımcıya, ücretsiz bir public veri kaynağını bir LLM ile birleştirip Clean Code/SOLID prensipleriyle yapılandırılmış, Cloud Run'da canlı çalışan bir GenAI MVP'sini uçtan uca deneyimletmek. Eğitmenin sahnede takip edeceği "altın yol" (golden path) budur.

**Users:**
- *Workshop katılımcısı (junior):* "AI özetleyen bir uygulama yaptım ve internette canlı" deneyimini yaşar.
- *Workshop katılımcısı (senior):* SOLID/DI soyutlamasını, async LLM çağrısını, grounding prompt'unu ve serverless deploy'u referans implementation olarak görür.
- *Eğitmen (Göker):* Sahnede her adımı canlı gösterir; aynı repo katılımcıların `start` branch'idir.

**Success Criteria:**
1. `git clone` + `pip install` + `.env` doldurma → 10 dakikada lokal çalışan app.
2. `POST /summarize` bir Wikipedia konusu için 3 cümlelik Türkçe TLDR döner.
3. `POST /ask` makaleye dayalı, "metinde yok" diyebilen bir cevap döner.
4. `gcloud run deploy --source .` → çalışan public `*.run.app` URL'i.
5. Frontend `/` adresinde açılır, iki endpoint'i de tarayıcıdan kullanılabilir kılar.
6. Kod, sunumda anlatılan SOLID prensiplerini gözle görülür biçimde örnekler (özellikle Dependency Inversion → `LLMClient` soyutlaması).

---

## 2. Tech Stack

| Katman | Teknoloji | Not |
|---|---|---|
| Dil | Python 3.11+ | Cloud Run buildpack uyumlu |
| Web framework | FastAPI + Uvicorn | async, otomatik `/docs` (Swagger) |
| Validation | Pydantic v2 | request/response şemaları |
| LLM SDK | `google-genai` **2.8.0** | `from google import genai` — eski `google-generativeai` KULLANILMAZ (30 Kasım 2025'te EOL) |
| Veri kaynağı | `wikipedia-api` 0.15.0 | `User-Agent` zorunlu |
| HTTP (gerekirse) | `httpx` | async |
| Config | `python-dotenv` | `.env` okuma |
| Frontend | HTML + Vanilla JS (fetch) | build step yok |
| Container | Docker (`python:3.11-slim`) | production örneği; buildpack da çalışır |
| Deploy | Cloud Run (`--source .` buildpack) | bölge `us-central1` (free tier bölgesi) |

**Model string:** `GEMINI_MODEL` env değişkeninden okunur (default `gemini-3-flash-preview`). `-latest` alias'ları kullanılmaz (Google bunları kısa ihbarla değiştirir). Free tier düşerse `gemini-3-flash-lite` veya `gemini-3.5-flash`'a tek satırla geçilir.

---

## 3. Architecture Draft

```
[ Frontend (statik HTML/JS) ]
            │  fetch (JSON)
            ▼
[ Backend — FastAPI ]
   /health   /summarize   /ask   /docs
            │  Depends(get_llm_client)
            ▼
[ ai_service ]
   ├── data_sources.py   → Wikipedia (wikipedia-api)
   ├── prompts.py        → prompt template'leri
   └── llm_client.py     → LLMClient (ABC) ─┬─ GeminiClient
                                            └─ MockClient
            │
            ▼
[ Gemini API (google-genai, free tier) ]

  Hepsi tek container → Cloud Run (scale-to-zero)
```

**Akış:**
1. Frontend kullanıcıdan `topic` (ve `/ask` için `question`) alır → backend'e POST.
2. Backend, `ai_service.data_sources.fetch_wikipedia(topic)` ile makale içeriğini ve URL'i çeker.
3. `prompts.py`'den uygun template doldurulur.
4. `Depends(get_llm_client)` ile enjekte edilen `LLMClient.generate(prompt)` çağrılır (async).
5. Sonuç Pydantic response modeliyle döner.

**SOLID haritalaması (sunumla birebir):**
- **S (Single Responsibility):** `ai_service` LLM ile konuşur, HTTP bilmez; `data_sources` sadece veri çeker; `routes` sadece HTTP katmanı.
- **O (Open/Closed):** Yeni provider eklemek için yeni `LLMClient` alt sınıfı yazılır, mevcut kod değişmez.
- **L (Liskov):** `GeminiClient` ve `MockClient` aynı interface'i implement eder, biri diğerinin yerine geçer (test'te Mock).
- **I (Interface Segregation):** `LLMClient` minimal — `generate` (ve opsiyonel `generate_stream`); şişkin değil.
- **D (Dependency Inversion):** `routes` somut `GeminiClient`'a değil, abstract `LLMClient`'a bağımlı; bağ `dependencies.py`'de kurulur.

---

## 4. Repo Structure (Claude Code bunu üretecek)

```
wiki-tldr/                          # workshop'ta: genai-workshop
├── README.md                       # setup + deploy + "kendi use-case'ini nasıl doldurursun"
├── Makefile                        # install / run / deploy / teardown
├── deploy.sh                       # gcloud run deploy --source .
├── teardown.sh                     # gcloud run services delete (maliyet güvenliği)
├── Dockerfile                      # production örneği (buildpack da çalışır)
├── .dockerignore
├── .gcloudignore
├── .env.example                    # GEMINI_API_KEY, GEMINI_MODEL
├── requirements.txt
├── pyproject.toml
├── frontend/
│   ├── index.html                  # tek sayfa: topic input + summarize/ask butonları
│   └── app.js                      # fetch ile backend çağrısı, sonuç render
├── backend/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app, CORS, static mount, router include
│   ├── routes.py                   # /summarize, /ask
│   ├── schemas.py                  # Pydantic request/response modelleri
│   └── dependencies.py             # get_llm_client() — Dependency Injection
└── ai_service/
    ├── __init__.py
    ├── llm_client.py               # LLMClient (ABC) + GeminiClient + MockClient
    ├── prompts.py                  # SUMMARIZE_PROMPT, ASK_PROMPT
    └── data_sources.py             # fetch_wikipedia()
```

> **Katılımcı deneyimi:** `start` branch'inde `ai_service/data_sources.py`, `prompts.py` ve `routes.py` içindeki iş mantığı `# TODO` ile boş bırakılır. `llm_client.py` (soyutlama) ve `main.py`/`dependencies.py` (iskelet) hazır gelir — yani katılımcı SOLID iskeleti bozmadan sadece "kendi projesinin etini" doldurur.

---

## 5. Endpoint Spesifikasyonu

### `GET /health`
- Yanıt: `{"status": "ok"}`
- Cloud Run health check + "ayakta mı?" testi.

### `POST /summarize`
- İstek: `{ "topic": "Mustafa Kemal Atatürk", "max_sentences": 3 }`
- Davranış: Wikipedia'dan `topic` sayfasının özetini çek → Gemini ile `max_sentences` cümlede sade Türkçe TLDR.
- Yanıt: `{ "title": "...", "tldr": "...", "source_url": "https://tr.wikipedia.org/..." }`
- Sayfa bulunamazsa: `404` + `{"detail": "Konu bulunamadı"}`.

### `POST /ask`
- İstek: `{ "topic": "Kuantum bilgisayar", "question": "Kübit nedir?" }`
- Davranış: Makale metnini bağlam olarak ver → Gemini'ye **sadece bu metne dayan, bilmiyorsan 'metinde yok' de** talimatı (grounding).
- Yanıt: `{ "answer": "...", "source_url": "..." }`

### `GET /` (frontend)
- `frontend/index.html` servis edilir.

### `GET /docs`
- FastAPI otomatik Swagger UI (ücretsiz test arayüzü; sahnede bunu göstereceksin).

---

## 6. Anahtar Kod Örnekleri (referans implementation)

### `ai_service/llm_client.py` — SOLID'in kalbi
```python
from abc import ABC, abstractmethod
import os


class LLMClient(ABC):
    """LLM provider soyutlaması — Dependency Inversion'ın merkezi."""

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        ...


class GeminiClient(LLMClient):
    def __init__(self, model: str | None = None):
        from google import genai
        self._client = genai.Client()  # GEMINI_API_KEY env'den okunur
        self._model = model or os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

    async def generate(self, prompt: str) -> str:
        resp = await self._client.aio.models.generate_content(
            model=self._model,
            contents=prompt,
        )
        return resp.text


class MockClient(LLMClient):
    """Offline/test için — API key gerektirmez."""

    async def generate(self, prompt: str) -> str:
        return f"[MOCK] {prompt[:60]}..."
```

### `ai_service/data_sources.py`
```python
import wikipediaapi

_wiki = wikipediaapi.Wikipedia(
    user_agent="WikiTLDR-Workshop (ornek@example.com)",
    language="tr",
)


def fetch_wikipedia(topic: str) -> tuple[str, str]:
    """Konu sayfasının metnini ve URL'ini döner. Bulunamazsa ValueError."""
    page = _wiki.page(topic)
    if not page.exists():
        raise ValueError("Konu bulunamadı")
    return page.text, page.fullurl
```

### `ai_service/prompts.py`
```python
SUMMARIZE_PROMPT = (
    "Aşağıdaki Wikipedia içeriğini {max_sentences} cümlede, "
    "sade ve akıcı Türkçe ile özetle. Teknik jargondan kaçın.\n\n"
    "İçerik:\n{content}"
)

ASK_PROMPT = (
    "Aşağıdaki metne SADECE bu metne dayanarak yanıt ver. "
    "Cevap metinde yoksa 'Bu bilgi makalede yer almıyor.' de.\n\n"
    "Metin:\n{content}\n\nSoru: {question}"
)
```

### `backend/dependencies.py` — Dependency Injection
```python
from functools import lru_cache
from ai_service.llm_client import LLMClient, GeminiClient


@lru_cache
def get_llm_client() -> LLMClient:
    return GeminiClient()
```

### `backend/routes.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from ai_service.llm_client import LLMClient
from ai_service.data_sources import fetch_wikipedia
from ai_service.prompts import SUMMARIZE_PROMPT, ASK_PROMPT
from backend.dependencies import get_llm_client
from backend.schemas import (
    SummarizeRequest, SummarizeResponse, AskRequest, AskResponse,
)

router = APIRouter()


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(req: SummarizeRequest, llm: LLMClient = Depends(get_llm_client)):
    try:
        content, url = fetch_wikipedia(req.topic)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    tldr = await llm.generate(
        SUMMARIZE_PROMPT.format(content=content[:6000], max_sentences=req.max_sentences)
    )
    return SummarizeResponse(title=req.topic, tldr=tldr, source_url=url)


@router.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest, llm: LLMClient = Depends(get_llm_client)):
    try:
        content, url = fetch_wikipedia(req.topic)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    answer = await llm.generate(
        ASK_PROMPT.format(content=content[:6000], question=req.question)
    )
    return AskResponse(answer=answer, source_url=url)
```

### `backend/main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.routes import router

app = FastAPI(title="WikiTLDR")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Frontend en sona mount edilir (route'ları gölgelememesi için)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
```

### `Dockerfile`
```dockerfile
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN adduser --disabled-password --no-create-home appuser
USER appuser
ENV PORT=8080
CMD exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT} --workers 1
```

### `requirements.txt`
```
fastapi
uvicorn[standard]
google-genai==2.8.0
pydantic
httpx
wikipedia-api
python-dotenv
```

### `.env.example`
```
GEMINI_API_KEY=buraya_anahtarini_koy
GEMINI_MODEL=gemini-3-flash-preview
```

### `deploy.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
SERVICE=${1:-genai-mvp}
REGION=${2:-us-central1}
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY},GEMINI_MODEL=${GEMINI_MODEL:-gemini-3-flash-preview}"
```

### `teardown.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
SERVICE=${1:-genai-mvp}
REGION=${2:-us-central1}
gcloud run services delete "$SERVICE" --region "$REGION" --quiet
echo "Servis silindi. Maliyet riski yok."
```

---

## 7. Frontend (statik, build'siz)

`frontend/index.html` minimal ama "gerçek ürün" hissi versin: bir konu input'u, "Özetle" ve "Soru Sor" butonları, sonuç kartı, kaynak linki. Marka paleti kullanılabilir (Grass `#154318`, Pear `#A8E665`, Cloud `#EBF0E6`, Lime `#CDF447`, Dark Green `#062D0A`, Light Green `#D7F3B8`). `app.js` `fetch("/summarize", ...)` ve `fetch("/ask", ...)` ile backend'i çağırır, JSON'u render eder. Tek dosya CSS, harici bağımlılık yok.

---

## 8. Milestones (Claude Code için inşa sırası)

**Phase 1 — İskelet:** Repo yapısı, `main.py` (`/health` + static mount), `llm_client.py` (ABC + Gemini + Mock), `dependencies.py`. `requirements.txt`, `Dockerfile`, `.env.example`. → Lokalde `/health` ve `/docs` açılır.

**Phase 2 — İş mantığı:** `data_sources.py` (Wikipedia), `prompts.py`, `schemas.py`, `routes.py` (`/summarize` + `/ask`). → Lokalde iki endpoint de çalışır.

**Phase 3 — Frontend + Deploy:** `frontend/index.html` + `app.js`, `deploy.sh`, `teardown.sh`, `Makefile`, `README.md`. → `gcloud run deploy --source .` ile public URL.

**Branch planı:** `main` (tam çalışan referans), `start` (TODO'lu boş iskelet — katılımcı buradan başlar), `checkpoint-0-setup`, `checkpoint-1-ai-service`, `checkpoint-2-endpoint`, `checkpoint-3-deployed`.

---

## 9. Risks

**Product:**
- Wikipedia'da konu adı tam eşleşmezse "bulunamadı" → frontend'de net hata mesajı + öneri ("tam başlık dene").
- TLDR çok uzun/dağınık olabilir → prompt'ta cümle sayısı sınırı + içerik truncation (`content[:6000]`).

**Technical:**
- **Gemini free tier 429 (rate limit):** 40+ kişi aynı anda → her katılımcı **kendi API key'i** + ayrı GCP projesi kullanmalı. Senior bonus: `slowapi` + exponential backoff.
- **Model string kararsızlığı:** `gemini-3-flash-preview` preview; `GEMINI_MODEL` env ile tek satırda değiştirilebilir kalsın. Workshop sabahı kendi key'inle bir `generate_content` smoke-test yap.
- **SDK karışıklığı:** Sadece `google-genai`; eski `google-generativeai` / `genai.GenerativeModel(...)` syntax'ı repo'da hiç bulunmasın.
- **Cold build süresi:** İlk `--source .` deploy birkaç dakika sürebilir; sahnede bunu anlatım fırsatına çevir.

**Security / Maliyet:**
- **Billing tuzağı:** Bir projede billing açılırsa o projede Gemini free tier tamamen kaybolur (BigQuery/Storage'dan farklı). Test için billing'siz ayrı proje kullan.
- **`--allow-unauthenticated`:** Workshop için public endpoint kasıtlı; production'da auth gerekir notu düşülmeli.
- **Cleanup zorunlu:** Workshop sonu `teardown.sh` çalıştırılmalı (Cloud Run scale-to-zero'da $0 olsa da disiplin için).

---

## 10. Questions (Claude Code'a vermeden önce netleştirilecekler)

- **P0:** Yok — proje uçtan uca tanımlı, inşaya hazır.
- **P1:** Frontend'de Türkçe Wikipedia (`language="tr"`) mi varsayılan, yoksa dil seçici de eklenecek mi? (Öneri: TR varsayılan, dil seçici opsiyonel bonus.)
- **P2:** `/ask` için streaming response sahnede gösterilecek mi, yoksa senior bonus task olarak mı kalacak? (Öneri: bonus.)
