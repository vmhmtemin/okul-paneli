"""Metin yardımcıları: HTML → düz metin, imza / alıntı temizleme, link çıkarma."""
from __future__ import annotations

import html
import re
from html.parser import HTMLParser

from .models import Link


# ---------------------------------------------------------------- HTML → metin
class _TextExtractor(HTMLParser):
    """Basit HTML → metin dönüştürücü (ek kütüphane gerektirmez)."""

    _BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "table", "ul", "ol"}
    _SKIP = {"style", "script", "head", "title"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag in self._BLOCK:
            self.parts.append("\n")
        if tag == "a":
            # Link metni yerine href önemli olabilir; sonradan link çıkarmak için ekle
            href = dict(attrs).get("href")
            if href and href.startswith("http"):
                self.parts.append(f" {href} ")

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif tag in self._BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip_depth:
            self.parts.append(data)


def html_to_text(raw_html: str) -> str:
    parser = _TextExtractor()
    parser.feed(raw_html)
    text = html.unescape("".join(parser.parts))
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


# ------------------------------------------------------- alıntı / imza temizleme
# Bu satırlardan biri görülünce, o satır ve sonrası atılır.
_CUT_PATTERNS = [
    r"^-- ?$",                                         # standart imza ayırıcı
    r"^_{5,}$",                                        # Outlook çizgisi
    r"^On .+ wrote:$",                                 # İngilizce yanıt alıntısı
    r"^.+tarihinde .+ şunu yazdı:?$",                  # Türkçe Gmail alıntısı
    r"^.+ tarihinde .+ yazdı:?$",
    r"^(From|Kimden|Gönderen):\s",                     # iletilmiş mail başlığı
    r"^-{2,}\s*(Original Message|Orijinal İleti|Forwarded message|İletilen ileti)",
    r"^(Saygılarım\w*|Saygılar|Sevgiler|İyi çalışmalar\w*|Kolay gelsin)[,.!]?$",
    r"^(Best regards|Kind regards|Regards|Best|Cheers|Thanks|Thank you)[,.!]?$",
    r"^(Sent from|iPhone'umdan|Android'imden|Outlook for)",
    r"^(YASAL UYARI|Yasal Uyarı|DISCLAIMER|Disclaimer|CONFIDENTIALITY)",
    r"^Bu (e-posta|e-posta mesajı|ileti) ve (ekleri|ekindeki)",
    r"^This (e-mail|email|message) and any (attachments|files)",
]
_CUT_RE = re.compile("|".join(f"(?:{p})" for p in _CUT_PATTERNS), re.IGNORECASE)


def clean_body(text: str) -> str:
    """İmza, alıntılanmış eski mesaj ve yasal uyarıları kırp."""
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(">"):          # alıntı satırı
            continue
        if _CUT_RE.match(stripped):
            break
        kept.append(stripped)
    cleaned = "\n".join(kept)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def make_snippet(text: str, limit: int = 260) -> str:
    """Selamlama satırını atlayıp ilk birkaç cümleyi tek paragraf yap."""
    lines = [l for l in text.splitlines() if l.strip()]
    # "Merhaba," / "Sevgili öğrenciler," gibi tek başına selamlamaları atla
    greeting = re.compile(r"^(merhaba|selam|sevgili|değerli|sayın|hi|hello|dear)\b.{0,40}[,!:]?$", re.I)
    if lines and greeting.match(lines[0].strip()):
        lines = lines[1:]
    flat = re.sub(r"\s+", " ", " ".join(lines)).strip()
    flat = _URL_RE.sub("", flat)              # linkler ayrı buton olarak gösterilecek
    # Link silinince ortada kalan "Yükleme linki:" / "Link:" gibi etiketleri de at
    flat = re.sub(r"(?:[\wçğıöşüÇĞİÖŞÜ]+\s)?(?:linki|link|bağlantısı|bağlantı)\s*:\s*(?=\s|$)", "",
                  flat, flags=re.I)
    flat = re.sub(r"\s{2,}", " ", flat).strip()
    if len(flat) <= limit:
        return flat
    cut = flat[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:") + "…"


# ----------------------------------------------------------------- link çıkarma
_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)

_LINK_LABELS = [
    (re.compile(r"zoom\.us/", re.I), "Zoom"),
    (re.compile(r"meet\.google\.com/", re.I), "Google Meet"),
    (re.compile(r"teams\.(microsoft|live)\.com/", re.I), "Teams"),
    (re.compile(r"(forms\.gle/|docs\.google\.com/forms)", re.I), "Form"),
    (re.compile(r"(drive|docs)\.google\.com/", re.I), "Google Drive"),
    (re.compile(r"(kuhub|moodle|lms|uzem|blackboard|canvas)", re.I), "Ders Sistemi"),
]

# Panelde buton olarak gösterilmeye değmeyen linkler
_LINK_IGNORE = re.compile(r"(unsubscribe|abonelik|tracking|click\.|/track/|mailchimp|list-manage)", re.I)


def extract_links(text: str, limit: int = 4) -> list[Link]:
    seen: set[str] = set()
    links: list[Link] = []
    for match in _URL_RE.finditer(text):
        url = match.group(0).rstrip(".,;:")
        if url in seen or _LINK_IGNORE.search(url):
            continue
        seen.add(url)
        label = next((lbl for rx, lbl in _LINK_LABELS if rx.search(url)), "Bağlantı")
        links.append(Link(url=url, label=label))
    # Toplantı linkleri önce gelsin
    priority = {"Zoom": 0, "Google Meet": 0, "Teams": 0, "Form": 1, "Ders Sistemi": 1}
    links.sort(key=lambda l: priority.get(l.label, 2))
    return links[:limit]
