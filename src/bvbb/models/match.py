from datetime import date, time

from pydantic import BaseModel


class ScheduleEntry(BaseModel):
    meeting_id: int
    match_day: int | None = None
    match_date: date | None = None
    match_time: time | None = None
    venue: str | None = None
    home_team: str
    away_team: str
    score: str | None = None  # e.g. "5:3"
    report_url: str | None = None


class SetScore(BaseModel):
    home: int
    away: int


class DisciplineResult(BaseModel):
    discipline: str  # e.g. "1.HD", "DD", "1.HE", "DE", "GD"
    home_players: list[str]
    away_players: list[str]
    home_player_ids: list[int] = []
    away_player_ids: list[int] = []
    home_club_ids: list[int] = []
    away_club_ids: list[int] = []
    sets: list[SetScore]
    home_match_point: int = 0
    away_match_point: int = 0


class MatchReport(BaseModel):
    meeting_id: int
    home_team: str
    away_team: str
    home_score: int = 0
    away_score: int = 0
    match_date: date | None = None
    disciplines: list[DisciplineResult]
