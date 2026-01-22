import pytest
import time
from rkdigi.asyncpkg.async_token_client import ManagedAsyncOAuth2Client


DUMMY_TOKEN_URL = "https://example.com/token"
DUMMY_CLIENT_ID = "dummy-client-id"
DUMMY_CLIENT_SECRET = "dummy-secret"


@pytest.fixture
def client():
    return ManagedAsyncOAuth2Client(
        DUMMY_TOKEN_URL,
        DUMMY_CLIENT_ID,
        DUMMY_CLIENT_SECRET
    )


@pytest.mark.asyncio
async def test_get_valid_token_refresh_branch(client, monkeypatch):
    client.token = {"access_token": "abc",
                    "expires_at": time.time() - 100,
                    "refresh_token": "refresh"}

    async def fake_refresh_token(url, refresh_token):
        return {"access_token": "newtoken", "expires_at": time.time() + 1000}
    monkeypatch.setattr(client, "refresh_token", fake_refresh_token)
    result = await client.get_valid_token()
    assert result == "newtoken"


@pytest.mark.asyncio
async def test_get_valid_token_valid_after_lock(client, monkeypatch):
    client.token = {"access_token": "abc", "expires_at": time.time() - 100}
    # Patch _is_token_valid to return False first, then True after lock
    call_count = {"count": 0}

    def fake_is_token_valid():
        call_count["count"] += 1
        if call_count["count"] == 1:
            return False
        client.token = {"access_token": "fresh",
                        "expires_at": time.time() + 1000}
        return True

    monkeypatch.setattr(client, "_is_token_valid", fake_is_token_valid)
    result = await client.get_valid_token()
    assert result == "fresh"


@pytest.mark.asyncio
async def test_expired_token_refresh_key_none(client, monkeypatch):
    client.token = {"access_token": "abc",
                    "expires_at": time.time() - 100,
                    "refresh_token": None}
    called = {}

    async def fake_fetch_token(url, grant_type):
        called["fetch"] = True
        client.token = {"access_token": "fetched5",
                        "expires_at": time.time() + 1000}

    monkeypatch.setattr(client, "fetch_token", fake_fetch_token)
    result = await client.get_valid_token()
    assert called["fetch"]
    assert result == "fetched5"


@pytest.mark.asyncio
async def test_expired_token_no_refresh_key(client, monkeypatch):
    client.token = {"access_token": "abc", "expires_at": time.time() - 100}
    called = {}

    async def fake_fetch_token(url, grant_type):
        called["fetch"] = True
        client.token = {"access_token": "fetched4",
                        "expires_at": time.time() + 1000}

    monkeypatch.setattr(client, "fetch_token", fake_fetch_token)
    result = await client.get_valid_token()
    assert called["fetch"]
    assert result == "fetched4"


@pytest.mark.asyncio
async def test_get_valid_token_no_token_no_refresh(client, monkeypatch):
    client.token = {}

    called = {}

    async def fake_fetch_token(url, grant_type):
        called["fetch"] = True
        client.token = {"access_token": "fetched2",
                        "expires_at": time.time() + 1000}

    monkeypatch.setattr(client, "fetch_token", fake_fetch_token)
    result = await client.get_valid_token()
    assert called["fetch"]
    assert result == "fetched2"


@pytest.mark.asyncio
async def test_request_with_token_calls_super(client, monkeypatch):
    client.token = {"access_token": "tok", "expires_at": time.time() + 1000}
    called = {}

    async def fake_super_request(self, method, url, **kwargs):
        called["super"] = (method, url, kwargs)
        return "response"

    base_class = ManagedAsyncOAuth2Client.__bases__[0]
    monkeypatch.setattr(base_class, "request", fake_super_request)
    result = await client.request("POST", "http://example.com", test=2)
    assert called["super"] == ("POST", "http://example.com", {"test": 2})
    assert result == "response"


def test_managed_async_oauth2_client_init():
    client = ManagedAsyncOAuth2Client(
        token_url=DUMMY_TOKEN_URL,
        client_id=DUMMY_CLIENT_ID,
        client_secret=DUMMY_CLIENT_SECRET
    )
    assert client.token_url == DUMMY_TOKEN_URL
    assert client.client_id == DUMMY_CLIENT_ID
    assert client.client_secret == DUMMY_CLIENT_SECRET
    assert hasattr(client, 'refresh_margin')
    assert hasattr(client, '_lock')


@pytest.mark.asyncio
async def test_is_token_valid_cases(client):
    # No token
    client.token = None
    assert not client._is_token_valid()
    # No expires_at
    client.token = {"access_token": "abc"}
    assert not client._is_token_valid()
    # Expired
    client.token = {"access_token": "abc", "expires_at": 1}
    assert not client._is_token_valid()
    # Valid
    client.token = {"access_token": "abc", "expires_at": time.time() + 1000}
    assert client._is_token_valid()


@pytest.mark.asyncio
async def test_get_valid_token_already_valid(client, monkeypatch):
    client.token = {"access_token": "abc", "expires_at": time.time() + 1000}
    result = await client.get_valid_token()
    assert result == "abc"


@pytest.mark.asyncio
async def test_get_valid_token_no_token(client, monkeypatch):
    client.token = None
    called = {}

    async def fake_fetch_token(url, grant_type):
        called["fetch"] = True
        client.token = {"access_token": "fetched",
                        "expires_at": time.time() + 1000}

    monkeypatch.setattr(client, "fetch_token", fake_fetch_token)
    result = await client.get_valid_token()
    assert called["fetch"]
    assert result == "fetched"


@pytest.mark.asyncio
async def test_request_fetch_token_and_super(client, monkeypatch):
    client.token = None
    called = {}

    async def fake_fetch_token(url, grant_type):
        called["fetch"] = True
        client.token = {"access_token": "tok",
                        "expires_at": time.time() + 1000}

    async def fake_super_request(self, method, url, **kwargs):
        called["super"] = (method, url, kwargs)
        return "response"

    monkeypatch.setattr(client, "fetch_token", fake_fetch_token)
    base_class = ManagedAsyncOAuth2Client.__bases__[0]
    monkeypatch.setattr(base_class, "request", fake_super_request)
    result = await client.request("GET", "http://example.com", test=1)
    assert called["fetch"]
    assert called["super"] == ("GET", "http://example.com", {"test": 1})
    assert result == "response"
