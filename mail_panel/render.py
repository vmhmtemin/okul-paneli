"""Rapor → HTML panel (Jinja2 şablonu ile)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .classify import KIND_LABELS
from .report import Report, TR_MONTHS, fmt_date

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def _short_date(dt: datetime) -> str:
    return f"{dt.day} {TR_MONTHS[dt.month - 1]} {dt:%H:%M}"


def _panel_data(report: Report, sync: dict | None) -> str:
    """Sayfadaki JavaScript'e verilecek veri (yapılacaklar + senkron ayarı)."""
    data = {
        "generatedAt": report.generated_at.isoformat(),
        "mailTodos": [
            {
                "id": t.id, "kind": t.kind, "kindLabel": t.kind_label, "group": t.group,
                "title": t.title, "due": t.deadline.isoformat() if t.deadline else None,
                "hasTime": t.has_time,
                "link": {"url": t.link.url, "label": t.link.label} if t.link else None,
            }
            for t in report.todos
        ],
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
