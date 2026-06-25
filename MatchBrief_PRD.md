# MatchBrief — Proje PRD'si

> **Python 202: Sıfırdan Production'a GenAI Application Workshop** — Katılımcı projesi.
> Takım adı gir → TheSportsDB'den yaklaşan maçları çek → Gemini ile taraftar dostu önizleme üret.

---

## 0. Tek Bakışta

| Alan | Karar |
|---|---|
| Proje adı | **MatchBrief** |
| Ne yapar? | Bir takım adı alır, yaklaşan maç listesini TheSportsDB'den çeker, Gemini ile taraftar dostu kısa önizleme metni üretir |
| Ücretsiz kaynak | **TheSportsDB API** (public test key: `3`, kayıt gerektirmez) |
| PyPI kütüphanesi | **`httpx`** (zaten kurulu) |
| LLM | **Gemini** (`google-genai` SDK 2.8.0, free tier) |
| Backend | **FastAPI** (async) |
| Frontend | Statik **HTML + Vanilla JS** (tek sayfa, fetch ile backend'i çağırır) |
| Deploy | **Cloud Run** (`gcloud run deploy --source .`, bölge `us-central1`) |
| Maliyet | **$0** (Gemini free tier + Cloud Run free tier) |

---

## 1. Requirement Summary

**Business Goal:** Spor severlere, seçtikleri takımın yaklaşan maçlarını AI destekli kısa bir brifing olarak sunmak. Workshop kapsamında ücretsiz veri kaynağı + LLM + Cloud Run deploy deneyimini uçtan uca tamamlamak.

**Users:**
- *Spor sever:* Takım adı yazar, yaklaşan maç önizlemesini okur.
- *Workshop katılımcısı:* SOLID iskelet üzerinde kendi use-case'ini doldurur ve canlı URL paylaşır.

**Success Criteria:**
1. `pip install` + `.env` doldurma → 10 dakikada lokal çalışan app.
2. `POST /match-brief` + `{"team": "Galatasaray"}` → Türkçe maç önizlemesi döner.
3. Takım bulunamazsa → `404` + anlamlı hata mesajı.
4. `gcloud run deploy --source .` → çalışan public `*.run.app` URL'i.
5. Frontend `/` adresinde açılır, takım adı yazılıp sonuç alınabilir.
6. SOLID iskelet korunur (`LLMClient` soyutlaması, katman ayrımı).

---

## 2. Tech Stack

| Katman | Teknoloji | Not |
|---|---|---|
| Dil | Python 3.11+ | Cloud Run buildpack uyumlu |
| Web framework | FastAPI + Uvicorn | async, otomatik `/docs` |
| Validation | Pydantic v2 | request/response şemaları |
| LLM SDK | `google-genai` 2.8.0 | `from google import genai` |
| Veri kaynağı | TheSportsDB REST API | public test key `3` |
| HTTP | `httpx` | async API çağrıları |
| Config | `python-dotenv` | `.env` okuma |
| Frontend | HTML + Vanilla JS | build step yok |
| Deploy | Cloud Run | bölge `us-central1` |

**Model string:** `GEMINI_MODEL` env değişkeninden okunur (default `gemini-3-flash-preview`).

---

## 3. Architecture

```
[ Frontend (statik HTML/JS) ]
            │  fetch POST /match-brief
            ▼
[ Backend — FastAPI ]
   /health   /match-brief   /docs
            │  Depends(get_llm_client)
            ▼
[ ai_service ]
   ├── data_sources.py   → TheSportsDB (searchteams + eventsnext)
   ├── prompts.py        → MATCH_BRIEF_PROMPT
   └── llm_client.py     → LLMClient (ABC) ─┬─ GeminiClient
                                            └─ MockClient
            │
            ▼
[ Gemini API (google-genai, free tier) ]

  Hepsi tek container → Cloud Run (scale-to-zero)
```

**Akış:**
1. Frontend kullanıcıdan `team` alır → backend'e POST.
2. Backend, `fetch_team_events(team)` ile takım ID + yaklaşan maçları çeker.
3. `MATCH_BRIEF_PROMPT` template'i doldurulur.
4. `LLMClient.generate(prompt)` async çağrılır.
5. Sonuç Pydantic response modeliyle döner.

---

## 4. Endpoint Spesifikasyonu

### `GET /health`
- Yanıt: `{"status": "ok"}`

### `POST /match-brief`
- İstek: `{ "team": "Galatasaray" }`
- Davranış: TheSportsDB'den takım ara → yaklaşan maçları çek → Gemini ile taraftar dostu önizleme.
- Yanıt: `{ "result": "...", "team_name": "Galatasaray", "source_url": "https://www.thesportsdb.com/..." }`
- Takım bulunamazsa: `404` + `{"detail": "Takım bulunamadı: ..."}`

### `GET /` (frontend)
- `frontend/index.html` servis edilir.

### `GET /docs`
- FastAPI Swagger UI — endpoint test arayüzü.

---

## 5. Milestones

**Phase 1 — İskelet:** Repo klonlandı, `.env` + Gemini key, `/health` çalışıyor. ✅

**Phase 2 — İş mantığı:** `data_sources.py`, `prompts.py`, `schemas.py`, `routes.py` → `/match-brief` lokalde çalışır.

**Phase 3 — Frontend + Deploy:** `index.html` + `app.js` güncelle → Cloud Run public URL.

---

## 6. Risks

**Product:**
- Takım adı tam eşleşmezse → 404; frontend'de net hata mesajı.
- Aynı isimde birden fazla takım → MVP'de ilk sonuç alınır.
- Yaklaşan maç yok → prompt'ta "uydurma, maç yoksa söyle" talimatı.

**Technical:**
- Gemini free tier 429 → kendi API key kullan.
- TheSportsDB test key sınırlı → demo için büyük kulüpler tercih et (Galatasaray, Manchester United, Barcelona).

**Demo takımları:** Galatasaray, Fenerbahce, Manchester United, Barcelona, Real Madrid.

**Security / Maliyet:**
- Workshop sonu `teardown.sh` çalıştırılmalı.
- `--allow-unauthenticated` workshop için kasıtlı; production'da auth gerekir.
