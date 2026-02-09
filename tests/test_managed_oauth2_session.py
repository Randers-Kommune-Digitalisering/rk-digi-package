import pytest
import time
import types
from requests_oauthlib import OAuth2Session

from rkdigi import ManagedOAuth2Session

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


class DummyRequest:
    url = "http://example.com"
    headers = {}
    body = b""


class DummyResponse:
    status_code = 200
    request = DummyRequest()
    headers = {}
    text = ""


def test_managed_oauth2_session_init(session):
    """Test init"""
    assert session.token_url == DUMMY_TOKEN_URL
    assert session.client_id == DUMMY_CLIENT_ID
    assert session.client_secret == DUMMY_CLIENT_SECRET
    assert isinstance(session.extra_params, dict)
    # Properties
    assert session.token == {}
    assert session.access_token is None
    assert session.refresh_token_value is None
    assert session.access_token_expiry == 0


def test_init_raises_on_grant_type():
    """
    Test that specifying grant_type
    in extra_params raises ValueError
    """
    with pytest.raises(ValueError):
        ManagedOAuth2Session(
            token_url=DUMMY_TOKEN_URL,
            client_id=DUMMY_CLIENT_ID,
            client_secret=DUMMY_CLIENT_SECRET,
            extra_params={"grant_type": "client_credentials"}
        )


def test_reacquire_if_expired_fetching_token(session):
    session.token = {}
    session._fetching_token = True
    called = {}

    def fake_acquire_token():
        called["called"] = True

    session._acquire_token = types.MethodType(fake_acquire_token, session)
    session._reacquire_if_expired()
    # Should not call _acquire_token if _fetching_token is True
    assert not called
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
        return DummyResponse()

    def fake_fetch_token(*a, **kw):
        return {"access_token": "dummy", "expires_at": time.time() + 100}

    monkeypatch.setattr(OAuth2Session, "request", fake_super_request)
    monkeypatch.setattr(OAuth2Session, "fetch_token", fake_fetch_token)
    result = session.request("GET", "http://example.com")
    assert isinstance(result, DummyResponse)
