"""Analiz edilmiş maillerden panel verisini (özet, yapılacaklar, kartlar) oluşturur."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .classify import KIND_LABELS
from .models import AnalyzedMail, Link

TR_MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
             "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
TR_DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

# Yapılacaklar listesinde bir mail tek satır olur; birden çok türü varsa
# en önemlisi etiket olarak seçilir.
KIND_PRIORITY = ["exam", "assignment", "meeting", "followup"]

# Tarihsiz takip maillerini en fazla kaç gün listede tutalım?
FOLLOWUP_MAX_AGE_DAYS = 7


def fmt_date(dt: datetime, has_time: bool = True) -> str:
    """'Cuma, 30 Ekim · 23:59' biçimi."""
    s = f"{TR_DAYS[dt.weekday()]}, {dt.day} {TR_MONTHS[dt.month - 1]}"
    if dt.year != datetime.now(dt.tzinfo).year:
        s += f" {dt.year}"
    return s + (f" · {dt:%H:%M}" if has_time else "")


def relative_day(dt: datetime, now: datetime) -> str:
    days = (dt.date() - now.date()).days
    if days < 0:
        return "geçti"
    if days == 0:
        return "bugün"
    if days == 1:
        return "yarın"
    return f"{days} gün sonra"


@dataclass
class TodoItem:
    id: str
    kind: str                  # assignment / exam / meeting / followup / reminder
    kind_label: str
    group: str
    category: str
    title: str
    deadline: datetime | None
    has_time: bool
    link: Link | None
    urgency: str               # "urgent" (≤48 saat) / "soon" (≤7 gün) / "later" / "none"
    when_text: str = ""
    rel_text: str = ""


@dataclass
class Card:
    category: str              # academic / club
    group: str
    mails: list[AnalyzedMail] = field(default_factory=list)

    @property
    def new_count(self) -> int:
        return sum(1 for m in self.mails if m.is_new)


@dataclass
class Report:
    title: str
    generated_at: datetime
    generated_text: str
    summary: list[str]
    todos: list[TodoItem]
    academic_cards: list[Card]
    club_cards: list[Card]
    new_count: int
    new_academic: int
    new_club: int
    urgent_count: int


def _todo_from(a: AnalyzedMail, now: datetime) -> TodoItem | None:
    kinds = [k for k in KIND_PRIORITY if k in a.kinds]
    if a.deadline is not None and a.deadline < now:
        return None                                      # süresi geçmiş
    if a.deadline is None:
        # Tarihsiz: sadece "yanıt/takip" gerektiren yeni sayılabilecek mailler
        if "followup" not in a.kinds or a.mail.date < now - timedelta(days=FOLLOWUP_MAX_AGE_DAYS):
            return None
        kind = "followup"
    elif kinds:
        kind = kinds[0]
        # "Etkinlik" kelimesi geçiyor ama saat/toplantı linki yoksa bu bir
        # toplantı değil, büyük ihtimalle bir takip işi (izin yazısı, form...)
        has_meeting_link = any(l.label in ("Zoom", "Google Meet", "Teams") for l in a.links)
        if kind == "meeting" and "followup" in a.kinds and not (a.deadline_has_time or has_meeting_link):
            kind = "followup"
    else:
        return None        # türü belirsiz ya da sadece iptal bildirimi: kartta görünür, listeye girmez

    if a.deadline is None:
        urgency = "none"
    elif a.deadline - now <= timedelta(hours=48):
        urgency = "urgent"
    elif a.deadline - now <= timedelta(days=7):
        urgency = "soon"
    else:
        urgency = "later"

    meeting_link = next((l for l in a.links if l.label in ("Zoom", "Google Meet", "Teams")), None)
    link = meeting_link or (a.links[0] if a.links else None)

    return TodoItem(
        id=a.item_id,
        kind=kind,
        kind_label=KIND_LABELS.get(kind, "Hatırlatma"),
        group=a.group,
        category=a.category,
        title=a.mail.subject,
        deadline=a.deadline,
        has_time=a.deadline_has_time,
        link=link,
        urgency=urgency,
        when_text=fmt_date(a.deadline, a.deadline_has_time) if a.deadline else "Tarih belirtilmemiş",
        rel_text=relative_day(a.deadline, now) if a.deadline else "",
    )


def _summary(new: list[AnalyzedMail], todos: list[TodoItem], now: datetime, window_h: int) -> list[str]:
    lines: list[str] = []
    if not new:
        lines.append("Son taramadan bu yana ders veya kulüple ilgili yeni bir e-posta yok.")
    else:
        acad = sum(1 for a in new if a.category == "academic")
        club = len(new) - acad
        parts = []
        if acad:
            parts.append(f"{acad} akademik")
        if club:
            parts.append(f"{club} kulüp")
        lines.append(f"Son {window_h} saatte {len(new)} yeni e-posta geldi ({', '.join(parts)}).")
        cancels = [a for a in new if "cancel" in a.kinds]
        if cancels:
            groups = ", ".join(sorted({a.group for a in cancels}))
            lines.append(f"Dikkat: {groups} için iptal / tarih değişikliği duyurusu var.")

    dated = [t for t in todos if t.deadline]
    urgent = [t for t in dated if t.urgency == "urgent"]
    if urgent:
        lines.append(f"Önümüzdeki 48 saatte {len(urgent)} iş var; ilki: "
                     f"{urgent[0].group} – {urgent[0].kind_label.lower()} ({urgent[0].rel_text}, "
                     f"{urgent[0].deadline:%H:%M}).")
    elif dated:
        t = dated[0]
        lines.append(f"En yakın tarih: {t.group} – {t.kind_label.lower()}, {t.when_text} ({t.rel_text}).")
    followups = [t for t in todos if t.kind == "followup"]
    if followups:
        lines.append(f"{len(followups)} mail yanıt veya takip bekliyor.")
    return lines


def build_report(analyzed: list[AnalyzedMail], now: datetime, config: dict) -> Report:
    analyzed = sorted(analyzed, key=lambda a: a.mail.date, reverse=True)

    todos = [t for a in analyzed if (t := _todo_from(a, now))]
    order = {"urgent": 0, "soon": 1, "later": 2, "none": 3}
    far_future = now + timedelta(days=3650)
    todos.sort(key=lambda t: (order[t.urgency], t.deadline or far_future))

    # Kartlarda: yeni mailler + hâlâ geçerli tarihi / takibi olan mailler
    todo_ids = {t.id for t in todos}
    visible = [a for a in analyzed if a.is_new or a.item_id in todo_ids]
    cards: dict[tuple[str, str], Card] = {}
    for a in visible:
        cards.setdefault((a.category, a.group), Card(a.category, a.group)).mails.append(a)

    def card_sort(c: Card):
        # Yeni maili olan kartlar önce, sonra alfabetik ("Genel" en sonda)
        return (-c.new_count, c.group.startswith(("Bölüm", "Diğer")), c.group)

    academic_cards = sorted([c for c in cards.values() if c.category == "academic"], key=card_sort)
    club_cards = sorted([c for c in cards.values() if c.category == "club"], key=card_sort)

    new = [a for a in analyzed if a.is_new]
    window_h = config.get("new_window_hours", 13) - 1   # 1 saatlik payı gösterme
    return Report(
        title=config.get("panel_title", "Günlük Okul Paneli"),
        generated_at=now,
        generated_text=f"{fmt_date(now)} itibarıyla",
        summary=_summary(new, todos, now, window_h),
        todos=todos,
        academic_cards=academic_cards,
        club_cards=club_cards,
        new_count=len(new),
        new_academic=sum(1 for a in new if a.category == "academic"),
        new_club=sum(1 for a in new if a.category == "club"),
        urgent_count=sum(1 for t in todos if t.urgency == "urgent"),
    )
