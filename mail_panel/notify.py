"""Telefona bildirim: kişinin kendi Gmail adresine kısa bir özet e-postası.

Aynı Uygulama Şifresi ile Gmail SMTP üzerinden gönderilir. Telefonda Gmail
bildirimi açıksa, özet bildirim olarak düşer.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from html import escape

from .models import SUMMARY_SUBJECT_PREFIX
from .report import Report

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def build_subject(r: Report) -> str:
    parts = []
    if r.new_count:
        parts.append(f"{r.new_count} yeni")
    if r.urgent_count:
        parts.append(f"{r.urgent_count} iş 48 saat içinde")
    if not parts:
        parts.append("yeni bir şey yok")
    return f"{SUMMARY_SUBJECT_PREFIX} {' · '.join(parts)}"


def build_bodies(r: Report, panel_url: str | None) -> tuple[str, str]:
    """(düz metin, HTML) gövdeleri. Mobil mail uygulamaları için sade tutuldu."""
    upcoming = [t for t in r.todos if t.urgency in ("urgent", "soon")][:6]

    text = [r.title, r.generated_text, ""]
    text += [f"• {s}" for s in r.summary]
    if upcoming:
        text += ["", "Yaklaşanlar:"]
        text += [f"[ ] {t.kind_label} – {t.group}: {t.title} ({t.when_text})" for t in upcoming]
    if panel_url:
        text += ["", f"Panelin tamamı: {panel_url}"]

    rows = "".join(
        f'<tr><td style="padding:8px 0;border-top:1px solid #e3e1d9">'
        f'<div style="font-size:12px;color:#6b6a66">{escape(t.kind_label)} · {escape(t.group)}</div>'
        f'<div style="font-weight:600">{escape(t.title)}</div>'
        f'<div style="font-size:14px;color:{"#c2410c" if t.urgency == "urgent" else "#1d1d1f"}">'
        f'{escape(t.when_text)}{" (" + escape(t.rel_text) + ")" if t.rel_text else ""}</div>'
        f"</td></tr>"
        for t in upcoming
    )
    button = (
        f'<p style="margin:20px 0 4px"><a href="{escape(panel_url)}" '
        f'style="display:inline-block;background:#2f5bd3;color:#fff;text-decoration:none;'
        f'font-weight:600;padding:12px 20px;border-radius:10px">Paneli aç</a></p>'
        if panel_url else ""
    )
    html = f"""\
<div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;font-size:16px;line-height:1.5;color:#1d1d1f;max-width:560px">
  <div style="font-size:13px;color:#6b6a66">{escape(r.generated_text)}</div>
  <ul style="padding-left:18px;margin:12px 0">{''.join(f'<li style="margin:4px 0">{escape(s)}</li>' for s in r.summary)}</ul>
  {f'<div style="font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#6b6a66;margin-top:16px">Yaklaşanlar</div><table style="width:100%;border-collapse:collapse">{rows}</table>' if rows else ''}
  {button}
</div>"""
    return "\n".join(text), html


def send_summary(r: Report, user: str, app_password: str, to: str, panel_url: str | None) -> None:
    msg = EmailMessage()
    msg["Subject"] = build_subject(r)
    msg["From"] = f"Okul Paneli <{user}>"
    msg["To"] = to
    plain, html = build_bodies(r, panel_url)
    msg.set_content(plain)
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(user, app_password)
        smtp.send_message(msg)
