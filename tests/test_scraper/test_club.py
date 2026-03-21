import pytest
import respx
from httpx import Response
from tests.conftest import load_fixture

from bvbb.scraper.client import RateLimitedClient
from bvbb.scraper.club import scrape_club


@pytest.mark.asyncio
async def test_scrape_club():
    info_html = load_fixture("club_info.html")
    teams_html = load_fixture("club_teams.html")

    async with respx.mock:
        respx.get("https://bvbb-badminton.liga.nu/cgi-bin/WebObjects/nuLigaBADDE.woa/wa/clubInfoDisplay").mock(
            return_value=Response(200, text=info_html)
        )
        respx.get("https://bvbb-badminton.liga.nu/cgi-bin/WebObjects/nuLigaBADDE.woa/wa/clubTeams").mock(
            return_value=Response(200, text=teams_html)
        )

        client = RateLimitedClient()
        client._delay = 0

        result = await scrape_club(client, 10951)

        assert result.club_id == 10951
        assert result.name == "SG Empor Brandenburger Tor 1952"
        assert result.website == "https://www.sg-ebt.de/badminton/"
        assert len(result.venues) >= 1

        assert len(result.teams) == 2
        assert result.teams[0].team_name == "Mannschaft"
        assert result.teams[0].league == "Berlin-Brandenburg-Liga"

        await client.close()
