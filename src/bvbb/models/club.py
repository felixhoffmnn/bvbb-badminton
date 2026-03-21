from pydantic import BaseModel


class ClubTeam(BaseModel):
    team_name: str
    league: str | None = None
    teamtable_id: int | None = None


class Club(BaseModel):
    club_id: int
    name: str
    website: str | None = None
    venues: list[str] = []
    teams: list[ClubTeam] = []
