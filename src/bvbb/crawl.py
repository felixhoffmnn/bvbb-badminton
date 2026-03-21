import argparse
import asyncio
import logging
from pathlib import Path

from tqdm import tqdm

from bvbb.config import derive_season, settings
from bvbb.db import (
    init_db,
    save_championship,
    save_club,
    save_match_report,
    save_player,
    save_schedule,
    save_standings,
)
from bvbb.log_setup import setup_logging
from bvbb.scraper.championship import discover_championships, scrape_championship
from bvbb.scraper.client import RateLimitedClient
from bvbb.scraper.club import scrape_club
from bvbb.scraper.group import scrape_schedule, scrape_standings
from bvbb.scraper.match_report import scrape_match_report
from bvbb.scraper.player import scrape_player

logger = logging.getLogger(__name__)


async def _select_championship() -> str:
    """Interactively discover and select a championship."""
    print("Discovering available championships...")
    client = RateLimitedClient()
    try:
        championships = await discover_championships(client)
    finally:
        await client.close()

    if not championships:
        raise SystemExit("No championships found.")

    print()
    for i, (code, name) in enumerate(championships, 1):
        print(f"  {i}. {name} [{code}]")
    print()

    while True:
        try:
            choice = int(input(f"Select championship (1-{len(championships)}): "))
            if 1 <= choice <= len(championships):
                return championships[choice - 1][0]
        except (ValueError, EOFError):
            pass
        print(f"Please enter a number between 1 and {len(championships)}.")


async def crawl(championship_code: str, db_path: Path) -> None:
    session = init_db(db_path)
    season = derive_season(championship_code)
    client = RateLimitedClient()
    try:
        # 1. Scrape championship
        logger.info("crawling championship %s", championship_code)
        champ = await scrape_championship(client, championship_code)
        save_championship(session, champ)

        # 2. Scrape all groups in parallel (standings + schedule)
        all_groups = [group for cat in champ.categories for group in cat.groups]
        logger.info("found %d groups", len(all_groups))

        async def _scrape_group(group):
            gid = group.group_id
            logger.info("crawling standings for group %d (%s)", gid, group.name)
            standings = await scrape_standings(client, championship_code, gid)
            logger.info("crawling schedule for group %d (%s)", gid, group.name)
            schedule = await scrape_schedule(client, championship_code, gid)
            bar_groups.update(1)
            return gid, standings, schedule

        bar_groups = tqdm(total=len(all_groups), desc="Groups")
        group_results = await asyncio.gather(*[_scrape_group(g) for g in all_groups])
        bar_groups.close()

        all_played: list[tuple[int, int]] = []  # (group_id, meeting_id)
        for gid, standings, schedule in group_results:
            save_standings(session, standings, championship_code)
            save_schedule(session, gid, schedule, championship_code)
            for e in schedule:
                if e.meeting_id != 0 and e.score is not None:
                    all_played.append((gid, e.meeting_id))

        # 3. Scrape all match reports in parallel
        logger.info("crawling %d match reports", len(all_played))

        async def _scrape_match(gid, mid):
            logger.info("crawling match report meeting=%d", mid)
            report = await scrape_match_report(client, championship_code, gid, mid)
            bar_matches.update(1)
            return gid, report

        bar_matches = tqdm(total=len(all_played), desc="Matches")
        match_results = await asyncio.gather(*[_scrape_match(gid, mid) for gid, mid in all_played])
        bar_matches.close()

        unique_players: set[tuple[int, int]] = set()  # (person_id, club_id)
        unique_clubs: set[int] = set()
        for gid, report in match_results:
            save_match_report(session, gid, report, championship_code)
            for disc in report.disciplines:
                for pid, cid in zip(disc.home_player_ids, disc.home_club_ids, strict=True):
                    unique_players.add((pid, cid))
                    unique_clubs.add(cid)
                for pid, cid in zip(disc.away_player_ids, disc.away_club_ids, strict=True):
                    unique_players.add((pid, cid))
                    unique_clubs.add(cid)

        # 4. Scrape unique players in parallel
        logger.info("crawling %d unique players", len(unique_players))

        async def _scrape_player_wrap(pid, cid):
            logger.info("crawling player person=%d club=%d", pid, cid)
            player = await scrape_player(client, pid, cid, season=season)
            bar_players.update(1)
            return player

        bar_players = tqdm(total=len(unique_players), desc="Players")
        players = await asyncio.gather(*[_scrape_player_wrap(pid, cid) for pid, cid in sorted(unique_players)])
        bar_players.close()

        for player in players:
            save_player(session, player, championship_code)

        # 5. Scrape unique clubs in parallel
        logger.info("crawling %d unique clubs", len(unique_clubs))

        async def _scrape_club_wrap(cid):
            logger.info("crawling club %d", cid)
            club = await scrape_club(client, cid)
            bar_clubs.update(1)
            return club

        bar_clubs = tqdm(total=len(unique_clubs), desc="Clubs")
        clubs = await asyncio.gather(*[_scrape_club_wrap(cid) for cid in sorted(unique_clubs)])
        bar_clubs.close()

        for club in clubs:
            save_club(session, club, championship_code)

        logger.info("crawl complete — data written to %s", db_path)
    finally:
        session.close()
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl BVBB championship data")
    parser.add_argument("--championship", help="Championship code, e.g. 'BBMM 25/26' (interactive if omitted)")
    parser.add_argument("--db-path", default=settings.db_path, help="Database path (default: data/bvbb.db)")
    args = parser.parse_args()

    setup_logging()

    championship_code = args.championship
    if not championship_code:
        championship_code = asyncio.run(_select_championship())

    asyncio.run(crawl(championship_code, Path(args.db_path)))


if __name__ == "__main__":
    main()
