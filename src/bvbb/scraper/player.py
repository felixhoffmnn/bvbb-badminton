import logging
import re

from bvbb.models.player import Player, PlayerMatchRecord, PlayerStats
from bvbb.scraper.client import RateLimitedClient
from bvbb.scraper.parser import make_soup

logger = logging.getLogger(__name__)


async def scrape_player(client: RateLimitedClient, person_id: int, club_id: int, season: str) -> Player:
    """Scrape a player portrait page.

    Structure:
        <h3>Verein</h3> + club link
        <h3>Summe Einzel</h3> with "VR X:Y RR X:Y gesamt X:Y"
        Match history tables per discipline category (Einzel, Doppel, Mixed)
        Columns: Datum, [discipline], Gegner, Sätze, Spiele
    """
    logger.info("scraping player person=%d club=%d season=%s", person_id, club_id, season)
    html = await client.get(
        "/playerPortrait",
        params={"federation": "BVBB", "season": season, "person": person_id, "club": club_id},
    )
    soup = make_soup(html)

    # Parse player name from heading
    name = ""
    h1 = soup.find("h1")
    if h1:
        h1_text = h1.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in h1_text.split("\n") if line.strip()]
        # Name is typically the last line
        if lines:
            name = lines[-1]

    # Parse club name
    club_name = None
    for h3 in soup.find_all("h3"):
        if "Verein" in h3.get_text(strip=True):
            club_link = h3.find_next("a", href=True)
            if club_link:
                club_name = club_link.get_text(strip=True)
            break

    # Parse stats (singles, doubles, mixed)
    stats = _parse_stats(soup)

    # Parse match history from all tables
    match_history = _parse_match_history(soup)

    if not name:
        logger.warning("no name found for player person=%d", person_id)

    logger.info("scraped player person=%d: %s (%d match records)", person_id, name or "<unknown>", len(match_history))

    return Player(
        person_id=person_id,
        name=name,
        club=club_name,
        club_id=club_id,
        stats=stats,
        match_history=match_history,
    )


def _parse_stats(soup) -> PlayerStats:
    """Parse win/loss stats from the Summe sections."""
    stats = PlayerStats()

    text = soup.get_text()

    # Look for "Summe Einzel" or "Einzel" stats like "gesamt 8:3"
    singles_match = re.search(r"Summe Einzel.*?gesamt\s+(\d+):(\d+)", text, re.DOTALL)
    if singles_match:
        stats.singles_wins = int(singles_match.group(1))
        stats.singles_losses = int(singles_match.group(2))

    doubles_match = re.search(r"Summe Doppel.*?gesamt\s+(\d+):(\d+)", text, re.DOTALL)
    if doubles_match:
        stats.doubles_wins = int(doubles_match.group(1))
        stats.doubles_losses = int(doubles_match.group(2))

    mixed_match = re.search(r"Summe Mixed.*?gesamt\s+(\d+):(\d+)", text, re.DOTALL)
    if mixed_match:
        stats.mixed_wins = int(mixed_match.group(1))
        stats.mixed_losses = int(mixed_match.group(2))

    return stats


def _parse_match_history(soup) -> list[PlayerMatchRecord]:
    """Parse match history from tables on the player page."""
    records: list[PlayerMatchRecord] = []

    for table in soup.find_all("table"):
        first_row = table.find("tr")
        if not first_row:
            continue
        headers = [th.get_text(strip=True) for th in first_row.find_all("th")]
        if "Datum" not in headers:
            continue

        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 4:
                continue

            date_text = cells[0].get_text(strip=True) or None
            discipline = cells[1].get_text(strip=True)

            # Opponent from cell with player link
            opponent_cell = cells[2]
            opponents = []
            for a in opponent_cell.find_all("a"):
                opp_name = a.get_text(strip=True)
                if opp_name:
                    opponents.append(opp_name)
            if not opponents:
                opp_text = opponent_cell.get_text(strip=True)
                if opp_text:
                    opponents = [opp_text]

            # Sets result
            sets_cell = cells[3]
            sets_text = sets_cell.get_text(separator=" ", strip=True)

            # Determine win/loss from bold set score or first number
            won = False
            strong = sets_cell.find("strong")
            if strong:
                score_text = strong.get_text(strip=True)
                sm = re.match(r"(\d+):(\d+)", score_text)
                if sm:
                    won = int(sm.group(1)) > int(sm.group(2))

            records.append(
                PlayerMatchRecord(
                    date=date_text,
                    discipline=discipline,
                    opponents=opponents,
                    sets=sets_text,
                    won=won,
                )
            )

    return records
