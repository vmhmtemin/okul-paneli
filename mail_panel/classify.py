"""Kural tabanlı sınıflandırma: mail akademik mi, kulüp mü, ne tür bir görev?"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from .dates import pick_deadline, tr_lower
from .models import SUMMARY_SUBJECT_PREFIX, AnalyzedMail, Mail
from .textutil import clean_body, extract_links, make_snippet

# Görev türü → bu kelimelerden biri geçerse o tür sayılır
KIND_KEYWORDS: dict[str, list[str]] = {
    "cancel":     ["iptal", "ertelen", "yapılmayacak", "cancelled", "canceled", "postponed"],
    "exam":       ["sınav", "sinav", "quiz", "vize", "final", "midterm", "exam", "bütünleme"],
    "assignment": ["ödev", "odev", "proje", "teslim", "assignment", "homework", "project",
                   "deadline", "rapor", "submission"],
    "meeting":    ["toplantı", "toplanti", "meeting", "zoom", "google meet", "buluşma",
                   "etkinlik", "workshop", "seminer", "event"],
    "followup":   ["geri dönüş", "geri donus", "dönüş yap", "yanıt", "cevap ver", "onay",
                   "imza", "izin yazısı", "sponsor", "form", "doldur", "bilgi verir",
                   "please reply", "let me know", "rsvp", "katılım durumu"],
}

KIND_LABELS = {
    "assignment": "Ödev / Proje",
    "exam": "Sınav",
    "meeting": "Toplantı / Etkinlik",
    "followup": "Yanıt / Takip",
    "cancel": "İptal / Değişiklik",
}


_LETTERS = "a-zçğıöşü"
_URL = re.compile(r"https?://\S+", re.I)
# Bu İngilizce kelimeler tam kelime olarak aranır ("exam" ≠ "example").
# Türkçe kelimeler ise ek alabilir ("ödev" → "ödevlerinizi").
_WHOLE_WORD = {"exam", "quiz", "midterm", "assignment", "homework", "project", "deadline",
               "submission", "meeting", "event", "workshop", "rsvp", "cancelled", "canceled",
               "postponed", "lab", "form", "onay", "ders", "sks", "gdg"}
_rx_cache: dict[str, re.Pattern] = {}


def _keyword_rx(word: str) -> re.Pattern:
    w = tr_lower(word)
    if w not in _rx_cache:
        end = rf"s?(?![{_LETTERS}])" if w in _WHOLE_WORD else ""
        # "form" tam kelime olsa da "formu/formunu" gibi Türkçe ekleri kabul et
        if w in ("form", "onay", "ders", "lab"):
            end = rf"(?:[{_LETTERS}]{{0,4}})(?![{_LETTERS}])"
        _rx_cache[w] = re.compile(rf"(?<![{_LETTERS}]){re.escape(w)}{end}")
    return _rx_cache[w]


def _contains_any(haystack: str, needles: list[str]) -> bool:
    """`haystack` önceden tr_lower ile küçültülmüş olmalı. Linkler yok sayılır."""
    text = _URL.sub(" ", haystack)
    return any(_keyword_rx(n).search(text) for n in needles)


class Classifier:
    def __init__(self, config: dict, now: datetime):
        self.cfg = config
        self.now = now
        acad = config.get("academic", {})
        self.acad_domains = [tr_lower(d) for d in acad.get("sender_domains", [])]
        self.acad_addresses = [tr_lower(a) for a in acad.get("sender_addresses", [])]
        self.acad_keywords = acad.get("keywords", [])
        self.course_rx = re.compile(acad.get("course_code_regex", r"\b([A-Z]{2,5})\s?(\d{3})\b"))
        self.clubs = config.get("clubs", [])
        self.club_generic = config.get("club_generic_keywords", [])
        ign = config.get("ignore", {})
        self.ignore_sender = [tr_lower(s) for s in ign.get("sender_contains", [])]
        self.ignore_subject = [tr_lower(s) for s in ign.get("subject_contains", [])]
        self.new_since = now - timedelta(hours=config.get("new_window_hours", 13))

    # ------------------------------------------------------------- yardımcılar
    def _is_ignored(self, mail: Mail) -> bool:
        if mail.subject.startswith(SUMMARY_SUBJECT_PREFIX):     # kendi özet mailimiz
            return True
        sender = tr_lower(mail.sender_email + " " + mail.sender_name)
        subject = tr_lower(mail.subject)
        return any(s in sender for s in self.ignore_sender) or any(s in subject for s in self.ignore_subject)

    def _academic_sender(self, mail: Mail) -> bool:
        email = tr_lower(mail.sender_email)
        domain = email.rsplit("@", 1)[-1]
        return email in self.acad_addresses or any(
            domain == d or domain.endswith("." + d) for d in self.acad_domains
        )

    def _match_club(self, mail: Mail, text: str) -> str | None:
        email = tr_lower(mail.sender_email)
        # Gönderen adı ve adresi de ipucu: "SKS Daire Başkanlığı" <sks@...>
        sender_text = tr_lower(mail.sender_name) + " " + re.sub(r"[@._-]", " ", email)
        for club in self.clubs:
            if email in [tr_lower(a) for a in club.get("sender_addresses", [])]:
                return club["name"]
            keywords = club.get("keywords", [])
            if _contains_any(text, keywords) or _contains_any(sender_text, keywords):
                return club["name"]
        return None

    def _course_code(self, *texts: str) -> str | None:
        for t in texts:
            m = self.course_rx.search(t)
            if m:
                return f"{m.group(1).upper()}{m.group(2)}"
        return None

    # ---------------------------------------------------------------- ana iş
    def analyze(self, mail: Mail) -> AnalyzedMail | None:
        if self._is_ignored(mail):
            return None

        body = clean_body(mail.body)
        subject_l = tr_lower(mail.subject)
        full_l = tr_lower(mail.subject + "\n" + body)

        # 1) Kategori — konu satırı en güçlü ipucu, sonra gönderen, sonra gövde
        category, group = None, None
        club = self._match_club(mail, subject_l)
        if club:
            category, group = "club", club
        elif self._academic_sender(mail):
            # Akademik adresten gelse bile gövdede kulüp adı geçiyorsa kulüp maili
            club = self._match_club(mail, full_l)
            category, group = ("club", club) if club else ("academic", None)
        elif (club := self._match_club(mail, full_l)):
            category, group = "club", club
        elif _contains_any(subject_l, self.acad_keywords):
            category = "academic"
        elif _contains_any(subject_l, self.club_generic):
            category, group = "club", "Diğer Kulüp İşleri"
        else:
            return None                                  # ders/kulüple ilgisiz

        if category == "academic":
            group = self._course_code(mail.subject, body) or "Bölüm / Genel Duyurular"

        # 2) Görev türleri
        kinds = [k for k, words in KIND_KEYWORDS.items() if _contains_any(full_l, words)]

        # 3) Tarih, linkler, özet
        deadline, has_time = pick_deadline(mail.subject + "\n" + body, mail.date)
        links = extract_links(body)
        if not any(l.label in ("Zoom", "Google Meet", "Teams") for l in links):
            # Toplantı linki bazen imzanın altında kalır; tüm metne de bak
            meeting = [l for l in extract_links(mail.body) if l.label in ("Zoom", "Google Meet", "Teams")]
            links = (meeting + links)[:4]

        return AnalyzedMail(
            mail=mail,
            category=category,
            group=group,
            kinds=kinds,
            deadline=deadline,
            deadline_has_time=has_time,
            links=links,
            snippet=make_snippet(body),
            is_new=mail.date >= self.new_since,
        )
