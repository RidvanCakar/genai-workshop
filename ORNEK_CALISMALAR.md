# Örnek Çalışmalar — Kendi Use-Case'ini Seç

> **Python 202: Sıfırdan Production'a GenAI Application Workshop**
>
> Araştırmayla vakit kaybetme. Aşağıda **6 hazır fikir** var; hepsi aynı tarifi paylaşır:
> **ücretsiz bir kaynak + bir PyPI kütüphanesi + Gemini**. Hepsi bu repodaki aynı iskelete
> (`frontend / backend / ai_service`) oturur. Bir tanesini çalıştırabilirsen hepsini çalıştırabilirsin.

---

## Önce bir bak, sonra seç

| # | Template | İlgi alanı | Ücretsiz kaynak | PyPI kütüphanesi | API key? | Zorluk |
|---|---|---|---|---|---|---|
| ⭐ | **WikiTLDR** *(eğitmen örneği)* | Genel / RAG | Wikipedia | `wikipedia-api` | ❌ Yok | 🟢 Kolay |
| 1 | **FinanceTLDR** 📈 | Finans | Yahoo Finance | `yfinance` | ❌ Yok | 🟢 Kolay |
| 2 | **NewsDigest** 📰 | Haber / İçerik | Google News / Guardian | `gnews` / `feedparser` | 🟡 Opsiyonel | 🟢 Kolay |
| 3 | **DevRadar** 🛠 | Geliştirici | Hacker News (Algolia) | `httpx` | ❌ Yok | 🟢 Kolay |
| 4 | **NutriCheck** 🥗 | Sağlık | Open Food Facts | `httpx` | ❌ Yok | 🟢 Kolay |
| 5 | **MatchBrief** ⚽ | Spor | TheSportsDB | `httpx` | ❌ Yok* | 🟡 Orta |
| 6 | **PaperTLDR** 🎓 | Akademi | arXiv | `arxiv` | ❌ Yok | 🟢 Kolay |

<sub>\* TheSportsDB ücretsiz public test key (`3`) kullanır — kayıt gerekmez.</sub>

**Karar veremiyorsan:** İlgi duyduğun alanı seç. Hepsi 2 saatlik workshop'ta junior bir
geliştirici tarafından bile bitirilebilir; hiçbiri kredi kartı istemez, maliyet **$0**.

---

## Her template'te değiştireceğin tek 3 dosya

Hangi fikri seçersen seç, dokunduğun yer hep aynı. SOLID iskelet (`llm_client.py`,
`dependencies.py`, `main.py`) **sabit kalır**.

| Dosya | Ne yazarsın? |
|---|---|
| `ai_service/data_sources.py` | Veriyi **nereden** çekiyorsun (bu sayfadaki kod parçaları buraya gider) |
| `ai_service/prompts.py` | Gemini'ye **ne** soruyorsun (prompt template) |
| `backend/routes.py` | Endpoint'in **adı ve şekli** (veri çek → prompt doldur → `llm.generate`) |
| `backend/schemas.py` | İstek/yanıt alanların (opsiyonel ama önerilir) |

> **Tüm akış:** `routes` → `data_sources.fetch(...)` → `prompts` template'i `.format()` →
> `await llm.generate(prompt)` → yanıt. Bu zinciri bir kez kurduğunda hepsi aynı.

---

## Template 1 — FinanceTLDR 📈

**Ne yapar?** Bir hisse senedinin son fiyat hareketini çeker, Gemini ile *"yatırım tavsiyesi
değildir"* notlu sade bir yorum üretir.

| | |
|---|---|
| **Ücretsiz kaynak** | Yahoo Finance (key gerektirmez, kütüphane üzerinden erişilir) |
| **PyPI** | `yfinance` |
| **Örnek endpoint** | `POST /stock-summary` → `{"ticker": "AAPL"}` |

**Kurulum** — `requirements.txt`'e ekle: `yfinance`

**`data_sources.py`:**
```python
import yfinance as yf

def fetch_stock(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    hist = t.history(period="5d")
    last = hist["Close"].iloc[-1]
    prev = hist["Close"].iloc[0]
    change_pct = (last - prev) / prev * 100
    return {"ticker": ticker, "last_price": round(last, 2),
            "change_pct": round(change_pct, 2)}
```

**Prompt fikri:** *"Şu hisse verisini bir yatırımcıya tek paragrafta sade Türkçe ile yorumla.
Sonuna 'Bu bir yatırım tavsiyesi değildir.' ekle. Veri: {content}"*

> ⚠️ `yfinance` Yahoo'nun public endpoint'lerini kullanır; ara sıra rate-limit olabilir.
> Demo için bir örnek ticker'ın çıktısını önceden cache'le.

---

## Template 2 — NewsDigest 📰

**Ne yapar?** Bir konudaki son haber başlıklarını çeker, Gemini ile tek paragraf brifing üretir.

| | |
|---|---|
| **Ücretsiz kaynak** | Google News RSS (key yok) **veya** The Guardian API (ücretsiz key, ~500 istek/gün, kredi kartısız) |
| **PyPI** | `gnews` (Google News) veya `feedparser` (genel RSS) |
| **Örnek endpoint** | `POST /news-digest` → `{"topic": "yapay zeka"}` |

**Kurulum** — `requirements.txt`'e ekle: `gnews` *(veya `feedparser`)*

**`data_sources.py`:**
```python
from gnews import GNews

def fetch_news(topic: str, max_results: int = 5) -> list[dict]:
    google_news = GNews(language="tr", country="TR", max_results=max_results)
    return google_news.get_news(topic)  # [{title, description, ...}]
```

**Prompt fikri:** *"Aşağıdaki haber başlıklarını tematik, akıcı tek paragraflık bir brifinge
dönüştür. Başlıklar: {content}"*

---

## Template 3 — DevRadar 🛠

**Ne yapar?** Hacker News'te bir teknolojinin tartışma nabzını ölçer; topluluğun ne düşündüğünü özetler.

| | |
|---|---|
| **Ücretsiz kaynak** | Hacker News Algolia Search API — key yok, auth yok |
| **PyPI** | `httpx` *(zaten kurulu)* |
| **Örnek endpoint** | `POST /hn-pulse` → `{"keyword": "rust"}` |

**Kurulum** — ek kütüphane gerekmez (`httpx` şablonda hazır).

**`data_sources.py`:**
```python
import httpx

async def fetch_hn(keyword: str, hits: int = 10) -> list[dict]:
    url = "https://hn.algolia.com/api/v1/search"
    params = {"query": keyword, "tags": "story", "hitsPerPage": hits}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
        return r.json()["hits"]  # [{title, points, url, ...}]
```

**Prompt fikri:** *"Şu Hacker News başlık ve puanlarına bakarak topluluğun '{keyword}' hakkında
şu an ne düşündüğünü 3-4 cümlede özetle. Veri: {content}"*

---

## Template 4 — NutriCheck 🥗

**Ne yapar?** Bir ürünün barkodunu alıp besin değerini çeker, Gemini ile sade sağlık yorumu üretir.

| | |
|---|---|
| **Ücretsiz kaynak** | Open Food Facts API — key yok, auth yok, 3M+ ürün |
| **PyPI** | `httpx` *(zaten kurulu)* |
| **Örnek endpoint** | `POST /nutri-check` → `{"barcode": "3017620422003"}` |

**Kurulum** — ek kütüphane gerekmez.

**`data_sources.py`:**
```python
import httpx

async def fetch_product(barcode: str) -> dict:
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers={"User-Agent": "NutriCheck-Workshop"})
        data = r.json()
    p = data.get("product", {})
    return {"product_name": p.get("product_name"),
            "nutriscore": p.get("nutriscore_grade"),
            "nutriments": p.get("nutriments", {})}
```

**Prompt fikri:** *"Şu ürünün Nutri-Score ve besin değerlerini, sıradan bir tüketicinin
anlayacağı sadelikte yorumla. Sağlık tavsiyesi verme, sadece açıkla. Veri: {content}"*

---

## Template 5 — MatchBrief ⚽

**Ne yapar?** Bir takımın yaklaşan maçlarını çeker, Gemini ile taraftar dostu kısa önizleme yazar.

| | |
|---|---|
| **Ücretsiz kaynak** | TheSportsDB free API (public test key: `3`) |
| **PyPI** | `httpx` *(zaten kurulu)* |
| **Örnek endpoint** | `POST /match-brief` → `{"team": "Galatasaray"}` |

**Kurulum** — ek kütüphane gerekmez.

**`data_sources.py`:**
```python
import httpx

async def fetch_team_events(team: str) -> dict:
    base = "https://www.thesportsdb.com/api/v1/json/3"  # public test key: 3
    async with httpx.AsyncClient() as client:
        sr = await client.get(f"{base}/searchteams.php", params={"t": team})
        team_id = sr.json()["teams"][0]["idTeam"]
        ev = await client.get(f"{base}/eventsnext.php", params={"id": team_id})
        return ev.json()
```

**Prompt fikri:** *"Şu yaklaşan maç listesini taraftar dostu, heyecanlı ama kısa bir önizleme
metnine çevir. Veri: {content}"*

> 🟡 Takım bulunamazsa `teams` boş gelebilir — `data_sources` içinde kontrol et, yoksa
> `ValueError("Takım bulunamadı")` fırlat (routes bunu 404'e çevirir).

---

## Template 6 — PaperTLDR 🎓

**Ne yapar?** arXiv'den son makaleyi çeker, Gemini ile herkesin anlayacağı sade özet üretir.

| | |
|---|---|
| **Ücretsiz kaynak** | arXiv API — key yok, açık erişim |
| **PyPI** | `arxiv` |
| **Örnek endpoint** | `POST /paper-tldr` → `{"query": "diffusion models"}` |

**Kurulum** — `requirements.txt`'e ekle: `arxiv`

**`data_sources.py`:**
```python
import arxiv

def fetch_paper(query: str) -> dict:
    search = arxiv.Search(query=query, max_results=1,
                          sort_by=arxiv.SortCriterion.SubmittedDate)
    result = next(arxiv.Client().results(search))
    return {"title": result.title,
            "authors": [a.name for a in result.authors],
            "abstract": result.summary}
```

**Prompt fikri:** *"Şu akademik özeti, bir lise öğrencisinin anlayacağı sade Türkçe ile,
teknik jargon kullanmadan açıkla. Özet: {content}"*

---

## Kendi fikrin mi var?

Harika — listede olmak zorunda değil. Tek kural: **ücretsiz bir veri kaynağı + bir PyPI
kütüphanesi + Gemini**. Aynı üç dosyayı (`data_sources.py`, `prompts.py`, `routes.py`)
kendi kaynağınla doldur, gerisi aynı kalır.

Ücretsiz kaynak ararken iyi bir başlangıç: [**free-for.dev**](https://free-for.dev) ve
[**public-apis**](https://github.com/public-apis/public-apis). Key gerektirmeyen veya
ücretsiz key veren (kredi kartısız) servisleri tercih et.

> **Anahtar gizliliği:** API key gerektiren bir servis seçersen, key'i `.env`'e koy —
> **asla repoya commit etme**. (`.env` zaten `.gitignore`'da.)
