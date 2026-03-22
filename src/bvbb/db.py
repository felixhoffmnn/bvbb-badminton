from pathlib import Path

from pydantic import TypeAdapter
from sqlmodel import Field, Session, SQLModel, create_engine, select

from bvbb.models.championship import Championship
from bvbb.models.club import Club
from bvbb.models.match import MatchReport, ScheduleEntry
from bvbb.models.player import Player
from bvbb.models.standing import GroupStandings

_schedule_adapter = TypeAdapter(list[ScheduleEntry])


class ChampionshipRow(SQLModel, table=True):
    __tablename__ = "championship"
    code: str = Field(primary_key=True)
    data: str


class StandingsRow(SQLModel, table=True):
    __tablename__ = "standings"
    group_id: int = Field(primary_key=True)
    championship_code: str = Field(primary_key=True, default="")
    data: str


class ScheduleRow(SQLModel, table=True):
    __tablename__ = "schedule"
    group_id: int = Field(primary_key=True)
    championship_code: str = Field(primary_key=True, default="")
    data: str


class MatchReportRow(SQLModel, table=True):
    __tablename__ = "match_report"
    meeting_id: int = Field(primary_key=True)
    championship_code: str = Field(primary_key=True, default="")
    group_id: int
    data: str


class PlayerRow(SQLModel, table=True):
    __tablename__ = "player"
    person_id: int = Field(primary_key=True)
    championship_code: str = Field(primary_key=True, default="")
    data: str


class ClubRow(SQLModel, table=True):
    __tablename__ = "club"
    club_id: int = Field(primary_key=True)
    championship_code: str = Field(primary_key=True, default="")
    data: str


def init_db(db_path: Path) -> Session:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


# --- Save functions ---


def save_championship(session: Session, champ: Championship) -> None:
    session.merge(ChampionshipRow(code=champ.code, data=champ.model_dump_json()))
    session.commit()


def save_standings(session: Session, standings: GroupStandings, championship_code: str) -> None:
    session.merge(
        StandingsRow(group_id=standings.group_id, championship_code=championship_code, data=standings.model_dump_json())
    )
    session.commit()


def save_schedule(session: Session, group_id: int, entries: list[ScheduleEntry], championship_code: str) -> None:
    session.merge(
        ScheduleRow(
            group_id=group_id,
            championship_code=championship_code,
            data=_schedule_adapter.dump_json(entries).decode(),
        )
    )
    session.commit()


def save_match_report(session: Session, group_id: int, report: MatchReport, championship_code: str) -> None:
    session.merge(
        MatchReportRow(
            meeting_id=report.meeting_id,
            championship_code=championship_code,
            group_id=group_id,
            data=report.model_dump_json(),
        )
    )
    session.commit()


def save_player(session: Session, player: Player, championship_code: str) -> None:
    session.merge(
        PlayerRow(person_id=player.person_id, championship_code=championship_code, data=player.model_dump_json())
    )
    session.commit()


def save_club(session: Session, club: Club, championship_code: str) -> None:
    session.merge(ClubRow(club_id=club.club_id, championship_code=championship_code, data=club.model_dump_json()))
    session.commit()


# --- Load functions ---


def load_championship(session: Session, code: str) -> Championship:
    row = session.get(ChampionshipRow, code)
    if row is None:
        raise KeyError(f"Championship {code!r} not found")
    return Championship.model_validate_json(row.data)


def load_standings(session: Session, group_id: int, championship_code: str) -> GroupStandings:
    row = session.get(StandingsRow, (group_id, championship_code))
    if row is None:
        raise KeyError(f"Standings for group {group_id} not found")
    return GroupStandings.model_validate_json(row.data)


def load_schedule(session: Session, group_id: int, championship_code: str) -> list[ScheduleEntry]:
    row = session.get(ScheduleRow, (group_id, championship_code))
    if row is None:
        raise KeyError(f"Schedule for group {group_id} not found")
    return _schedule_adapter.validate_json(row.data)


def load_match_report(session: Session, meeting_id: int, championship_code: str) -> MatchReport:
    row = session.get(MatchReportRow, (meeting_id, championship_code))
    if row is None:
        raise KeyError(f"Match report {meeting_id} not found")
    return MatchReport.model_validate_json(row.data)


def load_player(session: Session, person_id: int, championship_code: str) -> Player:
    row = session.get(PlayerRow, (person_id, championship_code))
    if row is None:
        raise KeyError(f"Player {person_id} not found")
    return Player.model_validate_json(row.data)


def load_club(session: Session, club_id: int, championship_code: str) -> Club:
    row = session.get(ClubRow, (club_id, championship_code))
    if row is None:
        raise KeyError(f"Club {club_id} not found")
    return Club.model_validate_json(row.data)


# --- Search / list functions ---


def list_championships(session: Session) -> list[str]:
    return list(session.exec(select(ChampionshipRow.code)).all())


def search_players(session: Session, query: str, championship_code: str) -> list[tuple[int, str, str | None]]:
    query_lower = query.lower()
    results: list[tuple[int, str, str | None]] = []
    stmt = select(PlayerRow).where(PlayerRow.championship_code == championship_code)
    for row in session.exec(stmt):
        player = Player.model_validate_json(row.data)
        if query_lower in player.name.lower():
            results.append((player.person_id, player.name, player.club))
            if len(results) >= 50:
                break
    return results


def search_clubs(session: Session, query: str, championship_code: str) -> list[tuple[int, str]]:
    query_lower = query.lower()
    results: list[tuple[int, str]] = []
    stmt = select(ClubRow).where(ClubRow.championship_code == championship_code)
    for row in session.exec(stmt):
        club = Club.model_validate_json(row.data)
        if query_lower in club.name.lower():
            results.append((club.club_id, club.name))
            if len(results) >= 50:
                break
    return results
