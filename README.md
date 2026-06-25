# GenAI MVP — Başlangıç Şablonu

> **Python 202: Sıfırdan Production'a GenAI Application Workshop** başlangıç iskeleti.
> Ücretsiz bir veri kaynağını **Gemini** ile birleştirip, Clean Code / SOLID prensipleriyle
> yapılandırılmış, **Cloud Run**'da canlı çalışan bir GenAI MVP'si üretmen için hazırlandı.

Bu repo **proje-bağımsız bir iskelettir**. SOLID katmanları ve deploy altyapısı hazır gelir;
sen sadece "kendi projenin etini" doldurursun.

---

## 1. Bu şablon ile nasıl çalışılır?

```
1. Bu repoyu klonla
2. Kendi use-case'ini seç (özetleyici, soru-cevap, sınıflandırıcı, çevirmen...)
3. Kendi PRD'ni yaz (referans: workshop'taki örnek PRD)
4. Aşağıdaki TODO'lu dosyaları kendi projene göre doldur
5. Lokalde çalıştır → Cloud Run'a deploy et
```

> 💡 **Ne yapacağına karar veremedin mi?** [**ORNEK_CALISMALAR.md**](ORNEK_CALISMALAR.md)
> içinde 6 hazır fikir var — her biri için hangi ücretsiz kaynağı, hangi kütüphaneyi ve
> hangi kodu kullanacağın yazılı. Bak, birini seç, kopyala-doldur.

### Hazır gelen (dokunmana gerek yok)
| Dosya | Görevi |
|---|---|
| `ai_service/llm_client.py` | `LLMClient` (ABC) + `GeminiClient` + `MockClient` — SOLID'in kalbi |
| `backend/dependencies.py` | `get_llm_client()` — Dependency Injection |
| `backend/main.py` | FastAPI app, CORS, `/health`, static mount |
| `Dockerfile`, `deploy.sh`, `teardown.sh`, `Makefile` | Production + deploy altyapısı |

### Sen dolduracaksın (`# TODO`)
| Dosya | Ne yazacaksın |
|---|---|
| `ai_service/data_sources.py` | Veri kaynağından içerik çekme (`fetch_source`) |
| `ai_service/prompts.py` | Prompt template'lerin |
| `backend/schemas.py` | Request/response alanların |
| `backend/routes.py` | Endpoint(ler)in (veri çek → prompt → LLM → döndür) |
| `frontend/index.html`, `frontend/app.js` | Arayüz (gerekirse) |

---

## 2. Lokal kurulum (~10 dk)

```bash
# 1. Sanal ortam
python -m venv .venv && source .venv/bin/activate

# 2. Bağımlılıklar
make install            # veya: pip install -r requirements.txt

# 3. API key
cp .env.example .env    # .env içine GEMINI_API_KEY'ini yaz
#   API key: https://aistudio.google.com/apikey (ücretsiz)

# 4. Çalıştır
make run                # http://localhost:8080
```

Açılış kontrolleri:
- `http://localhost:8080/health` → `{"status": "ok"}`
- `http://localhost:8080/docs` → Swagger UI (endpoint'lerini buradan test et)
- `http://localhost:8080/` → frontend

> **API key olmadan denemek?** `backend/dependencies.py` içinde `GeminiClient()` yerine
> `MockClient()` döndür — sahte yanıtla akış uçtan uca çalışır.

---

## 3. SOLID haritası

- **S — Single Responsibility:** `ai_service` LLM ile konuşur (HTTP bilmez), `data_sources` sadece veri çeker, `routes` sadece HTTP katmanıdır.
- **O — Open/Closed:** Yeni provider = yeni `LLMClient` alt sınıfı; mevcut kod değişmez.
- **L — Liskov:** `GeminiClient` ↔ `MockClient` aynı interface, biri diğerinin yerine geçer.
- **I — Interface Segregation:** `LLMClient` minimal — sadece `generate`.
- **D — Dependency Inversion:** `routes` somut `GeminiClient`'a değil, soyut `LLMClient`'a bağımlı; bağ `dependencies.py`'de kurulur.

---

## 4. Deploy (Cloud Run)

```bash
# .env yüklü olmalı (GEMINI_API_KEY, GEMINI_MODEL)
export $(grep -v '^#' .env | xargs)

make deploy             # gcloud run deploy --source . (bölge: us-central1)
```

İlk build birkaç dakika sürebilir. Çıktıdaki `*.run.app` URL'i public uygulamandır.

### Temizlik (maliyet güvenliği)
```bash
make teardown           # servisi siler
```

> **Notlar:** `--allow-unauthenticated` workshop için kasıtlıdır; production'da auth ekle.
> Gemini free tier'ı korumak için billing'siz ayrı bir GCP projesi kullan.

---

## 5. Model yapılandırması

`GEMINI_MODEL` env değişkeninden okunur (default `gemini-3-flash-preview`).
Free tier sıkışırsa `gemini-3-flash-lite` veya `gemini-3.5-flash`'a tek satırla geçebilirsin.
`-latest` alias'ları kullanma (Google kısa ihbarla değiştirir).

> Sadece **`google-genai`** SDK'sı kullanılır (`from google import genai`).
> Eski `google-generativeai` kullanılmaz.

---

## 6. Yardımcı dosyalar ne işe yarar?

Repodaki her dosya "kod" değil. Aşağıdakiler projeyi **çalıştırma, paketleme ve
dağıtma** işini kolaylaştıran yardımcı dosyalardır. Eğitim amaçlı kısa kısa:

| Dosya | Ne işe yarar? | Zorunlu mu? |
|---|---|---|
| `requirements.txt` | Projenin kullandığı Python kütüphanelerinin listesi. `pip install -r` bunu okur. | ✅ Evet |
| `Makefile` | Uzun komutlara kısa takma ad verir (`make run` → uzun uvicorn komutu). Ezber azaltır. | ⚪ Kolaylık |
| `pyproject.toml` | Projenin kimlik kartı: adı, sürümü, Python versiyonu, linter ayarları. Modern Python standardı. | ⚪ Kolaylık |
| `Dockerfile` | Uygulamayı bir **container imajına** paketler. Cloud Run bunu çalıştırır. | ✅ Deploy için |
| `deploy.sh` | Tek komutla Cloud Run'a yükler (`gcloud run deploy --source .`). | ⚪ Kolaylık |
| `teardown.sh` | Deploy edilen servisi **siler** (maliyet güvenliği — workshop sonu çalıştır). | ⚪ Önerilen |
| `.dockerignore` | `docker build` sırasında imaja **kopyalanmayacak** dosyalar (`.venv`, `.git`, `.env`...). İmajı küçültür, `.env` sızıntısını önler. | ✅ Önerilen |
| `.gcloudignore` | Aynı mantık, ama `gcloud` kaynağı yüklerken. Google'a gereksiz/gizli dosya göndermez. | ✅ Önerilen |
| `.gitignore` | Git'in **takip etmeyeceği** dosyalar (`.env`, `__pycache__`...). API key'in repoya kazara girmesini engeller. | ✅ Önerilen |
| `.env.example` | Hangi ortam değişkenlerine ihtiyaç olduğunu gösteren şablon. Gerçek `.env`'i bundan kopyalarsın. | ✅ Evet |

### Neden `.env` her yerde "ignore" ediliyor?
`.env` senin **gizli API key'ini** tutar. Üç ayrı ignore dosyası da (`.gitignore`,
`.dockerignore`, `.gcloudignore`) onu dışarıda bırakır ki key'in ne GitHub'a, ne
Docker imajına, ne de Google'a kazara sızsın. Production'da gizli bilgiler kodla
değil, platformun ortam değişkenleriyle (Cloud Run'da `--set-env-vars`) verilir.

### Container / imaj ne demek?
`Dockerfile`, uygulamanı + Python + tüm kütüphaneleri tek bir **kutuya** (imaj)
koyar. Bu kutu senin bilgisayarında da, Cloud Run'da da **aynı** çalışır —
"bende çalışıyordu" sorununu ortadan kaldırır. Cloud Run bu kutuyu alır, internete
açık bir URL'de çalıştırır ve kimse kullanmazsa otomatik kapatır (scale-to-zero → $0).
