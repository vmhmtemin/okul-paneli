"""Rapor → HTML panel (Jinja2 şablonu ile)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .classify import KIND_LABELS
from .report import Report, TR_MONTHS, fmt_date
from .textutil import clean_body

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def _short_date(dt: datetime) -> str:
    return f"{dt.day} {TR_MONTHS[dt.month - 1]} {dt:%H:%M}"


BODY_LIMIT = 8000        # panelde gösterilecek temiz metin (karakter)
RAW_LIMIT = 16000        # "tamamını göster" için ham metin (karakter)


def _panel_data(report: Report, sync: dict | None) -> str:
    """Sayfadaki JavaScript'e verilecek tüm veri."""
    def clip(text: str, n: int) -> str:
        return text if len(text) <= n else text[:n].rstrip() + "\n\n… (devamı kısaltıldı)"

    mails = []
    for a in report.mails:
        m = a.mail
        clean = clean_body(m.body)
        mails.append({
            "id": a.item_id, "cat": a.category, "group": a.group,
            "subject": m.subject, "from": m.sender_name, "fromEmail": m.sender_email,
            "date": m.date.isoformat(), "isNew": a.is_new, "thread": a.thread_count,
            "kinds": a.kinds, "kindLabels": [KIND_LABELS[k] for k in a.kinds if k in KIND_LABELS],
            "due": a.deadline.isoformat() if a.deadline else None, "hasTime": a.deadline_has_time,
            "links": [{"url": l.url, "label": l.label} for l in a.links],
            "attachments": m.attachments,
            "event": ({"summary": m.event.summary, "location": m.event.location} if m.event else None),
            "snippet": a.snippet,
            "body": clip(clean or m.body, BODY_LIMIT),
            "raw": clip(m.body, RAW_LIMIT) if m.body.strip() != clean.strip() else "",
        })
    data = {
        "generatedAt": report.generated_at.isoformat(),
        "summary": report.summary,
        "mailTodos": [
            {
                "id": t.id, "kind": t.kind, "kindLabel": t.kind_label, "group": t.group, "cat": t.category,
                "title": t.title, "due": t.deadline.isoformat() if t.deadline else None,
                "hasTime": t.has_time,
                "link": {"url": t.link.url, "label": t.link.label} if t.link else None,
            }
            for t in report.todos
        ],
        "mails": mails,
        "sync": sync,
    }
    # </script> kaçışı: veri <script> etiketinin içinde duruyor
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def render_panel(report: Report, out_file: Path, sync: dict | None = None) -> Path:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "j2"]),   # mail içeriği HTML olarak çalışmasın
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["short_date"] = _short_date
    env.filters["long_date"] = lambda dt, has_time=True: fmt_date(dt, has_time)
    html = env.get_template("panel.html.j2").render(
        r=report, kind_labels=KIND_LABELS, panel_data=_panel_data(report, sync))
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html, encoding="utf-8")
    return out_file
