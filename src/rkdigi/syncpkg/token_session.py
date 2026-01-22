import logging
import time
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient

logger = logging.getLogger(__name__)


class ManagedOAuth2Session(OAuth2Session):
    """
    A drop-in replacement for requests.Session/OAuth2Session
    that transparently handles OAuth2 token acquisition
    and refresh for both client credentials and refresh token flows.
    """
    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        extra_params: dict = None,
        **kwargs
    ):
        if extra_params and "grant_type" in extra_params:
            raise ValueError(
                "Specifying 'grant_type' in extra_params is not allowed. "
                "Only client credentials grant type is supported."
            )
        client = BackendApplicationClient(client_id=client_id)
        super().__init__(client=client, **kwargs)
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.extra_params = extra_params or {}
        self._initial_token = None
        self._fetching_token = False

    def _get_auto_refresh_kwargs(self):
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            **self.extra_params
        }

    def _acquire_token(self):
        logger.info("Acquiring new access token via OAuth2.")
        try:
            self._fetching_token = True
            try:
                token = super().fetch_token(
                    token_url=self.token_url,
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    include_client_id=True,
                    **self.extra_params
                )
            finally:
                self._fetching_token = False
            self.token = token
            return token
        except ValueError as e:
            raise RuntimeError(
                f"Failed to acquire OAuth2 token.\n"
                f"Original error: {e}"
            ) from e

    def _reacquire_if_expired(self):
        now = time.time()
        expires_at = self.token.get("expires_at", 0) if self.token else 0
        if not self.token or (expires_at and expires_at <= now):
            if not (self.token and self.token.get("refresh_token")):
                # Only reacquire if not already fetching token
                if not self._fetching_token:
                    self._acquire_token()

    def request(self, method, url, **kwargs):
        self._reacquire_if_expired()
        if self.token and self.token.get("refresh_token"):
            self.auto_refresh_url = self.token_url
            self.auto_refresh_kwargs = self._get_auto_refresh_kwargs()
        return super().request(method, url, **kwargs)

    @property
    def access_token(self):
        return self.token["access_token"] if self.token else None

    @property
    def refresh_token_value(self):
        return self.token.get("refresh_token") if self.token else None

    @property
    def access_token_expiry(self):
        return self.token.get("expires_at") if self.token else 0
