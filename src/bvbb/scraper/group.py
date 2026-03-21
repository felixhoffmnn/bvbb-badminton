import logging
import re
from datetime import time

from bvbb.models.match import ScheduleEntry
from bvbb.models.standing import GroupStandings, StandingEntry
from bvbb.scraper.client import RateLimitedClient
from bvbb.scraper.parser import extract_int_param, find_table_by_header, make_soup, parse_german_date, safe_int

logger = logging.getLogger(__name__)


async def scrape_standings(client: RateLimitedClient, championship_code: str, group_id: int) -> GroupStandings:
    """Scrape the group standings table.

    Table columns: Rang, Mannschaft, Begegnungen, S, U, N, Punkte, Spiele, Sätze
    """
    logger.info("scraping standings group=%d championship=%s", group_id, championship_code)
    html = await client.get(
        "/groupPage",
        params={"championship": championship_code, "group": group_id},
    )
    soup = make_soup(html)

    group_name = ""
    h1 = soup.find("h1")
    if h1:
        group_name = h1.get_text(strip=True)

    entries: list[StandingEntry] = []

    table = find_table_by_header(soup, "Rang")
    if table:
        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            # Detect extra empty first column and shift indices
            offset = 1 if cells and not cells[0].get_text(strip=True) else 0
            if len(cells) < 9 + offset:
                continue
            cells = cells[offset:]

            team_cell = cells[1]
            team_link = team_cell.find("a", href=True)
            team_name = team_cell.get_text(strip=True)
            team_url = str(team_link["href"]) if team_link else None

            rank = safe_int(cells[0].get_text(strip=True))
            if rank is None:
                continue

            try:
                matches_played = int(cells[2].get_text(strip=True))
                wins = int(cells[3].get_text(strip=True))
                draws = int(cells[4].get_text(strip=True))
                losses = int(cells[5].get_text(strip=True))
            except ValueError:
                logger.warning("non-numeric stats for team %s in group %d, defaulting to 0", team_name, group_id)
                matches_played = wins = draws = losses = 0

            entries.append(
                StandingEntry(
                    rank=rank,
                    team=team_name,
                    team_url=team_url,
                    matches_played=matches_played,
                    wins=wins,
                    draws=draws,
                    losses=losses,
                    points=cells[6].get_text(strip=True),
                    games=cells[7].get_text(strip=True),
                    sets=cells[8].get_text(strip=True),
                )
            )

    if not entries:
        logger.warning("no standings found for group %d", group_id)
    else:
        logger.info("scraped standings group=%d: %d entries", group_id, len(entries))

    return GroupStandings(group_id=group_id, group_name=group_name, entries=entries)


async def scrape_schedule(client: RateLimitedClient, championship_code: str, group_id: int) -> list[ScheduleEntry]:
    """Scrape the group schedule/meetings table.

    The table has two row types:
    1. Grouping rows with colspan containing date (e.g. "Sa. 20.09.2025")
    2. Match rows with: Zeit, Sporthalle, Nr., Heimmannschaft, Gastmannschaft, Spiele
    """
    logger.info("scraping schedule group=%d championship=%s", group_id, championship_code)
    html = await client.get(
        "/groupPage",
        params={
            "championship": championship_code,
            "group": group_id,
            "displayDetail": "meetings",
        },
    )
    soup = make_soup(html)
    entries: list[ScheduleEntry] = []

    table = find_table_by_header(soup, "Heimmannschaft")
    if not table:
        logger.warning("no schedule entries found for group %d", group_id)
        return entries

    current_date = None

    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if not cells:
            continue

        # Check for grouping row (has colspan or fewer cells with date)
        colspan_cell = cells[0] if cells else None
        if colspan_cell and colspan_cell.get("colspan"):
            current_date = parse_german_date(tr.get_text(strip=True))
            continue

        # Match rows: try both layouts
        # Layout A (8 cols): Tag, Datum, Zeit, Sporthalle, Nr., Heim, Gast, Spiele
        # Layout B (6 cols): Zeit, Sporthalle, Nr., Heim, Gast, Spiele (date from grouping row)
        if len(cells) >= 8:
            # Full row with date
            current_date = parse_german_date(cells[1].get_text(strip=True)) or current_date
            time_cell, venue_cell, nr_cell = cells[2], cells[3], cells[4]
            home_cell, away_cell, score_cell = cells[5], cells[6], cells[7]
        elif len(cells) >= 6:
            time_cell, venue_cell, nr_cell = cells[0], cells[1], cells[2]
            home_cell, away_cell, score_cell = cells[3], cells[4], cells[5]
        else:
            logger.debug("skipping row with %d cells (need 6+)", len(cells))
            continue

        # Parse time
        match_time = None
        time_text = time_cell.get_text(strip=True)
        tm = re.match(r"(\d{2}):(\d{2})", time_text)
        if tm:
            match_time = time(int(tm.group(1)), int(tm.group(2)))

        venue = venue_cell.get_text(strip=True) or None
        home_team = home_cell.get_text(strip=True)
        away_team = away_cell.get_text(strip=True)

        if not home_team and not away_team:
            continue

        # Score and meeting ID
        score_text = score_cell.get_text(strip=True)
        score = score_text if re.match(r"\d+:\d+", score_text) else None
        meeting_id = 0
        report_url = None

        score_link = score_cell.find("a", href=True)
        if score_link:
            mid = extract_int_param(str(score_link["href"]), "meeting")
            if mid is not None:
                meeting_id = mid
            report_url = str(score_link["href"])

        # Fallback: look for meeting link anywhere in the row
        if meeting_id == 0:
            for a in tr.find_all("a", href=True):
                if "meeting=" in str(a["href"]):
                    mid = extract_int_param(str(a["href"]), "meeting")
                    if mid:
                        meeting_id = mid
                        if not report_url:
                            report_url = str(a["href"])
                        break

        entries.append(
            ScheduleEntry(
                meeting_id=meeting_id,
                match_day=safe_int(nr_cell.get_text(strip=True)),
                match_date=current_date,
                match_time=match_time,
                venue=venue,
                home_team=home_team,
                away_team=away_team,
                score=score,
                report_url=report_url,
            )
        )

    if not entries:
        logger.warning("no schedule entries found for group %d", group_id)
    else:
        logger.info("scraped schedule group=%d: %d entries", group_id, len(entries))

    return entries
