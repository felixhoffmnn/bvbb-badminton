import logging

from bvbb.models.club import Club, ClubTeam
from bvbb.scraper.client import RateLimitedClient
from bvbb.scraper.parser import extract_int_param, find_table_by_header, make_soup

logger = logging.getLogger(__name__)


async def scrape_club(client: RateLimitedClient, club_id: int) -> Club:
    """Scrape club info and teams from clubInfoDisplay and clubTeams pages."""
    logger.info("scraping club %d", club_id)
    # Fetch club info
    info_html = await client.get("/clubInfoDisplay", params={"club": club_id})
    info_soup = make_soup(info_html)

    name = ""
    h1 = info_soup.find("h1")
    if h1:
        h1_lines = [line for line in h1.get_text(separator="\n", strip=True).split("\n") if line.strip()]
        name = h1_lines[-1].strip() if h1_lines else ""

    # Extract website
    website = None
    for a in info_soup.find_all("a", href=True):
        href = str(a["href"])
        if href.startswith("http") and "liga.nu" not in href and "bvbb" not in href.lower():
            website = href
            break

    # Extract venues
    venues: list[str] = []
    for a in info_soup.find_all("a", href=True):
        if "courtInfo" in str(a["href"]) or "location=" in str(a["href"]):
            venues.append(a.get_text(strip=True))

    # Fetch teams
    teams_html = await client.get("/clubTeams", params={"club": club_id})
    teams_soup = make_soup(teams_html)
    teams = _parse_club_teams(teams_soup)

    if not name:
        logger.warning("no name found for club %d", club_id)

    logger.info("scraped club %d: %s (%d teams, %d venues)", club_id, name or "<unknown>", len(teams), len(venues))

    return Club(
        club_id=club_id,
        name=name,
        website=website,
        venues=venues,
        teams=teams,
    )


def _parse_club_teams(soup) -> list[ClubTeam]:
    """Parse club teams table.

    Columns: Mannschaft, Liga, Mannschaftsführer, Tab.-Rang, Punkte
    """
    teams: list[ClubTeam] = []

    table = find_table_by_header(soup, "Mannschaft")
    if not table:
        return teams

    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 2:
            continue

        team_name = cells[0].get_text(strip=True)

        # League from link in second column
        league_cell = cells[1] if len(cells) > 1 else None
        league = None
        teamtable_id = None

        if league_cell:
            league_link = league_cell.find("a", href=True)
            if league_link:
                league = league_link.get_text(strip=True)
                # Extract group ID from the league link
                gid = extract_int_param(str(league_link["href"]), "group")
                if gid:
                    teamtable_id = gid
            else:
                league = league_cell.get_text(strip=True) or None

        teams.append(ClubTeam(team_name=team_name, league=league, teamtable_id=teamtable_id))

    return teams
