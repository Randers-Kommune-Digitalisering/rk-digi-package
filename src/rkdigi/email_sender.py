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
        import os
        self._smtp_server = smtp_server or \
            os.environ.get("SMTP_SERVER", "smtp.randers.dk")
        self._smtp_port = smtp_port or int(os.environ.get("SMTP_PORT", 25))
        self.sender_email = sender_email
        self._sender_password = sender_password

    def send_email(
        self,
        sender: str = "",
        recipients: str | Sequence[str] = [],
        subject: str = "",
        body: str = "",
        cc: str | Sequence[str] = [],
        attachments: Sequence[str | tuple[str, bytes]] = []
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

            recipients_list = [recipients] if isinstance(recipients, str) \
                else list(recipients)
            cc_list = [cc] if isinstance(cc, str) else list(cc)

            to_addrs = recipients_list + cc_list

            if not from_addr or not to_addrs:
                raise ValueError(
                    "A sender and at least one recipient "
                    "(recipients or cc) must be specified."
                )

            msg = MIMEMultipart()
            msg["From"] = from_addr
            msg["Subject"] = subject or ""

            if recipients_list:
                msg["To"] = ", ".join(recipients_list)

            if cc_list:
                msg["Cc"] = ", ".join(cc_list)

            body = MIMEText(body, "html") \
                if body and "<html>" in body.lower() \
                else MIMEText(body or " ", "plain")

            msg.attach(body)

            for att in attachments:
                if isinstance(att, str):
                    with open(att, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f'attachment; filename="{att}"'
                    )
                    msg.attach(part)
                elif (isinstance(att, tuple)
                      and len(att) == 2
                      and isinstance(att[0], str)
                      and isinstance(att[1], bytes)):
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

            server.sendmail(
                from_addr=from_addr,
                to_addrs=to_addrs,
                msg=msg.as_string()
            )
