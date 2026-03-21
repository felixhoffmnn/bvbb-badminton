import pytest
import respx
from httpx import Response
from tests.conftest import load_fixture

from bvbb.scraper.client import RateLimitedClient
from bvbb.scraper.match_report import scrape_match_report


@pytest.mark.asyncio
async def test_scrape_match_report():
    html = load_fixture("match_report.html")

    async with respx.mock:
        respx.get("https://bvbb-badminton.liga.nu/cgi-bin/WebObjects/nuLigaBADDE.woa/wa/groupMeetingReport").mock(
            return_value=Response(200, text=html)
        )

        client = RateLimitedClient()
        client._delay = 0

        result = await scrape_match_report(client, "BBMM 25/26", 38016, 364474)

        assert result.meeting_id == 364474
        assert result.home_team == "SG EBT III"
        assert result.away_team == "BC Schöneiche"
        assert result.home_score == 3
        assert result.away_score == 0

        assert len(result.disciplines) == 3

        hd1 = result.disciplines[0]
        assert hd1.discipline == "1.HD"
        assert hd1.home_players == ["Müller, Hans", "Schmidt, Peter"]
        assert hd1.away_players == ["Weber, Karl", "Fischer, Tom"]
        assert hd1.home_club_ids == [100, 100]
        assert hd1.away_club_ids == [200, 200]
        assert len(hd1.sets) == 2
        assert hd1.sets[0].home == 21
        assert hd1.sets[0].away == 15

        dd = result.disciplines[1]
        assert dd.discipline == "DD"
        assert dd.home_club_ids == [100, 100]
        assert dd.away_club_ids == [200, 200]
        assert len(dd.sets) == 3  # 3 sets played

        he1 = result.disciplines[2]
        assert he1.discipline == "1.HE"
        assert len(he1.home_players) == 1  # singles
        assert he1.home_club_ids == [100]
        assert he1.away_club_ids == [200]

        await client.close()
