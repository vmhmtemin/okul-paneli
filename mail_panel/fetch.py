"""E-postaları okuma: Gmail IMAP (gerçek kullanım) veya .eml klasörü (test/demo).

Gmail için normal şifre DEĞİL, "Uygulama Şifresi" (App Password) kullanılır.
Kutuyu salt-okunur açıyoruz; hiçbir mail "okundu" olarak işaretlenmez.
"""
from __future__ import annotations

import email
import imaplib
import re
import time
from datetime import datetime, timedelta
from email import policy
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import Mail
from .textutil import html_to_text

IMAP_HOST = "imap.gmail.com"
MAX_MESSAGES = 400          # güvenlik sınırı
BATCH_SIZE = 50             # tek istekte kaç mail çekilsin
MAX_TEXT_BYTES = 40_000     # her mailin gövdesinden en fazla bu kadar bayt (ekleri indirmez)
TIME_BUDGET_S = 240         # indirme 4 dakikayı geçerse kalanları bırak


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
        except Exception:
            # Kesilmiş (ilk 40 KB) veya bozuk kodlanmış parça: elden geldiğince çöz
            payload = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            try:
                content = payload.decode(charset, errors="replace")
            except LookupError:
                content = payload.decode("utf-8", errors="replace")
        body = html_to_text(content) if part.get_content_type() == "text/html" else content

    return Mail(uid=uid, sender_name=name or addr, sender_email=addr.lower(),
                subject=subject, date=date, body=body)


def _parse_fetch_response(data) -> list[tuple[str, bytes]]:
    """Toplu FETCH yanıtını (uid, başlık+metin baytları) listesine çevir.

    Gmail her mail için iki parça döndürür: BODY[HEADER] ve BODY[TEXT]<0>.
    """
    out: list[tuple[str, bytes]] = []
    current_uid, header, text = None, b"", b""
    for item in data:
        if not isinstance(item, tuple):
            continue
        meta, payload = item[0], item[1] or b""
        uid_m = re.search(rb"UID (\d+)", meta)
        if b"BODY[HEADER]" in meta:
            if current_uid is not None:
                out.append((current_uid, header + text))
            current_uid = uid_m.group(1).decode() if uid_m else str(len(out))
            header, text = payload, b""
        elif b"BODY[TEXT]" in meta:
            text = payload
            if uid_m and current_uid is None:
                current_uid = uid_m.group(1).decode()
    if current_uid is not None:
        out.append((current_uid, header + text))
    return out


def fetch_imap(user: str, app_password: str, since_days: int, tz: ZoneInfo) -> list[Mail]:
    """Gmail gelen kutusundan son `since_days` günün maillerini getir.

    Hızlı olması için:
      * mailler 50'şerli gruplar halinde tek istekte çekilir,
      * her mailin sadece başlığı ve gövdesinin ilk 40 KB'ı indirilir
        (ekler / büyük görseller indirilmez).
    """
    since = (datetime.now(tz) - timedelta(days=since_days)).strftime("%d-%b-%Y")
    mails: list[Mail] = []
    started = time.monotonic()
    with imaplib.IMAP4_SSL(IMAP_HOST, timeout=60) as imap:
        imap.login(user, app_password)
        imap.select("INBOX", readonly=True)
        status, data = imap.uid("search", None, f"(SINCE {since})")
        if status != "OK":
            raise RuntimeError("IMAP arama başarısız")
        uids = data[0].split()[-MAX_MESSAGES:]
        print(f"{len(uids)} mail bulundu, indiriliyor…", flush=True)
        for i in range(0, len(uids), BATCH_SIZE):
            chunk = b",".join(uids[i:i + BATCH_SIZE]).decode()
            # BODY.PEEK → maili okunmuş olarak işaretlemez; <0.N> → sadece ilk N bayt
            status, resp = imap.uid("fetch", chunk,
                                    f"(BODY.PEEK[HEADER] BODY.PEEK[TEXT]<0.{MAX_TEXT_BYTES}>)")
            if status != "OK":
                continue
            for uid, raw in _parse_fetch_response(resp):
                mail = _message_to_mail(uid, raw, tz)
                if mail:
                    mails.append(mail)
            if time.monotonic() - started > TIME_BUDGET_S:
                print("Süre sınırına yaklaşıldı; kalan mailler atlandı.", flush=True)
                break
    print(f"İndirme {time.monotonic() - started:.1f} sn sürdü.", flush=True)
    return mails


def load_eml_dir(folder: Path, tz: ZoneInfo) -> list[Mail]:
    """Test ve demo için: klasördeki .eml dosyalarını mail gibi oku."""
    mails = []
    for path in sorted(folder.glob("*.eml")):
        mail = _message_to_mail(path.stem, path.read_bytes(), tz)
        if mail:
            mails.append(mail)
    return mails
