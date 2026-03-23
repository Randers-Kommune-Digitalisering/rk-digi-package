import pytest
from unittest.mock import patch
from rkdigi.email_handling import EmailReader

EMAIL = "test@example.com"
PASSWORD = "password"
IMAP_SERVER = "imap.example.com"
IMAP_PORT = 143
ercc = "rkdigi.email_handling.EmailReader._can_connect"


def test_reader_init_success():
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
        assert reader.email == EMAIL
        assert reader.password == PASSWORD
        assert reader._imap_server == IMAP_SERVER
        assert reader._imap_port == IMAP_PORT


def test_reader_init_missing_email():
    with patch(ercc, return_value=True):
        with pytest.raises(ValueError):
            EmailReader(email=None, password=PASSWORD)


def test_reader_init_missing_password():
    with patch(ercc, return_value=True):
        with pytest.raises(ValueError):
            EmailReader(email=EMAIL, password=None)


def test_reader_init_connection_error():
    with patch(ercc, return_value=False):
        with pytest.raises(ConnectionError):
            EmailReader(
                email=EMAIL,
                password=PASSWORD,
                imap_server=IMAP_SERVER,
                imap_port=IMAP_PORT
            )


def test_can_connect_success(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    reader = EmailReader(
        email=EMAIL,
        password=PASSWORD,
        imap_server=IMAP_SERVER,
        imap_port=IMAP_PORT
    )
    assert reader._can_connect() is True


def test_can_connect_fail(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("NO", None)

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    assert EmailReader._can_connect(reader) is False


def test_list_mailboxes_success(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)

        def list(self):
            return ("OK", [b'(")" "/" INBOX', b'(")" "/" Sent'])

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
    mailboxes = reader.list_mailboxes()
    assert mailboxes == ["INBOX", "Sent"]


def test_list_mailboxes_error(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)

        def list(self):
            return ("NO", [])

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
    with pytest.raises(ConnectionError):
        reader.list_mailboxes()


def test_get_emails_success(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)
        def select(self, mailbox): return ("OK", None)

        def uid(self, command, *args):
            if command == 'search':
                return ("OK", [b'1 2'])
            elif command == 'fetch':
                msg = b"From: foo@bar.com\nSubject: Test\n\nBody"
                return ("OK", [(None, msg)])
            else:
                return ("NO", [])

        def store(self, email_id, command, flags): pass

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
    emails, failed = reader.get_emails()
    assert len(emails) == 2
    assert all(email["Subject"] == "Test" for email in emails)
    assert failed == []


def test_get_emails_partial_fail(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)
        def select(self, mailbox): return ("OK", None)

        def uid(self, command, *args):
            if command == 'search':
                return ("OK", [b'1 2 3'])
            elif command == 'fetch' and args[0] in [b'1', b'3']:
                msg = b"From: foo@bar.com\nSubject: Test\n\nBody"
                return ("OK", [(None, msg)])
            else:
                return ("NO", [])

        def store(self, email_id, command, flags): pass

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
    emails, failed = reader.get_emails()
    assert len(emails) == 2
    assert b'2' in failed


def test_get_emails_search_error(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)
        def select(self, mailbox): return ("OK", None)

        def uid(self, command, *args):
            return ("NO", [])

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
    with pytest.raises(ConnectionError):
        reader.get_emails()


def test_get_emails_with_max(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)
        def select(self, mailbox): return ("OK", None)

        def uid(self, command, *args):
            if command == 'search':
                return ("OK", [b'1 2 3 4'])
            elif command == 'fetch':
                msg = f"From: foo@bar.com\nSubject: \
                    Test {args[0].decode()}\n\nBody".encode()
                return ("OK", [(None, msg)])
            else:
                return ("NO", [])

        def store(self, email_id, command, flags): pass

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
    emails, failed = reader.get_emails(max=2)
    assert len(emails) == 2
    assert emails[0]["Subject"] == "Test 1"
    assert emails[1]["Subject"] == "Test 2"
    assert failed == []


def test_get_emails_with_reverse_order(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)
        def select(self, mailbox): return ("OK", None)

        def uid(self, command, *args):
            if command == 'search':
                return ("OK", [b'1 2 3'])
            elif command == 'fetch':
                msg = f"From: foo@bar.com\nSubject: \
                    Test {args[0].decode()}\n\nBody".encode()
                return ("OK", [(None, msg)])
            else:
                return ("NO", [])

        def store(self, email_id, command, flags): pass

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
    emails, failed = reader.get_emails(low_to_high=False)
    assert len(emails) == 3
    assert emails[0]["Subject"] == "Test 3"
    assert emails[0].uid == b'3'
    assert emails[1]["Subject"] == "Test 2"
    assert emails[1].uid == b'2'
    assert failed == []


def test_get_emails_with_flags(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)
        def select(self, mailbox): return ("OK", None)

        def uid(self, command, *args):
            if command == 'search':
                return ("OK", [b'1 2 3 4'])
            elif command == 'fetch':
                msg = f"From: foo@bar.com\nSubject: \
                    Test {args[0].decode()}\n\nBody".encode()
                return ("OK", [(None, msg)])
            else:
                return ("NO", [])

        def store(self, email_id, command, flags):
            assert command == '+FLAGS'
            assert flags == "\\Seen"

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
    emails, failed = reader.get_emails(modifiers="\\Seen", max=2)
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)
        def select(self, mailbox): return ("OK", None)

        def uid(self, command, *args):
            if command == 'search':
                return ("OK", [b'1 2 3 4'])
            elif command == 'fetch':
                msg = f"From: foo@bar.com\nSubject: \
                    Test {args[0].decode()}\n\nBody".encode()
                return ("OK", [(None, msg)])
            else:
                return ("NO", [])

        def fetch(self, email_id, _):
            msg = f"From: foo@bar.com\nSubject: \
                Test {email_id.decode()}\n\nBody".encode()
            return ("OK", [(None, msg)])

        def store(self, email_id, command, flags):
            assert command == '-FLAGS'
            assert flags == "\\Flagged"

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
    emails, failed = reader.get_emails(set_flags="\\Seen", max=2)
    assert len(emails) == 2
    assert emails[0]["Subject"] == "Test 1"
    assert emails[1]["Subject"] == "Test 2"
    assert failed == []


def test_get_emails_with_removing_flags(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)
        def select(self, mailbox): return ("OK", None)

        def search(self, charset, criteria):
            return ("OK", [b'1 2 3 4'])

        def fetch(self, email_id, _):
            msg = f"From: foo@bar.com\nSubject: \
                Test {email_id.decode()}\n\nBody".encode()
            return ("OK", [(None, msg)])

        def store(self, email_id, command, flags):
            assert command == '-FLAGS'
            assert flags == "\\Flagged"

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
    emails, failed = reader.get_emails(
        set_flags=None,
        del_flags="\\Flagged",
        max=2
    )
    assert len(emails) == 2
    assert emails[0]["Subject"] == "Test 1"
    assert emails[1]["Subject"] == "Test 2"
    assert failed == []


def test_get_email_by_uid_success(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)
        def select(self, mailbox): return ("OK", None)

        def uid(self, command, *args):
            msg = b"From: foo@bar.com\nSubject: Test 123"
            return ("OK", [(None, msg)])

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
    email = reader.get_email_by_uid(b'123')
    assert email["Subject"] == "Test 123"
    assert email.uid == b'123'


def test_get_email_by_uid_failure(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)
        def select(self, mailbox): return ("OK", None)

        def uid(self, command, *args):
            return ("NO", [])

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
        with pytest.raises(ConnectionError):
            reader.get_email_by_uid(b'123')


@pytest.mark.asyncio
async def test_list_mailboxes_async(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)

        def list(self):
            return ("OK", [b'("\")" "/" INBOX', b'("\")" "/" Sent'])

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
    mailboxes = await reader.list_mailboxes_async()
    assert mailboxes == ["INBOX", "Sent"]


@pytest.mark.asyncio
async def test_get_emails_async(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)
        def select(self, mailbox): return ("OK", None)

        def uid(self, command, *args):
            if command == 'search':
                return ("OK", [b'1 2'])
            elif command == 'fetch':
                msg = b"From: foo@bar.com\nSubject: Test\n\nBody"
                return ("OK", [(None, msg)])
            else:
                return ("NO", [])

        def store(self, email_id, command, flags):
            pass

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
    emails, failed = await reader.get_emails_async()
    assert len(emails) == 2
    assert all(email["Subject"] == "Test" for email in emails)
    assert failed == []


@pytest.mark.asyncio
async def test_get_emails_async_with_max(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)
        def select(self, mailbox): return ("OK", None)

        def uid(self, command, *args):
            if command == 'search':
                return ("OK", [b'1 2 3 4'])
            elif command == 'fetch':
                msg = f"From: foo@bar.com\nSubject: \
                    Test {args[0].decode()}\n\nBody".encode()
                return ("OK", [(None, msg)])

        def store(self, email_id, command, flags):
            pass

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
    emails, failed = await reader.get_emails_async(max=2)
    assert len(emails) == 2
    assert emails[0]["Subject"] == "Test 1"
    assert emails[1]["Subject"] == "Test 2"
    assert failed == []


@pytest.mark.asyncio
async def test_get_emails_async_with_flags(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)
        def select(self, mailbox): return ("OK", None)

        def uid(self, command, *args):
            if command == 'search':
                return ("OK", [b'1 2 3 4'])
            elif command == 'fetch':
                msg = f"From: foo@bar.com\nSubject: \
                    Test {args[0].decode()}\n\nBody".encode()
                return ("OK", [(None, msg)])

        def store(self, email_id, command, flags):
            assert command == '+FLAGS'
            assert flags == "\\Seen"

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
    emails, failed = await reader.get_emails_async(set_flags="\\Seen", max=2)
    assert len(emails) == 2
    assert emails[0]["Subject"] == "Test 1"
    assert emails[1]["Subject"] == "Test 2"
    assert failed == []


@pytest.mark.asyncio
async def test_get_email_by_uid_async_success(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)
        def select(self, mailbox): return ("OK", None)

        def uid(self, command, *args):
            msg = b"From: foo@bar.com\nSubject: Test 123"
            return ("OK", [(None, msg)])

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
        email = await reader.get_email_by_uid_async(b'123')
        assert email["Subject"] == "Test 123"
        assert email.uid == b'123'


@pytest.mark.asyncio
async def test_get_email_by_uid_async_failure(monkeypatch):
    class DummyIMAP:
        def __init__(self, host, port): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def starttls(self): pass
        def login(self, email, password): return ("OK", None)
        def select(self, mailbox): return ("OK", None)

        def uid(self, command, *args):
            return ("NO", [])

    monkeypatch.setattr("imaplib.IMAP4", DummyIMAP)
    with patch(ercc, return_value=True):
        reader = EmailReader(
            email=EMAIL,
            password=PASSWORD,
            imap_server=IMAP_SERVER,
            imap_port=IMAP_PORT
        )
        with pytest.raises(ConnectionError):
            await reader.get_email_by_uid_async(b'123')
