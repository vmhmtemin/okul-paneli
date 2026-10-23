"""Rapor → HTML panel (Jinja2 şablonu ile)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .classify import KIND_LABELS
from .report import Report, TR_MONTHS, fmt_date

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def _short_date(dt: datetime) -> str:
    return f"{dt.day} {TR_MONTHS[dt.month - 1]} {dt:%H:%M}"


def render_panel(report: Report, out_file: Path) -> Path:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "j2"]),   # mail içeriği HTML olarak çalışmasın
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["short_date"] = _short_date
    env.filters["long_date"] = lambda dt, has_time=True: fmt_date(dt, has_time)
    html = env.get_template("panel.html.j2").render(r=report, kind_labels=KIND_LABELS)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html, encoding="utf-8")
    return out_file
