"""FastAPI uygulaması — HAZIR gelir.

Genelde dokunman gerekmez: CORS, /health, router include ve statik frontend
mount'u burada kurulur. Yeni endpoint'leri backend/routes.py içine ekle.
"""

from __future__ import annotations

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

load_dotenv()  # lokalde .env okunur; Cloud Run'da env vars zaten set'li

from backend.routes import router  # noqa: E402

app = FastAPI(title="MatchBrief")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Frontend EN SONA mount edilir (API route'larını gölgelememesi için).
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
