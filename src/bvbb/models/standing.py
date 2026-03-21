from pydantic import BaseModel


class StandingEntry(BaseModel):
    rank: int
    team: str
    team_url: str | None = None
    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    points: str = ""  # "X:Y" format
    games: str = ""  # "X:Y" format
    sets: str = ""  # "X:Y" format


class GroupStandings(BaseModel):
    group_id: int
    group_name: str
    entries: list[StandingEntry]
