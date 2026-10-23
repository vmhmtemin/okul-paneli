"""Mail Paneli — giriş noktası.

Gerçek kullanım (GitHub Actions bunu çalıştırır):
    python main.py --send

Kendi bilgisayarında örnek maillerle deneme (şifre gerekmez):
    python tests/make_samples.py
    python main.py --source eml --config tests/test_config.yaml --now 2026-10-23T20:00

Ortam değişkenleri (GitHub'da "Secrets" olarak girilir):
    GMAIL_USER          okunacak Gmail adresi
    GMAIL_APP_PASSWORD  Gmail Uygulama Şifresi (16 harf)
    NOTIFY_TO           özet mailinin gideceği adres (boşsa GMAIL_USER)
    PANEL_URL           GitHub Pages linki (özet mailindeki buton için)
    SUPABASE_URL        (isteğe bağlı) görev senkronu için Supabase proje adresi
    SUPABASE_KEY        (isteğe bağlı) Supabase "publishable" anahtarı
    SYNC_KEY            (isteğe bağlı) en az 32 karakterlik gizli senkron anahtarı
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from mail_panel.classify import Classifier
from mail_panel.fetch import fetch_imap, load_eml_dir
from mail_panel.notify import build_subject, send_summary
from mail_panel.render import render_panel
from mail_panel.report import build_report

ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Gmail → mobil okul paneli")
    p.add_argument("--source", choices=["imap", "eml"], default="imap")
    p.add_argument("--eml-dir", type=Path, default=ROOT / "tests" / "sample_mails")
    p.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    p.add_argument("--out", type=Path, default=ROOT / "site" / "index.html")
    p.add_argument("--now", help="Test için 'şu an' (ISO, örn. 2026-10-23T20:00)")
    p.add_argument("--send", action="store_true", help="Özet e-postasını gönder")
    p.add_argument("--send-when", choices=["new", "always"], default="new",
                   help="new: sadece yeni ilgili mail varsa gönder (varsayılan)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    tz = ZoneInfo(config.get("timezone", "Europe/Istanbul"))
    now = datetime.fromisoformat(args.now).replace(tzinfo=tz) if args.now else datetime.now(tz)

    user = os.environ.get("GMAIL_USER", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()

    # 1) Mailleri oku
    if args.source == "imap":
        if not user or not password:
            print("HATA: GMAIL_USER ve GMAIL_APP_PASSWORD tanımlı değil.", file=sys.stderr)
            return 2
        mails = fetch_imap(user, password, config.get("lookback_days", 14), tz)
    else:
        mails = load_eml_dir(args.eml_dir, tz)
    print(f"{len(mails)} mail okundu.")

    # 2) Sınıflandır
    classifier = Classifier(config, now)
    analyzed = [a for m in mails if (a := classifier.analyze(m))]
    print(f"{len(analyzed)} mail ders/kulüple ilgili bulundu.")

    # 3) Paneli üret
    report = build_report(analyzed, now, config)
    sync = None
    sb_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    sb_key = os.environ.get("SUPABASE_KEY", "").strip()
    sync_key = os.environ.get("SYNC_KEY", "").strip()
    if sb_url and sb_key and len(sync_key) >= 32:
        sync = {"url": sb_url, "key": sb_key, "syncKey": sync_key}
    elif sb_url or sb_key or sync_key:
        print("UYARI: Senkron ayarları eksik/hatalı; görevler sadece cihazda saklanacak.")
    out = render_panel(report, args.out, sync)
    print(f"Panel yazıldı → {out}  ({len(report.todos)} yapılacak, {report.new_count} yeni, "
          f"senkron: {'açık' if sync else 'kapalı'})")

    # 4) Bildirim
    if args.send:
        if args.send_when == "new" and report.new_count == 0:
            print("Yeni ilgili mail yok; özet e-postası gönderilmedi.")
        else:
            to = os.environ.get("NOTIFY_TO", "").strip() or user
            send_summary(report, user, password, to, os.environ.get("PANEL_URL") or None)
            print(f"Özet e-postası gönderildi: {build_subject(report)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
