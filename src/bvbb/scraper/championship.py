import asyncio
import logging
from datetime import date, datetime

import httpx

from bvbb.models.championship import CategoryGroups, Championship, Group
from bvbb.scraper.client import RateLimitedClient
from bvbb.scraper.parser import extract_int_param, make_soup

logger = logging.getLogger(__name__)


async def discover_championships(
    client: RateLimitedClient, *, reference_date: date | None = None
) -> list[tuple[str, str]]:
    """Discover available BBMM championships by probing nuLiga.

    Returns ``(code, display_name)`` tuples sorted newest-first.
    """
    ref = reference_date or datetime.now().date()
    # Season starts in autumn: if we're in Aug+ we're in season YY/(YY+1)
    current_start = ref.year if ref.month >= 8 else ref.year - 1

    codes: list[str] = []
    for start_year in range(current_start, current_start - 15, -1):
        end_year = start_year + 1
        code = f"BBMM {start_year % 100:02d}/{end_year % 100:02d}"
        codes.append(code)

    async def _probe(code: str) -> tuple[str, str] | None:
        try:
            html = await client.get("/leaguePage", params={"championship": code})
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                logger.warning("HTTP %d probing championship %s", exc.response.status_code, code)
            return None
        except httpx.RequestError as exc:
            logger.warning("network error probing %s: %s", code, exc)
            return None
        soup = make_soup(html)
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
            if title:
                return (code, title)
        return None

    results = await asyncio.gather(*[_probe(c) for c in codes])
    return [r for r in results if r is not None]


async def scrape_championship(client: RateLimitedClient, championship_code: str) -> Championship:
    """Scrape the league page to get all categories and groups for a championship.

    HTML structure:
        <h1>Mannschaftsmeisterschaft 2025/26</h1>
        <h2>Ligenplan</h2>
        <h2>Mannschaft</h2>
        <ul><li><a href="...groupPage?championship=...&group=ID">Group Name</a></li></ul>
        <h2>Jugend</h2>
        <ul>...</ul>
    """
    logger.info("scraping championship %s", championship_code)
    html = await client.get("/leaguePage", params={"championship": championship_code})
    soup = make_soup(html)

    title = ""
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)

    categories: list[CategoryGroups] = []
    current_category: str | None = None
    current_groups: list[Group] = []

    # Walk through h2 and ul siblings
    content_area = soup.find("div", class_="content-row") or soup.body
    if not content_area:
        logger.warning("no content area found for championship %s", championship_code)
        return Championship(code=championship_code, name=title, categories=[])

    for element in content_area.find_all(["h2", "ul"]):
        if element.name == "h2":
            text = element.get_text(strip=True)
            # Skip the "Ligenplan" heading
            if text == "Ligenplan":
                continue
            # Save previous category
            if current_category and current_groups:
                categories.append(CategoryGroups(category=current_category, groups=current_groups))
            current_category = text
            current_groups = []
        elif element.name == "ul" and current_category:
            for li in element.find_all("li"):
                a = li.find("a", href=True)
                if a and "group=" in str(a["href"]):
                    group_id = extract_int_param(str(a["href"]), "group")
                    if group_id is not None:
                        current_groups.append(Group(group_id=group_id, name=a.get_text(strip=True)))

    # Don't forget the last category
    if current_category and current_groups:
        categories.append(CategoryGroups(category=current_category, groups=current_groups))

    total_groups = sum(len(c.groups) for c in categories)
    if not categories:
        logger.warning("no categories found for championship %s", championship_code)
    else:
        logger.info(
            "scraped championship %s: %d categories, %d groups", championship_code, len(categories), total_groups
        )

    return Championship(code=championship_code, name=title, categories=categories)
