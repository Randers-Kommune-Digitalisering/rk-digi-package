import os
import re
import asyncio
import imaplib
import smtplib
from typing import Sequence
import email as email_module
from email import encoders
from email.utils import formataddr, parseaddr
from email.message import EmailMessage
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from bs4 import BeautifulSoup


class EmailSender:
    """
    Class to send emails using SMTP server.
    It supports both synchronous and asynchronous sending of emails,
    as well as attachments.
    """
    def __init__(
        self,
        smtp_server: str | None = None,
        smtp_port: int | None = None,
        sender_email: str | None = None,
        sender_password: str | None = None,
        sender_name: str | None = None,
        reply_to_email: str | None = None,
        reply_to_name: str | None = None
    ):
        self._smtp_server = smtp_server or \
            os.environ.get("SMTP_SERVER", "smtp.randers.dk")
        self._smtp_port = smtp_port or int(os.environ.get("SMTP_PORT", 25))

        self.sender_email = sender_email
        self._sender_password = sender_password
        if sender_email:
            if self._is_valid_address(sender_email):
                if sender_name:
                    self.sender = (sender_name, sender_email)
                else:
                    self.sender = sender_email
            else:
                raise ValueError(
                    f"Invalid sender email address: {sender_email}"
                )
        else:
            self.sender = ""

        if reply_to_email:
            if self._is_valid_address(reply_to_email):
                if reply_to_name:
                    self.reply_to = (reply_to_name, reply_to_email)
                else:
                    self.reply_to = reply_to_email
            else:
                raise ValueError(
                    f"Invalid reply-to email address: {reply_to_email}"
                )
        else:
            self.reply_to = ""

        if not self._can_connect():
            raise ConnectionError(
                f"Cannot connect to SMTP server "
                f"{self._smtp_server}:{self._smtp_port}"
            )

    def _is_valid_address(self, address) -> bool:
        """
        Validate an address header.

        Accepts either:
        • a (name, email) tuple, or
        • a plain email string.
        """
        # Case 1: address is a plain string containing an email
        if isinstance(address, str):
            parsed = parseaddr(address)[1]
            return "@" in address and parsed == address

        # Case 2: address is a (name, email) tuple
        if (
            isinstance(address, tuple)
            and len(address) == 2
            and isinstance(address[1], str)
            and "@" in address[1]
            and "@" not in address[0]
            and parseaddr(formataddr(address))[1] == address[1]
        ):
            return True

        return False

    def _can_connect(self) -> bool:
        """
        Method to check if connection to
        SMTP server can be established.
        """
        try:
            with smtplib.SMTP(
                host=self._smtp_server,
                port=self._smtp_port,
                timeout=5
            ) as server:
                server.ehlo()
            return True
        except Exception:
            return False

    def _normalize_addresses(
        self,
        addresses: str | tuple[str, str] | Sequence[str | tuple[str, str]] | None,
    ) -> list[str | tuple[str, str]]:
        if addresses is None:
            return []
        if isinstance(addresses, str) and self._is_valid_address(addresses):
            return [addresses]
        elif isinstance(addresses, tuple) and self._is_valid_address(addresses):
            return [addresses]
        else:
            for addr in addresses:
                if not self._is_valid_address(addr):
                    raise ValueError(f"Invalid email address: {addr}")
        return list(addresses)

    def _build_message(
        self,
        sender: str | tuple[str, str],
        reply_to: str | tuple[str, str],
        recipients: str | tuple[str, str] | Sequence[str | tuple[str, str]],
        subject: str,
        body: str,
        cc: str | tuple[str, str] | Sequence[str | tuple[str, str]] | None,
        attachments: Sequence[str | tuple[str, bytes | bytearray | memoryview]] | None
    ) -> tuple[MIMEMultipart, str, Sequence[str]]:
        """
        Method to build the message object and return it
        along with from_addr and to_addrs.
        """
        attachments = attachments or []
        cc_list = self._normalize_addresses(cc)
        recipients_list = self._normalize_addresses(recipients)

        to_headers = recipients_list + cc_list

        for addr in [sender] + to_headers + ([reply_to] if reply_to else []):
            if not self._is_valid_address(addr):
                raise ValueError(f"Invalid email address: {addr}")

        msg = MIMEMultipart("mixed")
        msg["From"] = formataddr(sender) if isinstance(sender, tuple) \
            else sender

        if reply_to:
            msg["Reply-To"] = formataddr(reply_to) \
                if isinstance(reply_to, tuple) else reply_to

        if recipients:
            msg["To"] = ", ".join(
                formataddr(addr) if isinstance(addr, tuple) else addr
                for addr in recipients_list
            )

        if cc_list:
            msg["Cc"] = ", ".join(
                formataddr(addr) if isinstance(addr, tuple) else addr
                for addr in cc_list
            )

        msg["Subject"] = subject or ""

        soup = BeautifulSoup(body, "html.parser")

        if soup.find():  # If there are any HTML tags, treat as HTML email
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(soup.get_text(separator="\n", strip=True), "plain", "utf-8"))
            alt.attach(MIMEText(body, "html", "utf-8"))
            msg.attach(alt)
        else:
            msg.attach(MIMEText(body or "", "plain", "utf-8"))

        for att in attachments:
            if isinstance(att, str):
                # If value in attachments is a string,
                # treat it as a file path
                with open(att, "rb") as f:
                    filename = os.path.basename(att)
                    content = f.read()
            elif (isinstance(att, tuple)
                    and len(att) == 2
                    and isinstance(att[0], str)
                    and isinstance(att[1], (bytes, bytearray, memoryview))):
                # If value in attachments is a tuple of (filename, content),
                # content may be bytes, bytearray, or memoryview and will be
                # normalized to bytes before attaching.
                filename, content = att[0], bytes(att[1])
            else:
                raise ValueError(
                    "Attachments must be file paths "
                    "or (filename, content) tuples."
                )

            part = MIMEBase("application", "octet-stream")
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{filename}"'
            )
            msg.attach(part)
        from_addr = sender[1] if isinstance(sender, tuple) else sender
        to_addrs = [
            addr[1] if isinstance(addr, tuple) else addr
            for addr in to_headers
        ]

        return msg, from_addr, to_addrs

    def send_email(
        self,
        recipients: str | tuple[str, str] | Sequence[str | tuple[str, str]],
        sender: str | tuple[str, str] = "",
        reply_to: str | tuple[str, str] = "",
        subject: str = "",
        body: str = "",
        cc: str | tuple[str, str] | Sequence[str | tuple[str, str]] | None = None,
        attachments: Sequence[str | tuple[str, bytes]] | None = None
    ) -> None:
        """
        Sends an email with the specified parameters (sync).
        Will try to authenticate with the SMTP server.
        if sender_email and sender_password were provided in the constructor.
        """
        with smtplib.SMTP(
            host=self._smtp_server,
            port=self._smtp_port,
            timeout=60
        ) as server:
            server.ehlo()
            try:
                server.starttls()
                server.ehlo()
            except smtplib.SMTPException:
                # STARTTLS may be unsupported on some port 25 setups.
                # Fallback to unencrypted connection if STARTTLS fails or is not supported.
                pass
            if self.sender_email and self._sender_password:
                if sender:
                    raise ValueError(
                        "Cannot specify sender when using "
                        "authenticated email sending."
                    )
                else:
                    server.login(
                        user=self.sender_email,
                        password=self._sender_password
                    )

            sender = sender or self.sender or self.sender_email

            if not sender:
                raise ValueError("A sender must be specified.")

            if not recipients and not cc:
                raise ValueError(
                    "At least one recipient (recipients or cc) must be specified."
                )

            msg, from_addr, to_addrs = self._build_message(
                sender=sender,
                reply_to=reply_to or self.reply_to,
                recipients=recipients,
                subject=subject,
                body=body,
                cc=cc,
                attachments=attachments
            )

            server.sendmail(
                from_addr=from_addr,
                to_addrs=to_addrs,
                msg=msg.as_string()
            )

    async def send_email_async(
        self,
        sender: str | tuple[str, str] = "",
        reply_to: str | tuple[str, str] | None = None,
        recipients: str | tuple[str, str] | Sequence[str | tuple[str, str]] | None = None,
        subject: str = "",
        body: str = "",
        cc: str | tuple[str, str] | Sequence[str | tuple[str, str]] | None = None,
        attachments: Sequence[str | tuple[str, bytes]] | None = None
    ) -> None:
        """
        Sends an email with the specified parameters (async).
        Will try to authenticate with the SMTP server.
        if sender_email and sender_password were provided in the constructor.
        """
        import aiosmtplib
        if self.sender_email and self._sender_password and sender:
            raise ValueError(
                "Cannot specify sender when using authenticated email sending."
            )

        sender = sender or self.sender or self.sender_email

        if not sender:
            raise ValueError("A sender must be specified.")

        recipients_list = self._normalize_addresses(recipients)
        if not recipients_list and not cc:
            raise ValueError(
                "At least one recipient (recipients or cc) must be specified."
            )

        msg, from_addr, to_addrs = self._build_message(
            sender=sender,
            reply_to=reply_to or self.reply_to,
            recipients=recipients_list,
            subject=subject,
            body=body,
            cc=cc,
            attachments=attachments
        )

        async with aiosmtplib.SMTP(
            hostname=self._smtp_server,
            port=self._smtp_port,
            timeout=60,
        ) as server:
            await server.ehlo()
            try:
                await server.starttls()
                await server.ehlo()
            except (aiosmtplib.errors.SMTPNotSupported, aiosmtplib.errors.SMTPException):
                # STARTTLS may be unsupported on some port 25 setups.
                # Fallback to unencrypted connection if STARTTLS fails or is not supported.
                pass

            if self.sender_email and self._sender_password:
                await server.login(self.sender_email, self._sender_password)

            await server.send_message(
                msg,
                sender=from_addr,
                recipients=to_addrs
            )


class EmailReader:
    """
    Class to read emails from an IMAP server.
    """
    def __init__(
        self,
        email: str,
        password: str,
        imap_server: str | None = None,
        imap_port: int | None = None,
    ):
        if not all([email, password]):
            raise ValueError("Email and password must be provided.")
        self._imap_server = imap_server or \
            os.environ.get("IMAP_SERVER", "imap.randers.dk")
        self._imap_port = imap_port or int(os.environ.get("IMAP_PORT", 143))
        self.email = email
        self.password = password
        if not self._can_connect():
            raise ConnectionError(
                f"Cannot connect to IMAP server "
                f"{self._imap_server}:{self._imap_port}"
            )

    def _can_connect(self) -> bool:
        """
        method to check if connection to
        IMAP server can be established.
        """
        try:
            with imaplib.IMAP4(
                host=self._imap_server,
                port=self._imap_port
            ) as server:
                server.starttls()
                msg, _ = server.login(self.email, self.password)
                if msg != "OK":
                    raise ConnectionError("IMAP login failed.")
            return True
        except Exception:
            return False

    def list_mailboxes(self) -> list[str]:
        """
        List all mailboxes in the IMAP account.
        """
        with imaplib.IMAP4(
            host=self._imap_server,
            port=self._imap_port
        ) as server:
            server.starttls()
            server.login(self.email, self.password)
            status, mailboxes = server.list()
            if status != "OK":
                raise ConnectionError("Failed to list mailboxes.")
            return [
                mailbox.decode().split(' "/" ')[-1]
                for mailbox in mailboxes
            ]

    def get_emails(
        self,
        mailbox: str = "INBOX",
        criteria: str = "ALL",
        modifiers: str | None = None,
        max: int | None = None
    ) -> tuple[list[EmailMessage], list[bytes]]:
        """
        Retrieve emails from the specified mailbox
        matching the search criteria.

        param mailbox: The mailbox to search in (e.g., "INBOX")
        param criteria: The IMAP search criteria (e.g., "ALL", "UNSEEN")
        param modifiers: Optional IMAP flags to set on the emails
            after fetching (e.g., "\\Seen" to mark as read)
        param max: Optional maximum number of emails to fetch (all if None)
        """
        with imaplib.IMAP4(
            host=self._imap_server,
            port=self._imap_port
        ) as server:
            server.starttls()
            server.login(self.email, self.password)
            server.select(mailbox)
            status, data = server.search(None, criteria)
            if status != "OK":
                raise ConnectionError("Failed to search emails.")
            all_ids = data[0].split()
            if max is not None:
                email_ids = all_ids[:max]
            else:
                email_ids = all_ids
            emails = []
            failed_to_fetch_ids = []
            for email_id in email_ids:
                status, msg_data = server.fetch(email_id, "(RFC822)")
                if status != "OK":
                    failed_to_fetch_ids.append(email_id)
                    continue
                emails.append(email_module.message_from_bytes(msg_data[0][1]))
                if modifiers:
                    server.store(email_id, '+FLAGS', modifiers)
            return emails, failed_to_fetch_ids

    async def list_mailboxes_async(self) -> list[str]:
        """
        List all mailboxes in the IMAP account. (Async)
        """
        def _sync():
            return self.list_mailboxes()

        return await asyncio.to_thread(_sync)

    async def get_emails_async(
        self,
        mailbox: str = "INBOX",
        search_criteria: str = "ALL",
        modifiers: str | None = "\\Seen",
        max: int | None = None
    ) -> tuple[list[EmailMessage], list[bytes]]:
        """
        Retrieve emails from the specified mailbox
        matching the search criteria. (async)
        """
        def _sync():
            return self.get_emails(
                mailbox=mailbox,
                criteria=search_criteria,
                modifiers=modifiers,
                max=max
            )

        return await asyncio.to_thread(_sync)


class EmailManager:
    """
    Default email manager class that combines both EmailSender and EmailReader
    """
    def __init__(
            self,
            email: str,
            password: str,
            name: str | None = None,
            reply_to_email: str | None = None,
            reply_to_name: str | None = None,
            smtp_server: str | None = None,
            smtp_port: int | None = None,
            imap_server: str | None = None,
            imap_port: int | None = None,
            auth_for_sending: bool = False):
        self.email_sender = EmailSender(
            sender_email=email,
            sender_name=name,
            reply_to_email=reply_to_email,
            reply_to_name=reply_to_name,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            sender_password=password if auth_for_sending else None,
        )

        self.email_reader = EmailReader(
            email=email,
            password=password,
            imap_server=imap_server,
            imap_port=imap_port
        )

    def get_mailboxes(self, *args, **kwargs):
        return self.email_reader.list_mailboxes(*args, **kwargs)

    def get_emails(self, *args, **kwargs):
        return self.email_reader.get_emails(*args, **kwargs)

    def send_email(self, *args, **kwargs):
        return self.email_sender.send_email(*args, **kwargs)

    async def get_mailboxes_async(self, *args, **kwargs):
        return await self.email_reader.list_mailboxes_async(*args, **kwargs)

    async def get_emails_async(self, *args, **kwargs):
        return await self.email_reader.get_emails_async(*args, **kwargs)

    async def send_email_async(self, *args, **kwargs):
        return await self.email_sender.send_email_async(*args, **kwargs)
