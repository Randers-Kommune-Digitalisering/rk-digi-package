import pytest
from rkdigi.syncpkg.token_session import ManagedOAuth2Session
from requests_oauthlib import OAuth2Session
import time

DUMMY_TOKEN_URL = "https://example.com/token"
DUMMY_CLIENT_ID = "dummy-client-id"
DUMMY_CLIENT_SECRET = "dummy-secret"


@pytest.fixture
def session():
    return ManagedOAuth2Session(
        token_url=DUMMY_TOKEN_URL,
        client_id=DUMMY_CLIENT_ID,
        client_secret=DUMMY_CLIENT_SECRET
    )


class dummy_request:
    url = "http://example.com"
    headers = {}
    body = b""


class dummy_response:
    status_code = 200
    request = dummy_request()
    headers = {}
    text = ""


def test_managed_oauth2_session_init(session):
    assert session.token_url == DUMMY_TOKEN_URL
    assert session.client_id == DUMMY_CLIENT_ID
    assert session.client_secret == DUMMY_CLIENT_SECRET
    assert isinstance(session.extra_params, dict)


def test_init_raises_on_grant_type():
    with pytest.raises(ValueError):
        ManagedOAuth2Session(
            token_url=DUMMY_TOKEN_URL,
            client_id=DUMMY_CLIENT_ID,
            client_secret=DUMMY_CLIENT_SECRET,
            extra_params={"grant_type": "client_credentials"}
        )


def test_get_auto_refresh_kwargs(session):
    session.extra_params = {"foo": "bar"}
    result = session._get_auto_refresh_kwargs()
    assert result["client_id"] == DUMMY_CLIENT_ID
    assert result["client_secret"] == DUMMY_CLIENT_SECRET
    assert result["foo"] == "bar"


def test_access_token_property(session):
    session.token = {"access_token": "abc", "expires_at": 9999999999}
    assert session.access_token == "abc"


def test_refresh_token_value_property(session):
    session.token = {"refresh_token": "refresh", "expires_at": 9999999999}
    assert session.refresh_token_value == "refresh"


def test_access_token_expiry_property(session):
    session.token = {"expires_at": 12345}
    assert session.access_token_expiry == 12345


def test_access_token_property_empty(session):
    session.token = {}
    assert session.access_token is None


def test_refresh_token_value_property_empty(session):
    session.token = {}
    assert session.refresh_token_value is None


def test_access_token_expiry_property_empty(session):
    session.token = {}
    assert session.access_token_expiry == 0


def test_acquire_token_error(monkeypatch):
    def fake_fetch_token(*a, **kw):
        raise ValueError("fail")
    monkeypatch.setattr(OAuth2Session, "fetch_token", fake_fetch_token)
    session = ManagedOAuth2Session(
        DUMMY_TOKEN_URL,
        DUMMY_CLIENT_ID,
        DUMMY_CLIENT_SECRET
    )
    with pytest.raises(RuntimeError):
        session._acquire_token()


def test_reacquire_if_expired_triggers(session, monkeypatch):
    session.token = {"expires_at": time.time() - 10}  # expired

    def set_token():
        session.token = {"expires_at": time.time() + 100}

    monkeypatch.setattr(session, "_acquire_token", set_token)
    session._reacquire_if_expired()
    assert session.token["expires_at"] > time.time()


def test_reacquire_if_expired_not_expired(session):
    session.token = {"expires_at": time.time() + 100}
    session._reacquire_if_expired()
    assert session.token["expires_at"] > time.time()


def test_reacquire_if_expired_fetching_token(session):
    session.token = {}  # Use empty dict instead of None
    session._fetching_token = True
    session._reacquire_if_expired()
    session._fetching_token = False  # reset for other tests


def test_reacquire_if_expired_with_refresh_token(session, monkeypatch):
    session.token = {"refresh_token": "refresh",
                     "expires_at": time.time() - 10}
    called = {}

    def fake_acquire_token():
        called["called"] = True

    monkeypatch.setattr(session, "_acquire_token", fake_acquire_token)
    session._reacquire_if_expired()
    # Should not call _acquire_token if refresh_token is present
    assert not called


def test_reacquire_if_expired_token_not_expired(session, monkeypatch):
    session.token = {"expires_at": time.time() + 100}
    called = {}

    def fake_acquire_token():
        called["called"] = True

    monkeypatch.setattr(session, "_acquire_token", fake_acquire_token)
    session._reacquire_if_expired()
    # Should not call _acquire_token if token is not expired
    assert not called


def test_request_sets_auto_refresh(session, monkeypatch):
    session.token = {"refresh_token": "refresh",
                     "expires_at": time.time() + 100}
    called = {}

    def fake_super_request(self, method, url, **kwargs):
        called["called"] = True
        return "ok"

    monkeypatch.setattr(OAuth2Session, "request", fake_super_request)
    result = session.request("GET", "http://example.com")
    assert result == "ok"
    assert session.auto_refresh_url == DUMMY_TOKEN_URL


def test_request_no_refresh_token(session, monkeypatch):
    session.token = {}  # No refresh_token
    called = {}

    def fake_super_request(self, method, url, **kwargs):
        called["called"] = True
        return dummy_response()

    def fake_fetch_token(*a, **kw):
        return {"access_token": "dummy", "expires_at": time.time() + 100}

    monkeypatch.setattr(OAuth2Session, "request", fake_super_request)
    monkeypatch.setattr(OAuth2Session, "fetch_token", fake_fetch_token)
    result = session.request("GET", "http://example.com")
    assert isinstance(result, dummy_response)
