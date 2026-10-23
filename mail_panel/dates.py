"""Türkçe / İngilizce metinden tarih ve saat çıkarma (yapay zekasız, kurallarla).

Desteklenen örnekler:
    "25 Ekim 2026", "25 Ekim'e kadar", "25.10.2026", "25/10", "October 25",
    "Cuma günü", "haftaya salı", "yarın", "bugün", "bu akşam",
    saatler: "23:59", "saat 14.00", "saat 9", "14:30'da"
Göreli tarihler mailin gönderildiği güne göre hesaplanır.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

TR_MONTHS = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "mayis": 5,
    "haziran": 6, "temmuz": 7, "ağustos": 8, "agustos": 8, "eylül": 9, "eylul": 9,
    "ekim": 10, "kasım": 11, "kasim": 11, "aralık": 12, "aralik": 12,
}
EN_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
TR_WEEKDAYS = {
    "pazartesi": 0, "salı": 1, "sali": 1, "çarşamba": 2, "carsamba": 2,
    "perşembe": 3, "persembe": 3, "cumartesi": 5, "cuma": 4, "pazar": 6,
}
EN_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

_TR_LETTERS = "a-zçğıöşü"
# Türkçe ekleri (Ekim'e, Cuma'ya, cumaya) kabul et, ama "pazarlama" gibi
# başka kelimeleri ele: en fazla 3 harflik ek.
_SUFFIX = rf"(?:['’]?[{_TR_LETTERS}]{{0,3}})(?![{_TR_LETTERS}])"


def _alt(words) -> str:
    # Uzun kelimeler önce (cumartesi > cuma, pazartesi > pazar)
    return "|".join(sorted(map(re.escape, words), key=len, reverse=True))


RX_NUMERIC = re.compile(r"(?<![\d.:/])(\d{1,2})([./-])(\d{1,2})(?:\2(\d{4}|\d{2}))?(?![\d:])")
RX_TR_MONTH = re.compile(rf"(?<!\d)(\d{{1,2}})\s+({_alt(TR_MONTHS)}){_SUFFIX}(?:\s+(\d{{4}}))?")
RX_EN_MONTH_A = re.compile(rf"\b({_alt(EN_MONTHS)})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\b")
RX_EN_MONTH_B = re.compile(rf"(?<!\d)(\d{{1,2}})(?:st|nd|rd|th)?\s+({_alt(EN_MONTHS)})\b\.?(?:,?\s+(\d{{4}}))?")
RX_TR_WEEKDAY = re.compile(
    rf"(?<![{_TR_LETTERS}])(?:(haftaya|gelecek hafta|önümüzdeki|bu)\s+)?({_alt(TR_WEEKDAYS)}){_SUFFIX}"
)
RX_EN_WEEKDAY = re.compile(rf"\b(?:(next|this)\s+)?({_alt(EN_WEEKDAYS)})\b")
RX_RELATIVE = re.compile(
    rf"(?<![{_TR_LETTERS}])(bugün|bu akşam|bu gece|bu öğlen|yarın|öbür gün|today|tonight|tomorrow)(?![{_TR_LETTERS}])"
)
RX_TIME = re.compile(r"(?<![\d.:/])([01]?\d|2[0-3])[:.]([0-5]\d)(?![\d:/])(?!\.\d)")
RX_SAAT_HOUR = re.compile(r"saat\s*([01]?\d|2[0-3])(?![\d:.])")

# Erteleme bildiren cümlelerde en GEÇ tarih yeni tarihtir
RX_POSTPONE = re.compile(r"(ertelen|ileri bir tarihe|postpon|reschedul|moved to|yeni tarih)", re.I)


@dataclass
class FoundDate:
    when: datetime
    has_time: bool
    start: int
    end: int


def tr_lower(text: str) -> str:
    """Türkçe kurallarına göre küçült; karakter sayısını (konumları) korur."""
    return text.replace("İ", "i").replace("I", "ı").lower()


def _make_date(base: datetime, day: int, month: int, year: int | None) -> datetime | None:
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    if year is not None and year < 100:
        year += 2000
    y = year or base.year
    try:
        d = base.replace(year=y, month=month, day=day, hour=0, minute=0, second=0, microsecond=0)
    except ValueError:
        return None
    # Yıl yazılmamışsa ve tarih çok geride kaldıysa (Aralık'ta "5 Ocak") → gelecek yıl
    if year is None and d < base - timedelta(days=60):
        d = d.replace(year=y + 1)
    return d


def _next_weekday(base: datetime, weekday: int, next_week: bool) -> datetime:
    start = base.replace(hour=0, minute=0, second=0, microsecond=0)
    delta = (weekday - start.weekday()) % 7
    if next_week:
        delta += 7 if delta != 0 else 7
    return start + timedelta(days=delta)


def _date_spans(text: str, base: datetime) -> list[FoundDate]:
    tl = tr_lower(text)
    el = text.lower()
    found: list[FoundDate] = []
    taken: list[tuple[int, int]] = []

    def add(dt, s, e):
        if dt is None:
            return
        if any(s < te and e > ts for ts, te in taken):   # çakışan eşleşmeyi alma
            return
        taken.append((s, e))
        found.append(FoundDate(dt, False, s, e))

    for m in RX_TR_MONTH.finditer(tl):
        add(_make_date(base, int(m[1]), TR_MONTHS[m[2]], int(m[3]) if m[3] else None), m.start(), m.end())
    for m in RX_EN_MONTH_A.finditer(el):
        add(_make_date(base, int(m[2]), EN_MONTHS[m[1]], int(m[3]) if m[3] else None), m.start(), m.end())
    for m in RX_EN_MONTH_B.finditer(el):
        add(_make_date(base, int(m[1]), EN_MONTHS[m[2]], int(m[3]) if m[3] else None), m.start(), m.end())
    for m in RX_NUMERIC.finditer(text):
        sep, year = m[2], m[4]
        # "14.30" gibi saatlerle karışmasın: yılsız sadece "/" ayıracını kabul et
        if year is None and sep != "/":
            continue
        add(_make_date(base, int(m[1]), int(m[3]), int(year) if year else None), m.start(), m.end())
    def next_to_explicit_date(s, e) -> bool:
        # "28 Ekim Çarşamba" / "Friday, 30 October": gün adı tarihin eşlikçisi,
        # ayrı bir tarih değil
        return any(0 <= s - te <= 3 or 0 <= ts - e <= 3 for ts, te in taken)

    for m in RX_TR_WEEKDAY.finditer(tl):
        if next_to_explicit_date(m.start(), m.end()):
            continue
        nxt = m[1] in ("haftaya", "gelecek hafta")
        add(_next_weekday(base, TR_WEEKDAYS[m[2]], nxt), m.start(), m.end())
    for m in RX_EN_WEEKDAY.finditer(el):
        if next_to_explicit_date(m.start(), m.end()):
            continue
        add(_next_weekday(base, EN_WEEKDAYS[m[2]], m[1] == "next"), m.start(), m.end())
    for m in RX_RELATIVE.finditer(tl):
        word = m[1]
        offset = {"yarın": 1, "tomorrow": 1, "öbür gün": 2}.get(word, 0)
        day = base.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=offset)
        add(day, m.start(), m.end())
    return found


def _attach_times(text: str, dates: list[FoundDate]) -> None:
    """Her tarihe aynı satırda, yakınındaki saati bağla."""
    masked = list(text)
    for d in dates:                                   # tarih metnini saat aramasından gizle
        for i in range(d.start, d.end):
            masked[i] = " "
    masked_text = "".join(masked)
    times: list[tuple[int, int, int]] = []            # (konum, saat, dakika)
    for m in RX_TIME.finditer(masked_text):
        times.append((m.start(), int(m[1]), int(m[2])))
    for m in RX_SAAT_HOUR.finditer(tr_lower(masked_text)):
        times.append((m.start(), int(m[1]), 0))

    for d in dates:
        line_start = text.rfind("\n", 0, d.start) + 1
        line_end = text.find("\n", d.end)
        line_end = len(text) if line_end == -1 else line_end
        best = None
        for pos, h, mi in times:
            if not (line_start <= pos < line_end):
                continue
            dist = pos - d.end if pos >= d.end else d.start - pos
            if dist > 45:
                continue
            if best is None or dist < best[0]:
                best = (dist, h, mi)
        if best:
            d.when = d.when.replace(hour=best[1], minute=best[2])
            d.has_time = True


def find_dates(text: str, base: datetime) -> list[FoundDate]:
    dates = _date_spans(text, base)
    _attach_times(text, dates)
    dates.sort(key=lambda d: d.start)
    return dates


def pick_deadline(text: str, base: datetime) -> tuple[datetime | None, bool]:
    """Mailin "asıl" tarihini seç.

    - Mailin gönderildiği günden önceki tarihler elenir.
    - Erteleme mailinde en geç tarih, diğerlerinde en yakın tarih seçilir.
    - Saat bulunamazsa gün sonu (23:59) kabul edilir, ama has_time=False döner.
    """
    day_start = base.replace(hour=0, minute=0, second=0, microsecond=0)
    candidates = [d for d in find_dates(text, base) if d.when >= day_start]
    if not candidates:
        return None, False
    if RX_POSTPONE.search(text):
        chosen = max(candidates, key=lambda d: d.when)
    else:
        chosen = min(candidates, key=lambda d: d.when)
    # Aynı gün hem saatli hem saatsiz geçiyorsa (konu: "Cumartesi", gövde:
    # "Cumartesi saat 11:00") saatli olanı tercih et
    same_day_timed = [d for d in candidates
                      if d.has_time and d.when.date() == chosen.when.date()]
    if not chosen.has_time and same_day_timed:
        chosen = same_day_timed[0]
    when = chosen.when if chosen.has_time else chosen.when.replace(hour=23, minute=59)
    return when, chosen.has_time
