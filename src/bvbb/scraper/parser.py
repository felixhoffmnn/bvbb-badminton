import logging
import re
from datetime import date
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def find_table_by_header(soup: BeautifulSoup | Tag, header: str) -> Tag | None:
    """Return the first <table> whose header row contains the given text."""
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            ths = tr.find_all("th")
            if ths and any(header in th.get_text(strip=True) for th in ths):
                return table
    return None


def parse_german_date(text: str) -> date | None:
    """Parse 'DD.MM.YYYY' anywhere in text."""
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def safe_int(text: str) -> int | None:
    try:
        return int(text)
    except ValueError:
        return None


def extract_param(url: str, param: str) -> str | None:
    """Extract a query parameter value from a URL."""
    parsed = urlparse(url)
    values = parse_qs(parsed.query).get(param)
    return values[0] if values else None


def extract_int_param(url: str, param: str) -> int | None:
    """Extract an integer query parameter from a URL."""
    val = extract_param(url, param)
    if val is None:
        return None
    try:
        return int(val)
    except ValueError:
        logger.debug("extract_int_param: non-integer value %r for param %r", val, param)
        return None


def find_links_with_param(soup: BeautifulSoup | Tag, param: str) -> list[tuple[str, str]]:
    """Find all <a> tags whose href contains the given query parameter.
    Returns list of (href, link_text) tuples.
    """
    results = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if param + "=" in href:
            results.append((href, a.get_text(strip=True)))
    return results


def parse_score(text: str) -> tuple[int, int] | None:
    """Parse a 'X:Y' score string into (home, away) integers."""
    stripped = text.strip()
    m = re.match(r"(\d+):(\d+)", stripped)
    if m:
        return int(m.group(1)), int(m.group(2))
    if stripped:
        logger.debug("parse_score: could not parse %r", stripped)
    return None
