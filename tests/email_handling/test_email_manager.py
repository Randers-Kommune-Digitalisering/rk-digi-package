import pytest
from unittest.mock import patch, AsyncMock
from rkdigi.email_handling import EmailManager


@pytest.fixture
def email_manager():
    eh = "rkdigi.email_handling"
    with patch(f"{eh}.EmailSender._can_connect", return_value=True), \
         patch(f"{eh}.EmailReader._can_connect", return_value=True):
        yield EmailManager(
            email="test@example.com",
            password="password",
            name="Test User",
            smtp_server="smtp.example.com",
            smtp_port=25,
            imap_server="imap.example.com",
            imap_port=143,
            auth_for_sending=False
        )


def test_get_mailboxes_calls_reader(email_manager):
    with patch.object(
            email_manager.email_reader,
            "list_mailboxes",
            return_value=["INBOX", "Sent"]) as mock:
        result = email_manager.get_mailboxes()
        assert result == ["INBOX", "Sent"]
        mock.assert_called_once()


def test_get_emails_calls_reader(email_manager):
    with patch.object(
            email_manager.email_reader,
            "get_emails",
            return_value=([], [])) as mock:
        result = email_manager.get_emails(max=1)
        assert result == ([], [])
        mock.assert_called_once()


def test_send_email_calls_sender(email_manager):
    with patch.object(
            email_manager.email_sender,
            "send_email",
            return_value=None) as mock:
        email_manager.send_email(recipients="test@example.com", subject="Test")
        mock.assert_called_once()


@pytest.mark.asyncio
async def test_get_mailboxes_async_calls_reader(email_manager):
    with patch.object(
            email_manager.email_reader,
            "list_mailboxes_async",
            new_callable=AsyncMock) as mock:
        mock.return_value = ["INBOX", "Sent"]
        result = await email_manager.get_mailboxes_async()
        assert result == ["INBOX", "Sent"]
        mock.assert_called_once()


@pytest.mark.asyncio
async def test_get_emails_async_calls_reader(email_manager):
    with patch.object(
            email_manager.email_reader,
            "get_emails_async",
            new_callable=AsyncMock) as mock:
        mock.return_value = ([], [])
        result = await email_manager.get_emails_async(max=1)
        assert result == ([], [])
        mock.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_async_calls_sender(email_manager):
    with patch.object(
            email_manager.email_sender,
            "send_email_async",
            new_callable=AsyncMock) as mock:
        mock.return_value = None
        await email_manager.send_email_async(
            recipients="test@example.com",
            subject="Test")
        mock.assert_called_once()
