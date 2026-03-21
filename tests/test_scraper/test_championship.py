import pytest
import respx
from httpx import Response
from tests.conftest import load_fixture

from bvbb.config import derive_season
from bvbb.scraper.championship import discover_championships, scrape_championship
from bvbb.scraper.client import RateLimitedClient


@pytest.fixture
def html():
    return load_fixture("league_page.html")


@pytest.mark.asyncio
async def test_scrape_championship(html):
    async with respx.mock:
        respx.get("https://bvbb-badminton.liga.nu/cgi-bin/WebObjects/nuLigaBADDE.woa/wa/leaguePage").mock(
            return_value=Response(200, text=html)
        )

        client = RateLimitedClient()
        client._delay = 0  # No delay in tests

        result = await scrape_championship(client, "BBMM 25/26")

        assert result.code == "BBMM 25/26"
        assert result.name == "Mannschaftsmeisterschaft 2025/26"
        assert len(result.categories) == 3

        mannschaft = result.categories[0]
        assert mannschaft.category == "Mannschaft"
        assert len(mannschaft.groups) == 3
        assert mannschaft.groups[0].group_id == 38015
        assert mannschaft.groups[0].name == "Berlin-Brandenburg-Liga"

        jugend = result.categories[1]
        assert jugend.category == "Jugend"
        assert len(jugend.groups) == 1

        schueler = result.categories[2]
        assert schueler.category == "Schüler"
        assert len(schueler.groups) == 1

        await client.close()


@pytest.mark.asyncio
async def test_discover_championships(html):
    async with respx.mock:
        route = respx.get("https://bvbb-badminton.liga.nu/cgi-bin/WebObjects/nuLigaBADDE.woa/wa/leaguePage")
        route.side_effect = lambda request: (
            Response(200, text=html)
            if request.url.params.get("championship") == "BBMM 25/26"
            else Response(200, text="<html><body><h1></h1></body></html>")
        )

        client = RateLimitedClient()
        client._delay = 0

        results = await discover_championships(client)

        assert len(results) == 1
        assert results[0] == ("BBMM 25/26", "Mannschaftsmeisterschaft 2025/26")

        await client.close()


@pytest.mark.asyncio
async def test_discover_championships_http_error():
    async with respx.mock:
        respx.get("https://bvbb-badminton.liga.nu/cgi-bin/WebObjects/nuLigaBADDE.woa/wa/leaguePage").mock(
            return_value=Response(404)
        )

        client = RateLimitedClient()
        client._delay = 0

        results = await discover_championships(client)

        assert results == []

        await client.close()


def test_derive_season():
    assert derive_season("BBMM 25/26") == "2025/26"
    assert derive_season("BBMM 09/10") == "2009/10"
    assert derive_season("BBMM 99/00") == "2099/00"


def test_derive_season_invalid():
    with pytest.raises(ValueError):
        derive_season("INVALID")
    with pytest.raises(ValueError):
        derive_season("BBMM 2526")
