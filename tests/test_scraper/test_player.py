import pytest
import respx
from httpx import Response

from bvbb.scraper.client import RateLimitedClient
from bvbb.scraper.player import scrape_player
from conftest import load_fixture


@pytest.mark.asyncio
async def test_scrape_player():
    html = load_fixture("player_page.html")

    async with respx.mock:
        respx.get("https://bvbb-badminton.liga.nu/cgi-bin/WebObjects/nuLigaBADDE.woa/wa/playerPortrait").mock(
            return_value=Response(200, text=html)
        )

        client = RateLimitedClient()
        client._delay = 0

        result = await scrape_player(client, 1131771, 10951, season="2025/26")

        assert result.person_id == 1131771
        assert result.name == "Liubyvyi, Mykhailo"
        assert result.club == "SG Empor Brandenburger Tor 1952"
        assert result.stats.singles_wins == 8
        assert result.stats.singles_losses == 3
        assert result.stats.doubles_wins == 4
        assert result.stats.doubles_losses == 7

        assert len(result.match_history) == 2
        first_match = result.match_history[0]
        assert first_match.date == "18.10.2025"
        assert first_match.discipline == "1.HE"
        assert not first_match.won  # 1:2

        second_match = result.match_history[1]
        assert second_match.won  # 2:1

        await client.close()
