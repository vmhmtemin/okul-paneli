"""Veri modelleri: ham mail ve analiz edilmiş mail."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime

# Sistemin kendi gönderdiği özet maillerinin konu başı (tekrar taranmasın diye)
SUMMARY_SUBJECT_PREFIX = "📚 Okul Paneli:"


@dataclass
class Mail:
    """Kutudan okunmuş, metne çevrilmiş tek bir e-posta."""
    uid: str
    sender_name: str
    sender_email: str
    subject: str
    date: datetime          # saat dilimi bilgili (aware) datetime
    body: str               # düz metin gövde (imza temizlenmeden önce)


@dataclass
class Link:
    url: str
    label: str              # "Zoom", "Google Meet", "Teams" veya "Bağlantı"


@dataclass
class AnalyzedMail:
    """Kurallarla sınıflandırılmış mail."""
    mail: Mail
    category: str                       # "academic" | "club"
    group: str                          # kart başlığı: ders kodu / kulüp adı
    kinds: list[str]                    # "assignment", "exam", "meeting", "followup", "cancel"
    deadline: datetime | None           # metinde bulunan en yakın gelecek tarih
    deadline_has_time: bool             # tarih saat içeriyor mu?
    links: list[Link] = field(default_factory=list)
    snippet: str = ""                   # imzası temizlenmiş kısa özet
    is_new: bool = False                # son taramadan beri mi geldi?

    @property
    def item_id(self) -> str:
        """Checkbox durumunu tarayıcıda saklamak için sabit kimlik."""
        # hash() her çalıştırmada değişir; sabit kimlik için sha1 kullanıyoruz.
        key = f"{self.mail.sender_email}|{self.mail.subject}|{self.mail.date.isoformat()}"
        return "m" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
