from pathlib import Path

import streamlit as st

from bvbb.config import settings
from bvbb.db import (
    init_db,
    list_championships,
    load_championship,
    load_club,
    load_match_report,
    load_player,
    load_schedule,
    load_standings,
    search_clubs,
    search_players,
)
from bvbb.models.championship import Championship
from bvbb.models.club import Club
from bvbb.models.match import MatchReport, ScheduleEntry
from bvbb.models.player import Player
from bvbb.models.standing import GroupStandings


class DataStore:
    def __init__(self, db_path: Path) -> None:
        self._session = init_db(db_path)

    def list_championships(self) -> list[str]:
        return list_championships(self._session)

    def get_championship(self, code: str) -> Championship:
        return load_championship(self._session, code)

    def get_standings(self, group_id: int, championship_code: str) -> GroupStandings:
        return load_standings(self._session, group_id, championship_code)

    def get_schedule(self, group_id: int, championship_code: str) -> list[ScheduleEntry]:
        return load_schedule(self._session, group_id, championship_code)

    def get_match_report(self, meeting_id: int, championship_code: str) -> MatchReport:
        return load_match_report(self._session, meeting_id, championship_code)

    def get_player(self, person_id: int, championship_code: str) -> Player:
        return load_player(self._session, person_id, championship_code)

    def get_club(self, club_id: int, championship_code: str) -> Club:
        return load_club(self._session, club_id, championship_code)

    def search_players(self, query: str, championship_code: str) -> list[tuple[int, str, str | None]]:
        return search_players(self._session, query, championship_code)

    def search_clubs(self, query: str, championship_code: str) -> list[tuple[int, str]]:
        return search_clubs(self._session, query, championship_code)


@st.cache_resource
def get_store() -> DataStore:
    return DataStore(Path(settings.db_path))
