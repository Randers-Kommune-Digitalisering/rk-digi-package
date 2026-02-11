import os
import smtplib
from typing import Sequence
import html2text
from email import encoders
from email.utils import formataddr
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


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
            if self._check_address_header(sender_email):
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
            if self._check_address_header(reply_to_email):
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

    def _check_address_header(self, address: str | tuple[str, str]) -> bool:
        """
        Method to check if the provided address is a valid address header.
        """
        if isinstance(address, str):
            return '@' in address
        elif isinstance(address, tuple) and len(address) == 2:
            return '@' in address[1]
        return False

    def _can_connect(self) -> bool:
        """
        method to check if connection to
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

    def _build_message(
        self,
        sender: str | tuple[str, str],
        reply_to: str | tuple[str, str],
        recipients: list[str | tuple[str, str]],
        subject: str,
        body: str,
        cc: str | list[str | tuple[str, str]] | None,
        attachments: Sequence[str | tuple[str, bytes]] | None
    ) -> tuple[MIMEMultipart, str, Sequence[str]]:
        """
        Method to build the message object and return it
        along with from_addr and to_addrs.
        """
        if cc is None:
            cc = []
        if attachments is None:
            attachments = []

        cc_list = [cc] if isinstance(cc, str) or isinstance(cc, tuple) else cc

        to_headers = recipients + cc_list

        for addr in [sender] + to_headers + ([reply_to] if reply_to else []):
            if not self._check_address_header(addr):
                raise ValueError(f"Invalid email address: {addr}")

        msg = MIMEMultipart()
        msg["From"] = formataddr(sender) if isinstance(sender, tuple) \
            else sender

        if reply_to:
            msg["Reply-To"] = formataddr(reply_to) \
                if isinstance(reply_to, tuple) else reply_to

        if recipients:
            msg["To"] = ", ".join(
                formataddr(addr) if isinstance(addr, tuple) else addr
                for addr in recipients
            )

        if cc_list:
            msg["Cc"] = ", ".join(
                formataddr(addr) if isinstance(addr, tuple) else addr
                for addr in cc_list
            )

        msg["Subject"] = subject or ""

        body_part = MIMEText(body, "html") \
            if body and "<html>" in body.lower() \
            else MIMEText(body or " ", "plain")

        if body_part.get_content_subtype() == "html":
            plain_text = html2text.html2text(body)
            msg.attach(MIMEText(plain_text, "plain"))

        msg.attach(body_part)

        for att in attachments:
            if isinstance(att, str):
                # If value in attachments is a string,
                # treat it as a file path
                with open(att, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                filename = os.path.basename(att)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{filename}"'
                )
                msg.attach(part)
            elif (isinstance(att, tuple)
                    and len(att) == 2
                    and isinstance(att[0], str)
                    and isinstance(att[1], bytes)):
                # If value in attachments is
                # a tuple of (filename, content)
                # then only 'bytes' content is supported
                filename, content = att
                part = MIMEBase("application", "octet-stream")
                part.set_payload(content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{filename}"'
                )
                msg.attach(part)
            else:
                raise ValueError(
                    "Attachments must be file paths "
                    "or (filename, content) tuples."
                )
        from_addr = formataddr(sender) if isinstance(sender, tuple) else sender
        to_addrs = [
            formataddr(addr) if isinstance(addr, tuple) else addr
            for addr in to_headers
        ]

        return msg, from_addr, to_addrs

    def send_email(
        self,
        recipients: str | list[str | tuple[str, str]],
        sender: str | tuple[str, str] = "",
        reply_to: str | tuple[str, str] | None = None,
        subject: str = "",
        body: str = "",
        cc: str | list[str | tuple[str, str]] | None = None,
        attachments: Sequence[str | tuple[str, bytes]] | None = None
    ) -> None:
        """
        Sends an email with the specified parameters (sync).
        Will try to authenticate with the SMTP server
        if sender_email and sender_password were provided in the constructor.
        """
        with smtplib.SMTP(
            host=self._smtp_server,
            port=self._smtp_port,
            timeout=60
        ) as server:
            server.starttls()
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

            if not sender or not recipients and not cc:
                raise ValueError(
                    "A sender and at least one recipient "
                    "(recipients or cc) must be specified."
                )

            recipients_list = [recipients] if isinstance(recipients, str) \
                else recipients

            msg, from_addr, to_addrs = self._build_message(
                sender=sender,
                reply_to=reply_to or self.reply_to,
                recipients=recipients_list,
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
        sender: str = "",
        reply_to: str | tuple[str, str] | None = None,
        recipients: str | Sequence[str] | None = None,
        subject: str = "",
        body: str = "",
        cc: str | Sequence[str] | None = None,
        attachments: Sequence[str | tuple[str, bytes]] | None = None
    ) -> None:
        """
        Sends an email with the specified parameters (async).
        Will try to authenticate with the SMTP server
        if sender_email and sender_password were provided in the constructor.
        """
        import aiosmtplib
        if self.sender_email and self._sender_password:
            if sender:
                raise ValueError(
                    "Cannot specify sender when using "
                    "authenticated email sending."
                )

        sender = sender or self.sender or self.sender_email

        if not sender or not recipients and not cc:
            raise ValueError(
                "A sender and at least one recipient "
                "(recipients or cc) must be specified."
            )

        recipients_list = [recipients] if isinstance(recipients, str) \
            else recipients

        msg, from_addr, to_addrs = self._build_message(
            sender=sender,
            reply_to=reply_to or self.reply_to,
            recipients=recipients_list,
            subject=subject,
            body=body,
            cc=cc,
            attachments=attachments
        )

        smtp_kwargs = dict(
            hostname=self._smtp_server,
            port=self._smtp_port,
            start_tls=True,
        )

        if self.sender_email and self._sender_password:
            smtp_kwargs["username"] = self.sender_email
            smtp_kwargs["password"] = self._sender_password

        async with aiosmtplib.SMTP(**smtp_kwargs) as server:
            await server.send_message(
                msg,
                from_addr=from_addr,
                to_addrs=to_addrs
            )
