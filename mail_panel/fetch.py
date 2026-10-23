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
MAX_TEXT_BYTES = 120_000    # her mailin gövdesinden en fazla bu kadar bayt (ekleri indirmez)
TIME_BUDGET_S = 240         # indirme 4 dakikayı geçerse kalanları bırak


def _decode_part(part) -> str:
    """Bir MIME parçasını metne çevir; kesilmiş/bozuk kodlamalara dayanıklı."""
    try:
        content = part.get_content()
    except Exception:
        payload = part.get_payload(decode=True) or b""
        charset = part.get_content_charset() or "utf-8"
        try:
            content = payload.decode(charset, errors="replace")
        except LookupError:
            content = payload.decode("utf-8", errors="replace")
    if not isinstance(content, str):
        return ""
    return html_to_text(content) if part.get_content_type() == "text/html" else content


def _extract_body(msg) -> str:
    """Önce düz metin, yoksa HTML gövdeyi döndür. Boş çıkan parçaları atla."""
    candidates = []
    best = msg.get_body(preferencelist=("plain", "html"))
    if best is not None:
        candidates.append(best)
    for ctype in ("text/plain", "text/html"):
        for part in msg.walk():
            if part.get_content_type() == ctype and part.get_content_disposition() != "attachment":
                candidates.append(part)
    for part in candidates:
        text = _decode_part(part).strip()
        if len(text) > 20:
            return text
    return ""


def _is_bulk(msg, own_address: str | None) -> bool:
    """Toplu/duyuru maili mi? (posta listesi başlıkları veya kişiye özel gönderilmemiş)"""
    if msg.get("List-Id") or msg.get("List-Unsubscribe"):
        return True
    if str(msg.get("Precedence", "")).strip().lower() in ("bulk", "list", "junk"):
        return True
    if own_address:
        recipients = " ".join(str(msg.get(h, "")) for h in ("To", "Cc")).lower()
        if own_address.lower() not in recipients:
            return True          # gizli alıcı (BCC) veya bir liste adresine gitmiş
    return False


def _message_to_mail(uid: str, raw: bytes, tz: ZoneInfo, own_address: str | None = None) -> Mail | None:
    msg = email.message_from_bytes(raw, policy=policy.default)

    name, addr = parseaddr(str(msg.get("From", "")))
    subject = " ".join(str(msg.get("Subject", "") or "(konu yok)").split())

    try:
        date = parsedate_to_datetime(str(msg.get("Date")))
        if date.tzinfo is None:
            date = date.replace(tzinfo=ZoneInfo("UTC"))
        date = date.astimezone(tz)
    except (TypeError, ValueError):
        return None

    return Mail(uid=uid, sender_name=name or addr, sender_email=addr.lower(),
                subject=subject, date=date, body=_extract_body(msg),
                is_bulk=_is_bulk(msg, own_address))


def _parse_fetch_response(data) -> list[tuple[str, bytes]]:
    """Toplu FETCH yanıtını (uid, başlık+metin) listesine çevir.

    Her mail "N (" ile başlayan bir parçayla başlar; içindeki BODY[HEADER] ve
    BODY[TEXT] parçaları HERHANGİ bir sırayla gelebilir.
    """
    messages: list[dict] = []
    for item in data:
        if not isinstance(item, tuple):
            continue
        meta, payload = item[0] or b"", item[1] or b""
        if re.match(rb"\d+ \(", meta) or not messages:
            messages.append({"uid": None, "header": b"", "text": b""})
        cur = messages[-1]
        uid_m = re.search(rb"UID (\d+)", meta)
        if uid_m:
            cur["uid"] = uid_m.group(1).decode()
        if b"BODY[HEADER]" in meta:
            cur["header"] = payload
        elif b"BODY[TEXT]" in meta:
            cur["text"] = payload
    out = []
    for i, m in enumerate(messages):
        if not m["header"]:
            continue
        header = m["header"]
        if not header.endswith((b"\r\n\r\n", b"\n\n")):
            header = header.rstrip(b"\r\n") + b"\r\n\r\n"
        out.append((m["uid"] or str(i), header + m["text"]))
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
                mail = _message_to_mail(uid, raw, tz, own_address=user)
                if mail:
                    mails.append(mail)
            if time.monotonic() - started > TIME_BUDGET_S:
                print("Süre sınırına yaklaşıldı; kalan mailler atlandı.", flush=True)
                break
    empty = sum(1 for m in mails if not m.body)
    bulk = sum(1 for m in mails if m.is_bulk)
    print(f"İndirme {time.monotonic() - started:.1f} sn sürdü. "
          f"{len(mails)} mail çözüldü ({bulk} toplu duyuru, {empty} gövdesi boş).", flush=True)
    return mails


def load_eml_dir(folder: Path, tz: ZoneInfo) -> list[Mail]:
    """Test ve demo için: klasördeki .eml dosyalarını mail gibi oku."""
    mails = []
    for path in sorted(folder.glob("*.eml")):
        mail = _message_to_mail(path.stem, path.read_bytes(), tz)
        if mail:
            mails.append(mail)
    return mails
