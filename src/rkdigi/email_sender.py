import os
import smtplib
from typing import Sequence
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class EmailSender:
    def __init__(
        self,
        smtp_server: str | None = None,
        smtp_port: int | None = None,
        sender_email: str | None = None,
        sender_password: str | None = None
    ):
        self._smtp_server = smtp_server or \
            os.environ.get("SMTP_SERVER", "smtp.randers.dk")
        self._smtp_port = smtp_port or int(os.environ.get("SMTP_PORT", 25))
        self.sender_email = sender_email
        self._sender_password = sender_password
        if not self._can_connect():
            raise ConnectionError(
                f"Cannot connect to SMTP server "
                f"{self._smtp_server}:{self._smtp_port}"
            )

    def _can_connect(self) -> bool:
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
        from_addr: str,
        recipients: str | Sequence[str] | None,
        subject: str,
        body: str,
        cc: str | Sequence[str] | None,
        attachments: Sequence[str | tuple[str, bytes]] | None
    ) -> tuple[MIMEMultipart, str, Sequence[str]]:
        if recipients is None:
            recipients = []
        if cc is None:
            cc = []
        if attachments is None:
            attachments = []

        recipients_list = [recipients] if isinstance(recipients, str) \
            else list(recipients)
        cc_list = [cc] if isinstance(cc, str) else list(cc)

        to_addrs = recipients_list + cc_list

        msg = MIMEMultipart()
        msg["From"] = from_addr
        msg["Subject"] = subject or ""

        if recipients_list:
            msg["To"] = ", ".join(recipients_list)

        if cc_list:
            msg["Cc"] = ", ".join(cc_list)

        body_part = MIMEText(body, "html") \
            if body and "<html>" in body.lower() \
            else MIMEText(body or " ", "plain")

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
        return msg, from_addr, to_addrs

    def send_email(
        self,
        sender: str = "",
        recipients: str | Sequence[str] | None = None,
        subject: str = "",
        body: str = "",
        cc: str | Sequence[str] | None = None,
        attachments: Sequence[str | tuple[str, bytes]] | None = None
    ) -> None:
        with smtplib.SMTP(
            host=self._smtp_server,
            port=self._smtp_port
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
                    from_addr = self.sender_email
            else:
                from_addr = sender or self.sender_email

            if not from_addr or not recipients and not cc:
                raise ValueError(
                    "A sender and at least one recipient "
                    "(recipients or cc) must be specified."
                )

            msg, from_addr, to_addrs = self._build_message(
                from_addr=from_addr,
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
        sender: str = "",
        recipients: str | Sequence[str] | None = None,
        subject: str = "",
        body: str = "",
        cc: str | Sequence[str] | None = None,
        attachments: Sequence[str | tuple[str, bytes]] | None = None
    ) -> None:
        import aiosmtplib
        if self.sender_email and self._sender_password:
            if sender:
                raise ValueError(
                    "Cannot specify sender when using "
                    "authenticated email sending."
                )
            from_addr = self.sender_email
        else:
            from_addr = sender or self.sender_email

        if not from_addr or not recipients and not cc:
            raise ValueError(
                "A sender and at least one recipient "
                "(recipients or cc) must be specified."
            )

        msg, from_addr, to_addrs = self._build_message(
            from_addr=from_addr,
            recipients=recipients,
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
