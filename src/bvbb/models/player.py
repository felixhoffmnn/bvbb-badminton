from pydantic import BaseModel


class PlayerStats(BaseModel):
    singles_wins: int = 0
    singles_losses: int = 0
    doubles_wins: int = 0
    doubles_losses: int = 0
    mixed_wins: int = 0
    mixed_losses: int = 0


class PlayerMatchRecord(BaseModel):
    date: str | None = None
    discipline: str
    opponents: list[str]
    sets: str  # e.g. "21:15 21:18"
    won: bool


class Player(BaseModel):
    person_id: int
    name: str
    club: str | None = None
    club_id: int | None = None
    stats: PlayerStats = PlayerStats()
    match_history: list[PlayerMatchRecord] = []
