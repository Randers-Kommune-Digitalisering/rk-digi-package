import sys
import types
import pytest
from rkdigi.email_sender import EmailSender
from unittest.mock import patch


def test_init_with_server_and_port():
    with patch('smtplib.SMTP') as mock_smtp:
        instance = mock_smtp.return_value.__enter__.return_value
        instance.ehlo.return_value = None
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        assert sender._smtp_server == 'smtp.example.com'
        assert sender._smtp_port == 25


def test_init_with_env(monkeypatch):
    monkeypatch.setenv('SMTP_SERVER', 'env.smtp.com')
    monkeypatch.setenv('SMTP_PORT', '2525')
    with patch('smtplib.SMTP') as mock_smtp:
        instance = mock_smtp.return_value.__enter__.return_value
        instance.ehlo.return_value = None
        sender = EmailSender()
        assert sender._smtp_server == 'env.smtp.com'
        assert sender._smtp_port == 2525


def test_init_fail():
    with patch('smtplib.SMTP', side_effect=Exception('fail')):
        with pytest.raises(ConnectionError):
            EmailSender(smtp_server='smtp.example.com', smtp_port=25)


def test_can_connect_true():
    with patch('smtplib.SMTP') as mock_smtp:
        instance = mock_smtp.return_value.__enter__.return_value
        instance.ehlo.return_value = None
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        assert sender._can_connect() is True


def test_can_connect_false():
    with patch('smtplib.SMTP', side_effect=Exception('fail')):
        sender = object.__new__(EmailSender)
        sender._smtp_server = 'smtp.example.com'
        sender._smtp_port = 25
        assert sender._can_connect() is False


def test_send_email_basic():
    with patch('smtplib.SMTP') as mock_smtp:
        instance = mock_smtp.return_value.__enter__.return_value
        instance.starttls.return_value = None
        instance.sendmail.return_value = {}
        instance.ehlo.return_value = None
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        sender.send_email(
            sender='from@example.com',
            recipients=['to1@example.com', 'to2@example.com'],
            subject='Test Subject',
            body='Test Body'
        )
        instance.starttls.assert_called_once()
        instance.sendmail.assert_called_once()

        args = tuple(instance.sendmail.call_args.kwargs.values())
        assert 'from@example.com' in args[0]
        assert 'to1@example.com' in args[1]
        assert 'to2@example.com' in args[1]
        assert 'Test Subject' in args[2]
        assert 'Test Body' in args[2]


def test_send_email_authenticated():
    with patch('smtplib.SMTP') as mock_smtp:
        instance = mock_smtp.return_value.__enter__.return_value
        instance.starttls.return_value = None
        instance.ehlo.return_value = None
        instance.login.return_value = None
        instance.sendmail.return_value = {}
        sender = EmailSender(
            smtp_server='smtp.example.com',
            smtp_port=25,
            sender_email='auth@example.com',
            sender_password='pw')
        sender.send_email(
            recipients='to@example.com',
            subject='Auth Subject',
            body='Auth Body'
        )
        instance.starttls.assert_called_once()
        instance.login.assert_called_once_with(
            user='auth@example.com',
            password='pw'
        )
        instance.sendmail.assert_called_once()
        args = tuple(instance.sendmail.call_args.kwargs.values())
        assert 'auth@example.com' in args[0]
        assert 'to@example.com' in args[1]
        assert 'Auth Subject' in args[2]
        assert 'Auth Body' in args[2]


def test_send_email_fail_with_double_sender():
    with patch('smtplib.SMTP') as mock_smtp:
        instance = mock_smtp.return_value.__enter__.return_value
        instance.starttls.return_value = None
        instance.ehlo.return_value = None
        instance.login.return_value = None
        sender = EmailSender(
            smtp_server='smtp.example.com',
            smtp_port=25,
            sender_email='auth@example.com',
            sender_password='pw'
        )
        with pytest.raises(
            ValueError,
            match=(
                'Cannot specify sender when using authenticated email sending.'
            )
        ):
            sender.send_email(
                sender='other@example.com',
                recipients='to@example.com',
                subject='Test',
                body='Body'
            )


def test_send_email_no_sender_and_recipients():
    with patch('smtplib.SMTP') as mock_smtp:
        instance = mock_smtp.return_value.__enter__.return_value
        instance.starttls.return_value = None
        instance.ehlo.return_value = None

        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)

        # Test missing sender
        with pytest.raises(
            ValueError,
            match='A sender and at least one recipient'
        ):
            sender.send_email(
                sender='',
                recipients='to@example.com',
                subject='No Sender',
                body='Body'
            )

        # Test missing recipients
        with pytest.raises(
            ValueError,
            match='A sender and at least one recipient'
        ):
            sender.send_email(
                sender='from@example.com',
                recipients=[],
                subject='No Recipients',
                body='Body'
            )


def test_send_email_with_path_attachment(tmp_path):
    file_path = tmp_path / "test.txt"
    file_path.write_text("file content")
    with patch('smtplib.SMTP') as mock_smtp:
        instance = mock_smtp.return_value.__enter__.return_value
        instance.starttls.return_value = None
        instance.ehlo.return_value = None
        instance.sendmail.return_value = {}
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        sender.send_email(
            sender='from@example.com',
            recipients='to@example.com',
            subject='File Attachment',
            body='Body',
            attachments=[str(file_path)]
        )
        instance.sendmail.assert_called_once()
        args = tuple(instance.sendmail.call_args.kwargs.values())
        assert 'File Attachment' in args[2]
        assert 'test.txt' in args[2]


def test_send_email_with_bytes_attachment():
    with patch('smtplib.SMTP') as mock_smtp:
        instance = mock_smtp.return_value.__enter__.return_value
        instance.starttls.return_value = None
        instance.ehlo.return_value = None
        instance.sendmail.return_value = {}
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        sender.send_email(
            sender='from@example.com',
            recipients='to@example.com',
            subject='Bytes Attachment',
            body='Body',
            attachments=[('bytes.txt', b'bytes content')]
        )
        instance.sendmail.assert_called_once()
        args = tuple(instance.sendmail.call_args.kwargs.values())
        assert 'Bytes Attachment' in args[2]
        assert 'bytes.txt' in args[2]


def test_send_email_invalid_attachment_type():
    with patch('smtplib.SMTP') as mock_smtp:
        instance = mock_smtp.return_value.__enter__.return_value
        instance.starttls.return_value = None
        instance.ehlo.return_value = None
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        # Invalid tuple: wrong length
        with pytest.raises(ValueError, match='Attachments must be file paths'):
            sender.send_email(
                sender='from@example.com',
                recipients='to@example.com',
                subject='Invalid Attachment',
                body='Body',
                attachments=[('filename',)]
            )
        # Invalid tuple: wrong types
        with pytest.raises(ValueError, match='Attachments must be file paths'):
            sender.send_email(
                sender='from@example.com',
                recipients='to@example.com',
                subject='Invalid Attachment',
                body='Body',
                attachments=[(123, 456)]
            )


def test_send_email_to_and_cc_headers():
    with patch('smtplib.SMTP') as mock_smtp:
        instance = mock_smtp.return_value.__enter__.return_value
        instance.starttls.return_value = None
        instance.sendmail.return_value = {}
        instance.ehlo.return_value = None
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        sender.send_email(
            sender='from@example.com',
            recipients=['to1@example.com', 'to2@example.com'],
            cc=['cc1@example.com', 'cc2@example.com'],
            subject='Test',
            body='Body'
        )
        args = tuple(instance.sendmail.call_args.kwargs.values())
        msg_str = args[2]
        assert "To: to1@example.com, to2@example.com" in msg_str
        assert "Cc: cc1@example.com, cc2@example.com" in msg_str


def test_send_email_only_cc():
    with patch('smtplib.SMTP') as mock_smtp:
        instance = mock_smtp.return_value.__enter__.return_value
        instance.starttls.return_value = None
        instance.sendmail.return_value = {}
        instance.ehlo.return_value = None
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        sender.send_email(
            sender='from@example.com',
            recipients=[],
            cc=['cc1@example.com', 'cc2@example.com'],
            subject='CC Only',
            body='Body'
        )
        args = tuple(instance.sendmail.call_args.kwargs.values())
        msg_str = args[2]
        assert "To:" not in msg_str
        assert "Cc: cc1@example.com, cc2@example.com" in msg_str


# Mock aiosmtplib
class FakeSMTP:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    async def send_message(self, *args, **kwargs):
        return {}


fake_aiosmtplib = types.ModuleType("aiosmtplib")
fake_aiosmtplib.SMTP = lambda *args, **kwargs: FakeSMTP()

sys.modules["aiosmtplib"] = fake_aiosmtplib


# Async tests for EmailSender.send_email_async
@pytest.mark.asyncio
async def test_send_email_async_basic():
    with pytest.MonkeyPatch.context() as m:
        m.setattr(EmailSender, '_can_connect', lambda self: True)
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        await sender.send_email_async(
            sender='from@example.com',
            recipients=['to1@example.com', 'to2@example.com'],
            subject='Test Subject',
            body='Test Body'
        )


@pytest.mark.asyncio
async def test_send_email_async_authenticated():
    with pytest.MonkeyPatch.context() as m:
        m.setattr(EmailSender, '_can_connect', lambda self: True)
        sender = EmailSender(
            smtp_server='smtp.example.com',
            smtp_port=25,
            sender_email='auth@example.com',
            sender_password='pw')
        await sender.send_email_async(
            recipients='to@example.com',
            subject='Auth Subject',
            body='Auth Body'
        )


@pytest.mark.asyncio
async def test_send_email_async_fail_with_double_sender():
    with pytest.MonkeyPatch.context() as m:
        m.setattr(EmailSender, '_can_connect', lambda self: True)
        sender = EmailSender(
            smtp_server='smtp.example.com',
            smtp_port=25,
            sender_email='auth@example.com',
            sender_password='pw'
        )
        with pytest.raises(
                ValueError,
                match='Cannot specify sender when using'
        ):
            await sender.send_email_async(
                sender='other@example.com',
                recipients='to@example.com',
                subject='Test',
                body='Body'
            )


@pytest.mark.asyncio
async def test_send_email_async_no_sender_and_recipients():
    with pytest.MonkeyPatch.context() as m:
        m.setattr(EmailSender, '_can_connect', lambda self: True)
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        # Test missing sender
        with pytest.raises(
            ValueError,
            match='A sender and at least one recipient'
        ):
            await sender.send_email_async(
                sender='',
                recipients='to@example.com',
                subject='No Sender',
                body='Body'
            )
        # Test missing recipients
        with pytest.raises(
            ValueError,
            match='A sender and at least one recipient'
        ):
            await sender.send_email_async(
                sender='from@example.com',
                recipients=[],
                subject='No Recipients',
                body='Body'
            )


@pytest.mark.asyncio
async def test_send_email_async_with_path_attachment(tmp_path):
    with pytest.MonkeyPatch.context() as m:
        m.setattr(EmailSender, '_can_connect', lambda self: True)
        file_path = tmp_path / "test.txt"
        file_path.write_text("file content")
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        await sender.send_email_async(
            sender='from@example.com',
            recipients='to@example.com',
            subject='File Attachment',
            body='Body',
            attachments=[str(file_path)]
        )


@pytest.mark.asyncio
async def test_send_email_async_with_bytes_attachment():
    with pytest.MonkeyPatch.context() as m:
        m.setattr(EmailSender, '_can_connect', lambda self: True)
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        await sender.send_email_async(
            sender='from@example.com',
            recipients='to@example.com',
            subject='Bytes Attachment',
            body='Body',
            attachments=[('bytes.txt', b'bytes content')]
        )


@pytest.mark.asyncio
async def test_send_email_async_invalid_attachment_type():
    with pytest.MonkeyPatch.context() as m:
        m.setattr(EmailSender, '_can_connect', lambda self: True)
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        # Invalid tuple: wrong length
        with pytest.raises(ValueError, match='Attachments must be file paths'):
            await sender.send_email_async(
                sender='from@example.com',
                recipients='to@example.com',
                subject='Invalid Attachment',
                body='Body',
                attachments=[('filename',)]
            )
        # Invalid tuple: wrong types
        with pytest.raises(ValueError, match='Attachments must be file paths'):
            await sender.send_email_async(
                sender='from@example.com',
                recipients='to@example.com',
                subject='Invalid Attachment',
                body='Body',
                attachments=[(123, 456)]
            )


@pytest.mark.asyncio
async def test_send_email_async_to_and_cc_headers():
    with pytest.MonkeyPatch.context() as m:
        m.setattr(EmailSender, '_can_connect', lambda self: True)
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        await sender.send_email_async(
            sender='from@example.com',
            recipients=['to1@example.com', 'to2@example.com'],
            cc=['cc1@example.com', 'cc2@example.com'],
            subject='Test',
            body='Body'
        )


@pytest.mark.asyncio
async def test_send_email_async_only_cc():
    with pytest.MonkeyPatch.context() as m:
        m.setattr(EmailSender, '_can_connect', lambda self: True)
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        await sender.send_email_async(
            sender='from@example.com',
            recipients=[],
            cc=['cc1@example.com', 'cc2@example.com'],
            subject='CC Only',
            body='Body'
        )
