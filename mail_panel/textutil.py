"""Metin yardımcıları: HTML → düz metin, imza / alıntı temizleme, link çıkarma."""
from __future__ import annotations

import html
import re
from html.parser import HTMLParser

from .models import Link


# ---------------------------------------------------------------- HTML → metin
class _TextExtractor(HTMLParser):
    """HTML → okunabilir düz metin (ek kütüphane gerektirmez).

    - <style>/<script> ve GİZLİ öğeler (display:none, mso-hide, hidden) atlanır;
      bültenlerdeki görünmez "önizleme metni" bu sayede metne karışmaz.
    - Tablo hücreleri " · " ile, liste öğeleri "• " ile ayrılır.
    - Linklerin gerçek adresi metnin yanına eklenir (buton yapmak için).
    """

    _BLOCK = {"p", "div", "br", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "table", "ul", "ol",
              "section", "article", "header", "footer", "blockquote", "pre", "hr", "center"}
    _SKIP = {"style", "script", "head", "title", "noscript", "template"}
    _VOID = {"br", "img", "hr", "meta", "link", "input", "col", "area", "base", "wbr", "source"}
    _HIDDEN_RX = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden|mso-hide\s*:\s*all|max-height\s*:\s*0", re.I)

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._stack: list[tuple[str, bool]] = []      # (etiket, gizli mi)
        self._hidden = 0

    def _is_hidden(self, tag, attrs) -> bool:
        a = dict(attrs)
        return (tag in self._SKIP or "hidden" in a or a.get("aria-hidden") == "true"
                or bool(self._HIDDEN_RX.search(a.get("style") or "")))

    def handle_starttag(self, tag, attrs):
        hidden = self._is_hidden(tag, attrs)
        if tag not in self._VOID:
            self._stack.append((tag, hidden))
            if hidden:
                self._hidden += 1
        if self._hidden or hidden:
            return
        if tag in self._BLOCK:
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n• ")
        elif tag in ("td", "th"):
            self.parts.append(" · ")
        elif tag == "img":
            alt = (dict(attrs).get("alt") or "").strip()
            if alt and len(alt) < 80:
                self.parts.append(f" {alt} ")
        if tag == "a":
            href = unwrap_redirect(dict(attrs).get("href") or "")
            if href.startswith("http"):
                self.parts.append(f" {href} ")

    def handle_endtag(self, tag):
        # Kapanış etiketini yığında bul (bozuk HTML'e dayanıklı)
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                for _, h in self._stack[i:]:
                    if h:
                        self._hidden -= 1
                del self._stack[i:]
                break
        if not self._hidden and tag in self._BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._hidden:
            self.parts.append(data)


def html_to_text(raw_html: str) -> str:
    parser = _TextExtractor()
    parser.feed(raw_html)
    parser.close()
    text = html.unescape("".join(parser.parts))
    # görünmez dolgu karakterleri (bültenlerde önizleme metnini gizlemek için kullanılır)
    text = re.sub("[\u200b\u200c\u200d\u034f\u00ad\ufeff]", "", text)
    text = re.sub("[ \t\u00a0]+", " ", text)
    text = "\n".join(line.strip(" ·") for line in text.split("\n"))   # satır başı/sonu hücre ayıraçları
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
def unwrap_redirect(url: str) -> str:
    """Google / Outlook / LinkedIn yönlendirme linklerinin içindeki gerçek adresi çıkar."""
    from urllib.parse import parse_qs, unquote, urlparse
    try:
        u = urlparse(url)
    except ValueError:
        return url
    host = (u.netloc or "").lower()
    q = parse_qs(u.query)
    if host.endswith("safelinks.protection.outlook.com") and "url" in q:
        return unquote(q["url"][0])
    if host in ("www.google.com", "google.com") and u.path == "/url":
        return unquote((q.get("q") or q.get("url") or [url])[0])
    return url


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
        url = unwrap_redirect(match.group(0).rstrip(".,;:"))
        if url in seen or _LINK_IGNORE.search(url):
            continue
        seen.add(url)
        label = next((lbl for rx, lbl in _LINK_LABELS if rx.search(url)), "Bağlantı")
        links.append(Link(url=url, label=label))
    # Toplantı linkleri önce gelsin
    priority = {"Zoom": 0, "Google Meet": 0, "Teams": 0, "Form": 1, "Ders Sistemi": 1}
    links.sort(key=lambda l: priority.get(l.label, 2))
    return links[:limit]
