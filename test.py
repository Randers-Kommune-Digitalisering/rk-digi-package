from rkdigi import EmailSender
from email.message import Message
from typing import Any

mailer = EmailSender(
    smtp_server="relay.randers.dk",
    smtp_port=587,
    sender_email="kantinedata@randers.dk",
    sender_password="P4t1&!7VpYZvtyS^%RdaJ$mh",
    sender_name="Kantinedata",
    reply_to_email="st@randers.dk",
    reply_to_name="Søren LST"
)

# mailer = EmailSender(
#     smtp_server="smtp.randers.dk",
#     smtp_port=25,
#     sender_email="kantinedata@randers.dk",
#     sender_name="Kantinedata",
#     reply_to_email="st@randers.dk",
#     reply_to_name="Søren LST"
# )

mailer.send_email(
    recipients=["st@randers.dk"],
    subject="Test af mail",
    body="<html><h1>Testindhold</h1><p>Dette er alm tekst i paragraffen.</p></html>",
)

# reader = EmailReader(
# 	email='kantinedata@randers.dk',
# 	password='P4t1&!7VpYZvtyS^%RdaJ$mh',
# 	imap_server='10.193.9.202',
# 	imap_port=143
# )
# import json


# def _body_preview(message: Message, max_chars: int = 2000) -> str | None:
# 	if message.is_multipart():
# 		# Prefer text/plain, then text/html
# 		plain_part: Message | None = None
# 		html_part: Message | None = None
# 		for part in message.walk():
# 			if part.get_content_maintype() == "multipart":
# 				continue
# 			if part.get("Content-Disposition"):
# 				# skip attachments
# 				continue
# 			content_type = (part.get_content_type() or "").lower()
# 			if content_type == "text/plain" and plain_part is None:
# 				plain_part = part
# 			elif content_type == "text/html" and html_part is None:
# 				html_part = part
# 		chosen = plain_part or html_part
# 		if chosen is None:
# 			return None
# 		payload = chosen.get_payload(decode=True)
# 		charset = chosen.get_content_charset() or "utf-8"
# 		text = (
# 			payload.decode(charset, errors="replace")
# 			if isinstance(payload, (bytes, bytearray))
# 			else str(chosen.get_payload())
# 		)
# 	else:
# 		payload = message.get_payload(decode=True)
# 		charset = message.get_content_charset() or "utf-8"
# 		text = (
# 			payload.decode(charset, errors="replace")
# 			if isinstance(payload, (bytes, bytearray))
# 			else str(message.get_payload())
# 		)

# 	text = text.strip()
# 	if not text:
# 		return None
# 	return text[:max_chars]


# def _message_to_dict(message: Message) -> dict[str, Any]:
# 	return {
# 		"id": message.get("Message-ID"),
# 		"Subject": message.get("Subject"),
# 		"From": message.get("From"),
# 		"To": message.get("To"),
# 		"Cc": message.get("Cc"),
# 		"Date": message.get("Date"),
# 		"Message-ID": message.get("Message-ID"),
# 		"Content-Type": message.get_content_type(),
# 		"BodyPreview": str(message.get_payload())
# 	}


# def _json_default(obj: Any):
# 	if isinstance(obj, Message):
# 		return _message_to_dict(obj)
# 	if isinstance(obj, (bytes, bytearray)):
# 		return bytes(obj).decode("utf-8", errors="replace")
# 	return str(obj)


# emails, failed = reader.get_emails(criteria='(UNSEEN)', mark_seen=False)
# print(
# 	"Read mails:",
# 	json.dumps({"emails": emails, "failed": failed}, indent=2, ensure_ascii=False, default=_json_default),
# )
# email = reader.get_email_by_id(email_id="<27a5661ac63f4113be28c005e1502673@randers.dk>", mark_seen=True)
# print(
# 	"Read mails:",
# 	json.dumps({"email": email}, indent=2, ensure_ascii=False, default=_json_default),
# )

