import logging
import re

from bvbb.models.match import DisciplineResult, MatchReport, SetScore
from bvbb.scraper.client import RateLimitedClient
from bvbb.scraper.parser import extract_int_param, find_table_by_header, make_soup, parse_german_date

logger = logging.getLogger(__name__)


async def scrape_match_report(
    client: RateLimitedClient, championship_code: str, group_id: int, meeting_id: int
) -> MatchReport:
    """Scrape a match report page with discipline results.

    Header: <h1> with championship, league, "HomeTeam - AwayTeam, DD.MM.YYYY, HH:MM Uhr"
    Table columns: [discipline], [home players], [away players], 1.Satz, 2.Satz, 3.Satz, Spielpunkte, Sätze, Spiele
    Players: <a> tags separated by <br/> for doubles
    """
    logger.info("scraping match report meeting=%d group=%d", meeting_id, group_id)
    html = await client.get(
        "/groupMeetingReport",
        params={"meeting": meeting_id, "championship": championship_code, "group": group_id},
    )
    soup = make_soup(html)

    # Parse header
    home_team = ""
    away_team = ""
    match_date = None

    h1 = soup.find("h1")
    if h1:
        h1_text = h1.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in h1_text.split("\n") if line.strip()]
        matched_header = False
        # Try single-line format first: "HomeTeam - AwayTeam, DD.MM.YYYY, HH:MM Uhr"
        for line in lines:
            m = re.match(r"(.+?)\s*-\s*(.+?)\s*,\s*(\d{2}\.\d{2}\.\d{4})", line)
            if m:
                home_team = m.group(1).strip()
                away_team = m.group(2).strip()
                match_date = parse_german_date(m.group(3))
                matched_header = True
                break
        # Fallback: multi-line format where "-" is on its own line between team names
        if not matched_header:
            for i, line in enumerate(lines):
                if line == "-" and i > 0 and i + 1 < len(lines):
                    home_team = lines[i - 1]
                    away_team = lines[i + 1]
                    # Search remaining lines for a date
                    for rest in lines[i + 2 :]:
                        d = parse_german_date(rest)
                        if d:
                            match_date = d
                            break
                    matched_header = True
                    break
        if not matched_header:
            logger.warning("header regex miss for meeting %d", meeting_id)

    disciplines: list[DisciplineResult] = []
    home_score = 0
    away_score = 0

    # Find the match results table
    table = find_table_by_header(soup, "Satz")
    if table:
        rows = table.find_all("tr")
        for tr in rows:
            cells = tr.find_all("td")
            if len(cells) < 7:
                continue

            discipline_text = cells[0].get_text(strip=True)
            # Skip summary/total rows
            if not discipline_text or discipline_text.lower() in ("summe", "gesamt"):
                # Parse final score from last cell of the summary row
                if len(cells) >= 3:
                    score_text = cells[-1].get_text(strip=True)
                    score_match = re.match(r"(\d+):(\d+)", score_text)
                    if score_match:
                        home_score = int(score_match.group(1))
                        away_score = int(score_match.group(2))
                continue

            # Parse players from cells[1] (home) and cells[2] (away)
            home_players, home_player_ids, home_club_ids = _parse_players(cells[1])
            away_players, away_player_ids, away_club_ids = _parse_players(cells[2])

            # Parse set scores from cells[3], cells[4], cells[5]
            sets: list[SetScore] = []
            for i in range(3, 6):
                if i < len(cells):
                    set_text = cells[i].get_text(strip=True)
                    sm = re.match(r"(\d+):(\d+)", set_text)
                    if sm:
                        sets.append(SetScore(home=int(sm.group(1)), away=int(sm.group(2))))

            # Parse match point from "Spiele" column (last column)
            home_mp = 0
            away_mp = 0
            if len(cells) >= 9:
                mp_text = cells[8].get_text(strip=True)
                mp_match = re.match(r"(\d+):(\d+)", mp_text)
                if mp_match:
                    home_mp = int(mp_match.group(1))
                    away_mp = int(mp_match.group(2))

            disciplines.append(
                DisciplineResult(
                    discipline=discipline_text,
                    home_players=home_players,
                    away_players=away_players,
                    home_player_ids=home_player_ids,
                    away_player_ids=away_player_ids,
                    home_club_ids=home_club_ids,
                    away_club_ids=away_club_ids,
                    sets=sets,
                    home_match_point=home_mp,
                    away_match_point=away_mp,
                )
            )

    if not disciplines:
        logger.warning("no disciplines found for meeting %d", meeting_id)
    else:
        logger.info(
            "scraped match report meeting=%d: %s %d:%d (%d disciplines)",
            meeting_id,
            f"{home_team} vs {away_team}",
            home_score,
            away_score,
            len(disciplines),
        )

    return MatchReport(
        meeting_id=meeting_id,
        home_team=home_team,
        away_team=away_team,
        home_score=home_score,
        away_score=away_score,
        match_date=match_date,
        disciplines=disciplines,
    )


def _parse_players(cell) -> tuple[list[str], list[int], list[int]]:
    """Extract player names, person IDs, and club IDs from a table cell with <a> tags."""
    names: list[str] = []
    person_ids: list[int] = []
    club_ids: list[int] = []
    for a in cell.find_all("a", href=True):
        name = a.get_text(strip=True)
        if name:
            names.append(name)
        person_id = extract_int_param(a["href"], "person")
        if person_id is not None:
            person_ids.append(person_id)
        club_id = extract_int_param(a["href"], "club")
        if club_id is not None:
            club_ids.append(club_id)
    return names, person_ids, club_ids
