
import time
import asyncio
import logging
from authlib.integrations.httpx_client import AsyncOAuth2Client

logger = logging.getLogger(__name__)


class ManagedAsyncOAuth2Client(AsyncOAuth2Client):
    """
    AsyncOAuth2Client with proactive token refresh and
    concurrency control.
    """
    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: str | None = None,
        refresh_margin: int = 30,
        **kwargs
    ):
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            scope=scope,
            token_endpoint=token_url,
            **kwargs
        )
        self.token_url = token_url
        self.refresh_margin = refresh_margin
        self._lock = asyncio.Lock()

    def _is_token_valid(self) -> bool:
        token = self.token
        if not token:
            return False
        expires_at = token.get("expires_at")
        if not expires_at:
            return False
        return (time.time() + self.refresh_margin) < expires_at

    async def get_valid_token(self) -> str:
        """
        Return a valid access token, refreshing or reacquiring as needed.
        """
        if self._is_token_valid():
            return self.token["access_token"]

        async with self._lock:
            if self._is_token_valid():
                return self.token["access_token"]

            if self.token and self.token.get("refresh_token"):
                logger.info(
                    "Refreshing access token using refresh token."
                )
                new_token = await self.refresh_token(
                    url=self.token_url,
                    refresh_token=self.token["refresh_token"]
                )
                self.token = new_token
                return self.token["access_token"]

            logger.info(
                "Acquiring new access token using client credentials."
            )
            await self.fetch_token(
                url=self.token_url,
                grant_type="client_credentials"
            )
            return self.token["access_token"]

    async def request(self, method, url, **kwargs):
        await self.get_valid_token()
        return await super().request(method, url, **kwargs)
