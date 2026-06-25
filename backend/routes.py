"""HTTP katmanı — sadece istek/yanıt akışını yönetir (Single Responsibility)."""

from __future__ import annotations

import json

import httpx
from fastapi import APIRouter, Depends, HTTPException

from ai_service.data_sources import RateLimitError, fetch_team_full
from ai_service.llm_client import LLMClient
from ai_service.prompts import MATCH_BRIEF_PROMPT, SECTION_PROMPTS
from backend.dependencies import get_llm_client
from backend.schemas import (
    AiBriefRequest,
    MatchBriefResponse,
    TeamInfoResponse,
    TeamRequest,
)

router = APIRouter()


def _llm_error(exc: Exception) -> HTTPException:
    msg = str(exc)
    if "API key" in msg or "API_KEY" in msg:
        return HTTPException(
            status_code=503,
            detail="Gemini API key bulunamadı. .env dosyasına GEMINI_API_KEY ekle ve sunucuyu yeniden başlat.",
        )
    return HTTPException(status_code=502, detail=f"Gemini hatası: {msg}")


def _sportsdb_error(exc: Exception) -> HTTPException:
    if isinstance(exc, RateLimitError):
        return HTTPException(status_code=429, detail=str(exc))
    if isinstance(exc, httpx.HTTPError):
        return HTTPException(
            status_code=502,
            detail="Spor verisi şu an alınamıyor. Lütfen bir dakika sonra tekrar dene.",
        )
    return HTTPException(status_code=500, detail=f"Beklenmeyen hata: {exc}")


@router.post("/team-info", response_model=TeamInfoResponse)
async def team_info(req: TeamRequest) -> TeamInfoResponse:
    """Takım adı al → yapılandırılmış veri döndür (LLM yok, hızlı)."""
    try:
        data = await fetch_team_full(req.team)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (RateLimitError, httpx.HTTPError) as e:
        raise _sportsdb_error(e) from e
    return TeamInfoResponse(**data)


@router.post("/match-brief", response_model=MatchBriefResponse)
async def match_brief(
    req: AiBriefRequest,
    llm: LLMClient = Depends(get_llm_client),
) -> MatchBriefResponse:
    """Seçilen bölüm için AI brifing üret."""
    try:
        data = await fetch_team_full(req.team)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (RateLimitError, httpx.HTTPError) as e:
        raise _sportsdb_error(e) from e

    section = req.section if req.section in SECTION_PROMPTS else "general"
    content = _section_content(data, section)
    prompt_template = SECTION_PROMPTS.get(section, MATCH_BRIEF_PROMPT)

    prompt = prompt_template.format(
        team=data["team_name"],
        brief_mode=data["brief_mode"],
        content=content[:8000],
    )
    try:
        result = await llm.generate(prompt)
    except Exception as e:
        raise _llm_error(e) from e

    return MatchBriefResponse(
        result=result,
        team_name=data["team_name"],
        source_url=data["source_url"],
        brief_mode=data["brief_mode"],
        section=section,
    )


def _section_content(data: dict, section: str) -> str:
    if section == "squad":
        payload = {"players": data["players"], "team_name": data["team_name"]}
    elif section == "matches":
        payload = {
            "upcoming_events": data["upcoming_events"],
            "last_events": data["last_events"],
        }
    elif section == "stadium":
        payload = {"stadium": data["stadium"], "team_name": data["team_name"]}
    else:
        payload = {
            "profile": data["profile"],
            "brief_mode": data["brief_mode"],
            "stadium": {"name": data["stadium"].get("name")},
        }
    return json.dumps(payload, ensure_ascii=False, indent=2)
