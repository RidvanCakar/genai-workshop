"""Veri kaynağı katmanı — Single Responsibility: sadece dış veriyi çeker.

TheSportsDB free API (public test key: 3) — ücretsiz, kayıt gerekmez.
Free tier kadro limiti: API başına en fazla ~10 oyuncu (TheSportsDB kısıtı).
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import httpx

_BASE_URL = "https://www.thesportsdb.com/api/v1/json/3"
# TheSportsDB free tier lookup_all_players limiti
_FREE_PLAYER_LIMIT = 10


class RateLimitError(Exception):
    """TheSportsDB 429 — çok fazla istek."""


def _ensure_ok(resp: httpx.Response) -> None:
    if resp.status_code == 429:
        raise RateLimitError(
            "TheSportsDB istek limiti doldu. Bir dakika bekleyip tekrar dene."
        )
    resp.raise_for_status()


_MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}

_RESULT_ROW_RE = re.compile(
    r"<tr><td[^>]*>.*?"
    r"(?P<day>\d{1,2})\s+(?P<month>\w+)\s+<span class='team-table-year'>(?P<year>\d{2})</span>"
    r".*?team-fixture-name-full'>(?P<home>[^<]+)</span>"
    r".*?text-nowrap'>(?P<home_score>\d+)\s*-\s*(?P<away_score>\d+)\s*"
    r".*?team-fixture-name-full'>(?P<away>[^<]+)</span>",
    re.DOTALL,
)


def _parse_display_date(day: str, month: str, year2: str) -> str:
    year = 2000 + int(year2)
    month_num = _MONTHS.get(month[:3], 1)
    return f"{year}-{month_num:02d}-{int(day):02d}"


def _badge_from_row(row: str, kind: str) -> str | None:
    match = re.search(rf"src='([^']+)' alt='tiny {kind} badge icon'", row)
    return match.group(1) if match else None


def _parse_last_events_from_page(html: str, limit: int = 5) -> list[dict[str, Any]]:
    """TheSportsDB takım sayfasındaki Results tablosunu okur (free API'de 5 maç)."""
    idx = html.find("Results</td>")
    if idx == -1:
        return []

    chunk = html[idx : idx + 15000]
    rows = re.findall(r"<tr><td width='5%'.*?</tr>", chunk, re.DOTALL)
    events: list[dict[str, Any]] = []

    for row in rows[:limit]:
        match = _RESULT_ROW_RE.search(row)
        if not match:
            continue

        home = match.group("home").strip()
        away = match.group("away").strip()
        events.append(
            {
                "title": f"{home} vs {away}",
                "date": _parse_display_date(
                    match.group("day"),
                    match.group("month"),
                    match.group("year"),
                ),
                "time": None,
                "home_team": home,
                "away_team": away,
                "home_score": match.group("home_score"),
                "away_score": match.group("away_score"),
                "home_badge": _badge_from_row(row, "home"),
                "away_badge": _badge_from_row(row, "away"),
                "venue": None,
                "league": None,
                "thumb": None,
            }
        )

    return events


def _trim_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": event.get("strEvent") or event.get("title"),
        "date": event.get("dateEvent") or event.get("date"),
        "time": event.get("strTime") or event.get("time"),
        "home_team": event.get("strHomeTeam") or event.get("home_team"),
        "away_team": event.get("strAwayTeam") or event.get("away_team"),
        "home_score": event.get("intHomeScore") or event.get("home_score"),
        "away_score": event.get("intAwayScore") or event.get("away_score"),
        "home_badge": event.get("strHomeTeamBadge") or event.get("home_badge"),
        "away_badge": event.get("strAwayTeamBadge") or event.get("away_badge"),
        "venue": event.get("strVenue") or event.get("venue"),
        "league": event.get("strLeague") or event.get("league"),
        "thumb": event.get("strThumb") or event.get("thumb"),
    }


def _trim_player(player: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": player.get("strPlayer"),
        "position": player.get("strPosition"),
        "nationality": player.get("strNationality"),
        "birth_date": player.get("dateBorn"),
        "photo": player.get("strThumb") or player.get("strCutout"),
    }


def _team_slug(name: str) -> str:
    return name.lower().replace(" ", "-")


def _empty_manager() -> dict[str, str | None]:
    return {"name": None, "photo": None, "nationality": None}


def _team_page_url(team_id: str, team_name: str) -> str:
    return f"https://www.thesportsdb.com/team/{team_id}-{_team_slug(team_name)}"


async def _fetch_manager(
    client: httpx.AsyncClient,
    team_id: str,
    team_name: str,
    detail: dict[str, Any],
    page_html: str | None = None,
) -> dict[str, str | None]:
    """Free API'de strManager boş gelebilir; takım sayfasından + lookupplayer ile tamamlanır."""
    api_name = detail.get("strManager")
    if api_name:
        return {"name": api_name, "photo": None, "nationality": None}

    html = page_html
    if html is None:
        page_resp = await client.get(
            _team_page_url(team_id, team_name),
            headers={"User-Agent": "MatchBrief-Workshop/1.0"},
            follow_redirects=True,
        )
        if page_resp.status_code != 200:
            return _empty_manager()
        html = page_resp.text

    match = re.search(
        r"Manager</b>.*?href='/player/(\d+)-",
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return _empty_manager()

    pl_resp = await client.get(
        f"{_BASE_URL}/lookupplayer.php",
        params={"id": match.group(1)},
    )
    if pl_resp.status_code != 200:
        return _empty_manager()

    try:
        players = pl_resp.json().get("players") or []
    except Exception:
        return _empty_manager()

    if not players:
        return _empty_manager()

    player = players[0]
    return {
        "name": player.get("strPlayer"),
        "photo": player.get("strThumb") or player.get("strCutout"),
        "nationality": player.get("strNationality"),
    }


async def _fetch_team_players(
    client: httpx.AsyncClient,
    team_id: str,
) -> list[dict[str, Any]]:
    """Free API: lookup_all_players (max ~10 oyuncu)."""
    resp = await client.get(
        f"{_BASE_URL}/lookup_all_players.php",
        params={"id": team_id},
    )
    _ensure_ok(resp)

    players = resp.json().get("player") or []
    return [_trim_player(p) for p in players[:_FREE_PLAYER_LIMIT]]


def _build_team_payload(
    team_info: dict[str, Any],
    lookup_data: dict[str, Any],
    next_data: dict[str, Any],
    last_data: dict[str, Any],
    players: list[dict[str, Any]],
    manager: dict[str, str | None],
    team_id: str,
    team_name: str,
    page_html: str = "",
) -> dict[str, Any]:
    detail = (lookup_data.get("teams") or [{}])[0]
    upcoming = next_data.get("events") or []
    brief_mode = "upcoming" if upcoming else "off_season"

    last_from_page = _parse_last_events_from_page(page_html)
    last_from_api = [
        _trim_event(e)
        for e in (last_data.get("results") or last_data.get("events") or [])
    ]
    last_events = last_from_page or last_from_api

    return {
        "team_id": team_id,
        "team_name": team_name,
        "source_url": f"https://www.thesportsdb.com/team/{team_id}",
        "brief_mode": brief_mode,
        "players_limit": _FREE_PLAYER_LIMIT,
        "profile": {
            "name": team_name,
            "league": team_info.get("strLeague") or detail.get("strLeague"),
            "country": team_info.get("strCountry") or detail.get("strCountry"),
            "founded": team_info.get("intFormedYear") or detail.get("intFormedYear"),
            "manager": manager.get("name"),
            "manager_photo": manager.get("photo"),
            "manager_nationality": manager.get("nationality"),
            "website": team_info.get("strWebsite") or detail.get("strWebsite"),
            "description": detail.get("strDescriptionEN") or detail.get("strDescription"),
        },
        "images": {
            "badge": detail.get("strTeamBadge") or detail.get("strBadge") or team_info.get("strBadge"),
            "banner": detail.get("strBanner") or detail.get("strFanart1"),
            "jersey": detail.get("strEquipment") or detail.get("strJersey"),
        },
        "stadium": {
            "name": team_info.get("strStadium") or detail.get("strStadium"),
            "capacity": detail.get("intStadiumCapacity"),
            "location": detail.get("strLocation") or detail.get("strStadiumLocation"),
            "description": detail.get("strStadiumDescription"),
            "image": detail.get("strStadiumThumb"),
        },
        "upcoming_events": [_trim_event(e) for e in upcoming],
        "last_events": last_events,
        "players": players,
    }


async def fetch_team_full(team: str) -> dict[str, Any]:
    """Takım adına göre yapılandırılmış tam veri paketi döndürür."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        search_resp = await client.get(
            f"{_BASE_URL}/searchteams.php",
            params={"t": team},
        )
        _ensure_ok(search_resp)
        search_data = search_resp.json()

        teams = search_data.get("teams")
        if not teams:
            raise ValueError(f"Takım bulunamadı: {team}")

        team_info = teams[0]
        team_id = team_info["idTeam"]
        team_name = team_info.get("strTeam", team)

        next_resp, last_resp, lookup_resp, page_resp = await asyncio.gather(
            client.get(f"{_BASE_URL}/eventsnext.php", params={"id": team_id}),
            client.get(f"{_BASE_URL}/eventslast.php", params={"id": team_id}),
            client.get(f"{_BASE_URL}/lookupteam.php", params={"id": team_id}),
            client.get(
                _team_page_url(team_id, team_name),
                headers={"User-Agent": "MatchBrief-Workshop/1.0"},
                follow_redirects=True,
            ),
        )
        for resp in (next_resp, last_resp, lookup_resp):
            _ensure_ok(resp)

        next_data = next_resp.json()
        last_data = last_resp.json()
        lookup_data = lookup_resp.json()
        detail = (lookup_data.get("teams") or [{}])[0]
        page_html = page_resp.text if page_resp.status_code == 200 else ""

        players, manager = await asyncio.gather(
            _fetch_team_players(client, team_id),
            _fetch_manager(client, team_id, team_name, detail, page_html=page_html),
        )

        return _build_team_payload(
            team_info,
            lookup_data,
            next_data,
            last_data,
            players,
            manager,
            team_id,
            team_name,
            page_html,
        )


async def fetch_team_brief(team: str) -> tuple[str, str, str, str]:
    """LLM brifingi için JSON metin paketi döndürür (geriye uyumluluk)."""
    payload = await fetch_team_full(team)
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    return (
        content,
        payload["source_url"],
        payload["team_name"],
        payload["brief_mode"],
    )
