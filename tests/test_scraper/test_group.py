import pytest
import respx
from httpx import Response
from tests.conftest import load_fixture

from bvbb.scraper.client import RateLimitedClient
from bvbb.scraper.group import scrape_schedule, scrape_standings


@pytest.mark.asyncio
async def test_scrape_standings():
    html = load_fixture("standings_page.html")

    async with respx.mock:
        respx.get("https://bvbb-badminton.liga.nu/cgi-bin/WebObjects/nuLigaBADDE.woa/wa/groupPage").mock(
            return_value=Response(200, text=html)
        )

        client = RateLimitedClient()
        client._delay = 0

        result = await scrape_standings(client, "BBMM 25/26", 38016)

        assert result.group_id == 38016
        assert len(result.entries) == 3

        first = result.entries[0]
        assert first.rank == 1
        assert first.team == "VfB Kiefholz II"
        assert first.wins == 12
        assert first.losses == 2
        assert first.points == "24:4"

        second = result.entries[1]
        assert second.rank == 2
        assert second.team == "SG EBT III"

        await client.close()


@pytest.mark.asyncio
async def test_scrape_schedule():
    html = load_fixture("schedule_page.html")

    async with respx.mock:
        respx.get("https://bvbb-badminton.liga.nu/cgi-bin/WebObjects/nuLigaBADDE.woa/wa/groupPage").mock(
            return_value=Response(200, text=html)
        )

        client = RateLimitedClient()
        client._delay = 0

        result = await scrape_schedule(client, "BBMM 25/26", 38016)

        assert len(result) >= 2

        first = result[0]
        assert first.home_team == "Team A"
        assert first.away_team == "Team B"
        assert first.score == "3:5"
        assert first.meeting_id == 364436

        await client.close()
