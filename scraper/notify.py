"""Trimite alerta.txt pe email prin SMTP. Prima linie = subiect, restul = continut.

Variabile (GitHub Secrets): SMTP_USER, SMTP_PASS, EMAIL_TO; optional SMTP_HOST (implicit smtp.mail.yahoo.com), SMTP_PORT (465).
"""
import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

path = Path(__file__).resolve().parent.parent / "alerta.txt"
if not path.exists():
    print("Nicio alerta.")
    sys.exit(0)

user, password, to = (os.environ.get(k) for k in ("SMTP_USER", "SMTP_PASS", "EMAIL_TO"))
if not (user and password and to):
    print("Lipsesc secretele SMTP_USER / SMTP_PASS / EMAIL_TO; emailul nu a fost trimis.")
    sys.exit(1)

subject, _, body = path.read_text(encoding="utf-8").partition("\n")
msg = EmailMessage()
msg["Subject"], msg["From"], msg["To"] = subject, user, to
msg.set_content(body)
with smtplib.SMTP_SSL(os.environ.get("SMTP_HOST") or "smtp.mail.yahoo.com", int(os.environ.get("SMTP_PORT") or 465)) as s:
    s.login(user, password)
    s.send_message(msg)
print(f"Email trimis: {subject}")
