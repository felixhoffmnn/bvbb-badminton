import asyncio
import logging

import httpx

from bvbb.config import settings

logger = logging.getLogger(__name__)


class RateLimitedClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.base_url,
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": "bvbb-dashboard/0.1"},
        )
        self._delay = settings.rate_limit_delay
        self._semaphore = asyncio.Semaphore(settings.max_concurrent)

    async def get(self, path: str, params: dict | None = None) -> str:
        async with self._semaphore:
            await asyncio.sleep(self._delay)
            logger.debug("GET %s params=%s", path, params)
            try:
                resp = await self._client.get(path, params=params)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error("HTTP %s for %s", exc.response.status_code, path)
                raise
            except httpx.RequestError as exc:
                logger.error("request failed for %s: %s", path, exc)
                raise
            logger.debug("response %s (%d bytes)", resp.status_code, len(resp.content))
            return resp.text

    async def close(self) -> None:
        await self._client.aclose()
