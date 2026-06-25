"""Pydantic request/response şemaları — API'nin sözleşmesi."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TeamRequest(BaseModel):
    team: str = Field(..., description="Takım adı", examples=["Bayern Munich"])


class TeamImages(BaseModel):
    badge: str | None = None
    banner: str | None = None
    jersey: str | None = None


class TeamProfile(BaseModel):
    name: str
    league: str | None = None
    country: str | None = None
    founded: str | None = None
    manager: str | None = None
    manager_photo: str | None = None
    manager_nationality: str | None = None
    website: str | None = None
    description: str | None = None


class StadiumInfo(BaseModel):
    name: str | None = None
    capacity: str | None = None
    location: str | None = None
    description: str | None = None
    image: str | None = None


class MatchEvent(BaseModel):
    title: str | None = None
    date: str | None = None
    time: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    home_score: str | None = None
    away_score: str | None = None
    home_badge: str | None = None
    away_badge: str | None = None
    venue: str | None = None
    league: str | None = None
    thumb: str | None = None


class PlayerInfo(BaseModel):
    name: str | None = None
    position: str | None = None
    nationality: str | None = None
    birth_date: str | None = None
    photo: str | None = None


class TeamInfoResponse(BaseModel):
    team_id: str
    team_name: str
    source_url: str
    brief_mode: str
    profile: TeamProfile
    images: TeamImages
    stadium: StadiumInfo
    upcoming_events: list[MatchEvent]
    last_events: list[MatchEvent]
    players: list[PlayerInfo]
    players_limit: int = Field(
        10,
        description="TheSportsDB free API kadro limiti",
    )


class AiBriefRequest(TeamRequest):
    section: str = Field(
        default="general",
        description="general | squad | matches | stadium",
    )


class MatchBriefResponse(BaseModel):
    result: str = Field(..., description="AI brifing metni")
    team_name: str
    source_url: str | None = None
    brief_mode: str
    section: str = "general"
