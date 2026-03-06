import sys
import types
import pytest
import smtplib
import asyncio
import email as email_module
from rkdigi.email_handling import EmailSender
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


def test_init_with_address_headers():
    with patch('smtplib.SMTP') as mock_smtp:
        instance = mock_smtp.return_value.__enter__.return_value
        instance.ehlo.return_value = None
        sender = EmailSender(
            smtp_server='smtp.example.com',
            smtp_port=25,
            sender_email='from@example.com',
            sender_name='Mr. From',
            sender_password='pw',
            reply_to_email="reply@example.com",
            reply_to_name="Ms. Reply"
        )
        assert sender._smtp_server == 'smtp.example.com'
        assert sender._smtp_port == 25
        assert sender.sender == ('Mr. From', 'from@example.com')
        assert sender.reply_to == ("Ms. Reply", "reply@example.com")


def test_init_fail_connection():
    with patch('smtplib.SMTP', side_effect=Exception('fail')):
        with pytest.raises(ConnectionError):
            EmailSender(smtp_server='smtp.example.com', smtp_port=25)


def test_init_fail_invalid_sender_email():
    with patch('smtplib.SMTP'):
        with pytest.raises(ValueError, match='Invalid sender email address'):
            EmailSender(
                smtp_server='smtp.example.com',
                smtp_port=25,
                sender_email='invalid-email'
            )


def test_init_reply_to_no_name():
    with patch('smtplib.SMTP') as mock_smtp:
        instance = mock_smtp.return_value.__enter__.return_value
        instance.ehlo.return_value = None
        sender = EmailSender(
            smtp_server='smtp.example.com',
            smtp_port=25,
            sender_email='from@example.com',
            sender_name='Mr. From',
            sender_password='pw',
            reply_to_email="reply@example.com",
        )
        assert sender.reply_to == "reply@example.com"


def test_init_fail_invalid_reply_to_email():
    with patch('smtplib.SMTP'):
        with pytest.raises(ValueError, match='Invalid reply-to email address'):
            EmailSender(
                smtp_server='smtp.example.com',
                smtp_port=25,
                reply_to_email='invalid-email'
            )


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


def test_check_address_header_valid():
    with patch('smtplib.SMTP'):
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        assert sender._check_address_header(
            address='example@example.com'
        ) is True
        assert sender._check_address_header(
            address=('Example', 'example@example.com')
        ) is True


def test_check_address_header_invalid():
    with patch('smtplib.SMTP'):
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        assert sender._check_address_header(
            address='example-example.com'
        ) is False
        assert sender._check_address_header(
            address=('Example', 'example-example.com')
        ) is False
        assert sender._check_address_header(
            address=('Example',)
        ) is False
        assert sender._check_address_header(
            None
        ) is False


def test_build_message_valid_address():
    with patch('smtplib.SMTP'):
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        msg, from_addr, to_addrs = sender._build_message(
            sender=('Valid Sender', 'valid1@example.com'),
            reply_to='valid2@example.com',
            recipients=[
                'valid3@example.com',
                ('Valid Recipient', 'valid4@example.com')
            ],
            subject='Test',
            body='Body',
            cc=None,
            attachments=None
        )

        assert 'valid1@example.com' == from_addr
        assert 'valid2@example.com' == msg['Reply-To']
        assert isinstance(to_addrs, list) and \
            all(isinstance(addr, str) for addr in to_addrs)
        assert 'valid3@example.com' in to_addrs
        assert 'valid4@example.com' in to_addrs


def test_build_message_invalid_address():
    with patch('smtplib.SMTP'):
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        with pytest.raises(ValueError, match='Invalid email address'):
            _, _, _ = sender._build_message(
                sender='invalid-email',
                reply_to="",
                recipients=['valid@example.com'],
                subject='Test',
                body='Body',
                cc=None,
                attachments=None
            )
        with pytest.raises(ValueError, match='Invalid email address'):
            _, _, _ = sender._build_message(
                sender='valid@example.com',
                recipients=['invalid-email'],
                reply_to="",
                subject='Test',
                body='Body',
                cc=None,
                attachments=None
            )
        with pytest.raises(ValueError, match='Invalid email address'):
            _, _, _ = sender._build_message(
                sender='valid@example.com',
                reply_to="",
                recipients=['valid@example.com'],
                subject='Test',
                body='Body',
                cc=['invalid-email'],
                attachments=None
            )
        with pytest.raises(ValueError, match='Invalid email address'):
            _, _, _ = sender._build_message(
                sender='valid@example.com',
                reply_to="invalid-email",
                recipients=['valid@example.com'],
                subject='Test',
                body='Body',
                cc=['invalid-email'],
                attachments=None
            )


def test_build_message_only_html_body():
    with patch('smtplib.SMTP'):
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        msg, _, _ = sender._build_message(
            sender='valid@example.com',
            reply_to="",
            recipients=['valid@example.com'],
            subject='Test',
            body='<html><body>HTML Body</body></html>',
            cc=None,
            attachments=None
        )
        assert msg.get_payload()[0].get_content_subtype() == 'alternative'

        alt = msg.get_payload()[0]
        assert alt.get_payload()[0].get_content_subtype() == 'plain'
        assert alt.get_payload()[0].get_payload(decode=True).decode('utf-8') == 'HTML Body'
        assert alt.get_payload()[1].get_content_subtype() == 'html'
        assert alt.get_payload()[1].get_payload(decode=True).decode('utf-8') == \
            '<html><body>HTML Body</body></html>'


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
        parsed = email_module.message_from_string(args[2])
        plain_parts = [
            p for p in parsed.walk()
            if p.get_content_type() == 'text/plain' and p.get_content_disposition() != 'attachment'
        ]
        assert plain_parts
        assert plain_parts[0].get_payload(decode=True).decode('utf-8').strip() == 'Test Body'


def test_send_email_recipients_tuple_of_emails_is_rejected():
    with patch('smtplib.SMTP'):
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        with pytest.raises(ValueError, match='Invalid address tuple'):
            sender.send_email(
                sender='from@example.com',
                recipients=('to1@example.com', 'to2@example.com'),
                subject='Tuple Recipients',
                body='Body'
            )


def test_send_email_starttls_smtpexception_falls_back_to_plaintext():
    with patch('smtplib.SMTP') as mock_smtp:
        instance = mock_smtp.return_value.__enter__.return_value
        instance.starttls.side_effect = smtplib.SMTPException('STARTTLS failed')
        instance.sendmail.return_value = {}
        instance.ehlo.return_value = None

        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        sender.send_email(
            sender='from@example.com',
            recipients=['to@example.com'],
            subject='Test Subject',
            body='Test Body'
        )

        instance.starttls.assert_called_once()
        instance.sendmail.assert_called_once()


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
        parsed = email_module.message_from_string(args[2])
        plain_parts = [
            p for p in parsed.walk()
            if p.get_content_type() == 'text/plain' and p.get_content_disposition() != 'attachment'
        ]
        assert plain_parts
        assert plain_parts[0].get_payload(decode=True).decode('utf-8').strip() == 'Auth Body'


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
            match='A sender must be specified'
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
            match='At least one recipient'
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


def test_send_email_cc_tuple_of_emails_is_rejected():
    with patch('smtplib.SMTP'):
        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        with pytest.raises(ValueError, match='Invalid address tuple'):
            sender.send_email(
                sender='from@example.com',
                recipients=['to@example.com'],
                cc=('cc1@example.com', 'cc2@example.com'),
                subject='Bad CC Tuple',
                body='Body'
            )


# Mock aiosmtplib
class FakeSMTP:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    async def ehlo(self, *args, **kwargs):
        return None

    async def starttls(self, *args, **kwargs):
        return None

    async def login(self, *args, **kwargs):
        return None

    async def send_message(self, message, *, sender=None, recipients=None, **kwargs):
        return {}


fake_aiosmtplib = types.ModuleType("aiosmtplib")
fake_aiosmtplib.SMTP = lambda *args, **kwargs: FakeSMTP()

fake_aiosmtplib_errors = types.SimpleNamespace(
    SMTPException=Exception,
    SMTPNotSupported=Exception,
)
fake_aiosmtplib.errors = fake_aiosmtplib_errors

sys.modules["aiosmtplib"] = fake_aiosmtplib


def test_send_email_async_starttls_not_supported_falls_back_to_plaintext():
    class StartTLSNotSupported(Exception):
        pass

    class FakeSMTPStartTLSFails(FakeSMTP):
        def __init__(self, *, starttls_fails: bool):
            self._starttls_fails = starttls_fails
            self.send_message_called = False

        async def starttls(self, *args, **kwargs):
            if self._starttls_fails:
                raise StartTLSNotSupported("no STARTTLS")
            return None

        async def send_message(self, message, *, sender=None, recipients=None, **kwargs):
            self.send_message_called = True
            return {}

    created: list[FakeSMTPStartTLSFails] = []

    def smtp_factory(*args, **kwargs):
        inst = FakeSMTPStartTLSFails(starttls_fails=True)
        created.append(inst)
        return inst

    with pytest.MonkeyPatch.context() as m:
        m.setattr(EmailSender, '_can_connect', lambda self: True)

        # Patch the pre-injected fake module.
        fake_aiosmtplib.SMTP = smtp_factory
        fake_aiosmtplib.errors.SMTPNotSupported = StartTLSNotSupported
        fake_aiosmtplib.errors.SMTPException = Exception

        sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
        asyncio.run(
            sender.send_email_async(
                sender='from@example.com',
                recipients=['to@example.com'],
                subject='Test Subject',
                body='Test Body',
            )
        )

    assert created, "Expected FakeSMTP instance to be created"
    assert created[0].send_message_called is True


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
            match='A sender must be specified'
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
            match='At least one recipient'
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
