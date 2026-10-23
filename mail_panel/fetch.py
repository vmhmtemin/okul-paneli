"""E-postaları okuma: Gmail IMAP (gerçek kullanım) veya .eml klasörü (test/demo).

Gmail için normal şifre DEĞİL, "Uygulama Şifresi" (App Password) kullanılır.
Kutuyu salt-okunur açıyoruz; hiçbir mail "okundu" olarak işaretlenmez.
"""
from __future__ import annotations

import email
import imaplib
from datetime import datetime, timedelta
from email import policy
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import Mail
from .textutil import html_to_text

IMAP_HOST = "imap.gmail.com"
MAX_MESSAGES = 400          # güvenlik sınırı


def _message_to_mail(uid: str, raw: bytes, tz: ZoneInfo) -> Mail | None:
    msg = email.message_from_bytes(raw, policy=policy.default)

    name, addr = parseaddr(str(msg.get("From", "")))
    subject = str(msg.get("Subject", "") or "(konu yok)").strip()

    try:
        date = parsedate_to_datetime(str(msg.get("Date")))
        if date.tzinfo is None:
            date = date.replace(tzinfo=ZoneInfo("UTC"))
        date = date.astimezone(tz)
    except (TypeError, ValueError):
        return None

    body = ""
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is not None:
        try:
            content = part.get_content()
        except (LookupError, UnicodeDecodeError):
            content = part.get_payload(decode=True).decode("utf-8", errors="replace")
        body = html_to_text(content) if part.get_content_type() == "text/html" else content

    return Mail(uid=uid, sender_name=name or addr, sender_email=addr.lower(),
                subject=subject, date=date, body=body)


def fetch_imap(user: str, app_password: str, since_days: int, tz: ZoneInfo) -> list[Mail]:
    """Gmail gelen kutusundan son `since_days` günün maillerini getir."""
    since = (datetime.now(tz) - timedelta(days=since_days)).strftime("%d-%b-%Y")
    mails: list[Mail] = []
    with imaplib.IMAP4_SSL(IMAP_HOST) as imap:
        imap.login(user, app_password)
        imap.select("INBOX", readonly=True)
        status, data = imap.uid("search", None, f"(SINCE {since})")
        if status != "OK":
            raise RuntimeError("IMAP arama başarısız")
        uids = data[0].split()[-MAX_MESSAGES:]
        for uid in uids:
            # BODY.PEEK → maili okunmuş olarak işaretlemez
            status, msg_data = imap.uid("fetch", uid, "(BODY.PEEK[])")
            if status != "OK" or not msg_data or msg_data[0] is None:
                continue
            mail = _message_to_mail(uid.decode(), msg_data[0][1], tz)
            if mail:
                mails.append(mail)
    return mails


def load_eml_dir(folder: Path, tz: ZoneInfo) -> list[Mail]:
    """Test ve demo için: klasördeki .eml dosyalarını mail gibi oku."""
    mails = []
    for path in sorted(folder.glob("*.eml")):
        mail = _message_to_mail(path.stem, path.read_bytes(), tz)
        if mail:
            mails.append(mail)
    return mails
