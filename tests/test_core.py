"""Birim testleri:  python -m pytest -q"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mail_panel import fetch, notify  # noqa: E402
from mail_panel.classify import Classifier  # noqa: E402
from mail_panel.dates import pick_deadline  # noqa: E402
from mail_panel.report import build_report  # noqa: E402
from mail_panel.textutil import clean_body, extract_links  # noqa: E402

TZ = ZoneInfo("Europe/Istanbul")
FRI = datetime(2026, 10, 23, 10, 0, tzinfo=TZ)          # Cuma
NOW = datetime(2026, 10, 23, 20, 0, tzinfo=TZ)
CFG = yaml.safe_load((ROOT / "tests" / "test_config.yaml").read_text(encoding="utf-8"))
SAMPLES = ROOT / "tests" / "sample_mails"


def d(y, mo, da, h=23, mi=59):
    return datetime(y, mo, da, h, mi, tzinfo=TZ)


# ------------------------------------------------------------------ tarihler
def test_turkish_month_with_time():
    assert pick_deadline("25 Ekim 2026 saat 23:59'a kadar", FRI) == (d(2026, 10, 25), True)


def test_numeric_date():
    assert pick_deadline("Son teslim: 30.10.2026 23.59", FRI) == (d(2026, 10, 30), True)


def test_next_week_weekday():
    assert pick_deadline("haftaya Salı saat 10:00", FRI) == (d(2026, 11, 3, 10, 0), True)


def test_tomorrow():
    assert pick_deadline("yarın 14:30'da toplantı", FRI) == (d(2026, 10, 24, 14, 30), True)


def test_postponed_picks_new_date():
    when, _ = pick_deadline("15 Kasım olan vize 22 Kasım'a ertelenmiştir", FRI)
    assert when.date() == d(2026, 11, 22).date()


def test_weekday_next_to_date_is_not_separate():
    when, _ = pick_deadline("28 Ekim Çarşamba dersler iptal", datetime(2026, 10, 21, 9, 0, tzinfo=TZ))
    assert when.date() == d(2026, 10, 28).date()


def test_plain_time_is_not_a_date():
    assert pick_deadline("Ders 14.30 da başlayacak", FRI) == (None, False)


def test_pazarlama_is_not_pazar():
    assert pick_deadline("Pazarlama dersi", FRI) == (None, False)


def test_year_rollover():
    when, _ = pick_deadline("5 Ocak'ta final", datetime(2026, 12, 20, 9, 0, tzinfo=TZ))
    assert when.year == 2027


# ----------------------------------------------------------- metin temizleme
def test_signature_and_quote_removed():
    body = "Merhaba,\nÖdev yarın.\n\nSaygılarımla,\nDr. X\nTel: 123\n> eski mesaj"
    assert clean_body(body) == "Merhaba,\nÖdev yarın."


def test_meeting_links_first():
    links = extract_links("doc https://drive.google.com/x zoom https://zoom.us/j/1 https://x.com/unsubscribe")
    assert [l.label for l in links] == ["Zoom", "Google Drive"]


# ---------------------------------------------------------- sınıflandırma
def _analyze_samples():
    c = Classifier(CFG, NOW)
    mails = fetch.load_eml_dir(SAMPLES, TZ)
    return {m.uid: c.analyze(m) for m in mails}


def test_samples_classification():
    r = _analyze_samples()
    assert r["07_promo"] is None and r["08_arkadas"] is None
    assert r["01_coe203_proje"].group == "COE203"
    assert r["02_math101_quiz_html"].group == "MATH101"
    assert r["04_gdg_toplanti"].category == "club"
    assert r["05_sks_izin_yazisi"].group == "SKS"
    assert "exam" not in r["05_sks_izin_yazisi"].kinds        # linkteki "example" sayılmamalı
    assert r["06_foto_stant"].deadline == d(2026, 10, 24, 11, 0)


def test_report_hides_past_and_sorts():
    analyzed = [a for a in _analyze_samples().values() if a]
    rep = build_report(analyzed, NOW, CFG)
    titles = [t.title for t in rep.todos]
    assert "PHYS102 Lab raporu" not in titles                  # süresi geçmiş
    assert rep.todos[0].urgency == "urgent"
    deadlines = [t.deadline for t in rep.todos if t.deadline]
    assert deadlines == sorted(deadlines)


def test_own_summary_mail_is_ignored():
    from mail_panel.models import SUMMARY_SUBJECT_PREFIX, Mail
    m = Mail("1", "Okul Paneli", "me@gmail.com", f"{SUMMARY_SUBJECT_PREFIX} 3 yeni", NOW, "GDG toplantısı yarın")
    assert Classifier(CFG, NOW).analyze(m) is None


# --------------------------------------------- IMAP / SMTP (sahte sunucuyla)
def test_fetch_imap_readonly_and_peek():
    raw = (SAMPLES / "01_coe203_proje.eml").read_bytes()
    imap = mock.MagicMock()
    imap.__enter__.return_value = imap
    imap.uid.side_effect = lambda cmd, *a: ("OK", [b"7"]) if cmd == "search" else ("OK", [(b"7 (BODY[] {1}", raw)])
    with mock.patch.object(fetch.imaplib, "IMAP4_SSL", return_value=imap):
        mails = fetch.fetch_imap("u@gmail.com", "pw", 14, TZ)
    imap.select.assert_called_once_with("INBOX", readonly=True)
    assert imap.uid.call_args_list[1].args[2] == "(BODY.PEEK[])"   # okundu işaretlemez
    assert mails[0].subject.startswith("COE203")


def test_send_summary_uses_ssl_and_login():
    analyzed = [a for a in _analyze_samples().values() if a]
    rep = build_report(analyzed, NOW, CFG)
    smtp = mock.MagicMock()
    smtp.__enter__.return_value = smtp
    with mock.patch.object(notify.smtplib, "SMTP_SSL", return_value=smtp) as ctor:
        notify.send_summary(rep, "u@gmail.com", "pw", "u@gmail.com", "https://x.github.io/p/")
    ctor.assert_called_once_with("smtp.gmail.com", 465)
    smtp.login.assert_called_once_with("u@gmail.com", "pw")
    msg = smtp.send_message.call_args.args[0]
    assert msg["Subject"].startswith("📚 Okul Paneli:")
    assert "https://x.github.io/p/" in msg.get_body(("html",)).get_content()
