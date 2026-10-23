"""Test/demo için sahte .eml dosyaları üretir (gerçek kişi/veri içermez).

Çalıştır:  python tests/make_samples.py
Demo "şu an"ı: 2026-10-23 20:00 (İstanbul)
"""
from email.message import EmailMessage
from email.utils import format_datetime
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Istanbul")
OUT = Path(__file__).parent / "sample_mails"

SAMPLES = [
    dict(
        name="01_coe203_proje",
        frm='"Dr. Ayşe Yılmaz" <ayse.yilmaz@istinye.edu.tr>',
        subject="COE203 - Proje 1 Teslim Tarihi",
        date=datetime(2026, 10, 23, 14, 5, tzinfo=TZ),
        text=(
            "Sevgili öğrenciler,\n\n"
            "Proje 1 raporlarınızı 30 Ekim 2026 saat 23:59'a kadar Moodle üzerinden yüklemeniz gerekmektedir. "
            "Gecikmeli teslimler kabul edilmeyecektir. Grup üyelerinin isimlerini raporun ilk sayfasına yazmayı unutmayın.\n\n"
            "Yükleme linki: https://moodle.istinye.edu.tr/mod/assign/view.php?id=4821\n\n"
            "Saygılarımla,\n"
            "Dr. Ayşe Yılmaz\n"
            "Bilgisayar Mühendisliği Bölümü\n"
            "Tel: 0212 000 00 00\n\n"
            "YASAL UYARI: Bu e-posta ve ekleri gizli bilgi içerebilir..."
        ),
    ),
    dict(
        name="02_math101_quiz_html",
        frm='"MATH101 Asistan" <math.asistan@istinye.edu.tr>',
        subject="Quiz 2 hakkında",
        date=datetime(2026, 10, 23, 16, 40, tzinfo=TZ),
        html=(
            "<html><body><p>Merhaba,</p>"
            "<p><b>MATH 101</b> Quiz 2 <b>haftaya Salı saat 10:00</b>'da B-204 sınıfında yapılacaktır. "
            "Konular: limit ve süreklilik. Hesap makinesi kullanılamaz.</p>"
            "<p>Sorularınız için ofis saatlerime gelebilirsiniz.</p>"
            "<p>İyi çalışmalar</p><p>Arş. Gör. Mert Kaya</p></body></html>"
        ),
    ),
    dict(
        name="03_ogrenci_isleri_iptal",
        frm='"Öğrenci İşleri" <ogrenciisleri@istinye.edu.tr>',
        subject="Duyuru: 29 Ekim Cumhuriyet Bayramı",
        date=datetime(2026, 10, 21, 9, 15, tzinfo=TZ),
        text=(
            "Değerli öğrencilerimiz,\n\n"
            "28 Ekim Çarşamba öğleden sonra ve 29 Ekim Perşembe günü tüm dersler iptal edilmiştir. "
            "Telafi programı bölümler tarafından ayrıca duyurulacaktır.\n\n"
            "Öğrenci İşleri Daire Başkanlığı"
        ),
    ),
    dict(
        name="04_gdg_toplanti",
        frm='"Buse" <buse.ornek@gmail.com>',
        subject="GDG çekirdek ekip toplantısı",
        date=datetime(2026, 10, 23, 18, 2, tzinfo=TZ),
        text=(
            "Selam ekip!\n\n"
            "Yarın 19:00'da Hackfest hazırlıkları için kısa bir toplantı yapalım. "
            "Gündem: sponsor listesi, afiş taslağı ve görev dağılımı.\n"
            "Link: https://meet.google.com/abc-defg-hij\n\n"
            "Katılım durumunuzu bu maile yanıt vererek bildirir misiniz?\n\n"
            "--\nBuse\nGDG on Campus İstinye"
        ),
    ),
    dict(
        name="05_sks_izin_yazisi",
        frm='"SKS Daire Başkanlığı" <sks@istinye.edu.tr>',
        subject="Etkinlik izin yazısı hk.",
        date=datetime(2026, 10, 22, 11, 30, tzinfo=TZ),
        text=(
            "Merhaba,\n\n"
            "Kulübünüzün 6 Kasım tarihli etkinliği için izin yazısının danışman hocanız tarafından imzalanıp "
            "en geç 31.10.2026 tarihine kadar ofisimize iletilmesi gerekmektedir. "
            "Etkinlik formunu da doldurmanızı rica ederiz: https://forms.gle/ExampleForm123\n\n"
            "Saygılarımızla,\nSKS"
        ),
    ),
    dict(
        name="06_foto_stant",
        frm='"Fotoğrafçılık Kulübü" <fotokulup.ornek@gmail.com>',
        subject="Cumartesi tanıtım standı",
        date=datetime(2026, 10, 23, 12, 0, tzinfo=TZ),
        text=(
            "Merhaba arkadaşlar,\n\n"
            "Fotoğrafçılık kulübü olarak Cumartesi günü saat 11:00-15:00 arası Vadi kampüsünde tanıtım standı açıyoruz. "
            "Gönüllü olmak isteyenler bu maile yanıt versin.\n\n"
            "> Önceki mesaj: geçen hafta stant için malzeme listesi paylaşmıştık\n"
            "> Lütfen getirin\n"
        ),
    ),
    dict(
        name="07_promo",
        frm='"Kampanya" <newsletter@shop.example.com>',
        subject="Öğrencilere özel indirim kampanyası!",
        date=datetime(2026, 10, 23, 10, 0, tzinfo=TZ),
        text="Sınav haftasına özel %50 indirim! https://shop.example.com/track/123",
    ),
    dict(
        name="08_arkadas",
        frm='"Can" <can.ornek@gmail.com>',
        subject="akşam maç var mı",
        date=datetime(2026, 10, 23, 17, 0, tzinfo=TZ),
        text="Kanka akşam halı saha var gelir misin?",
    ),
    dict(
        name="09_eski_odev_gecmis",
        frm='"Dr. Ali Demir" <ali.demir@istinye.edu.tr>',
        subject="PHYS102 Lab raporu",
        date=datetime(2026, 10, 15, 9, 0, tzinfo=TZ),
        text="Lab 3 raporlarınızı 20 Ekim 2026 23:59'a kadar teslim ediniz.",
    ),
    dict(
        name="10_vize_ertelendi",
        frm='"Dr. Ayşe Yılmaz" <ayse.yilmaz@istinye.edu.tr>',
        subject="COE203 vize tarihi değişikliği",
        date=datetime(2026, 10, 23, 15, 20, tzinfo=TZ),
        text=(
            "Merhaba,\n\n10 Kasım'da yapılması planlanan COE203 vize sınavı 17 Kasım 2026 saat 13:30'a ertelenmiştir. "
            "Sınav yeri değişmemiştir (A-101).\n\nİyi çalışmalar"
        ),
    ),
]


BULK = [
    dict(
        name="11_toplu_bulten",
        frm='"KU Announcements" <announcements@ku.edu.tr>',
        subject="KUDaily [Student]",
        date=datetime(2026, 10, 23, 9, 0, tzinfo=TZ),
        text="Bugün kampüste: Bilim Kafe buluşması saat 14.00'te. Yarın proje fuarı var. Etkinliklere herkes davetli.",
    ),
    dict(
        name="12_toplu_ders_duyurusu",
        frm='"Registrar" <registrar@ku.edu.tr>',
        subject="Final sınav programı yayınlandı",
        date=datetime(2026, 10, 23, 11, 0, tzinfo=TZ),
        text="Final sınav programı öğrenci sistemine yüklenmiştir. Son itiraz tarihi 30.10.2026.",
    ),
]


def _calendar_invite():
    m = EmailMessage()
    m.set_content("Dr. Ayşe Yılmaz sizi bir toplantıya davet etti.\nCOMP 132 proje görüşmesi için takvim davetini kabul edin.")
    ics = ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nMETHOD:REQUEST\r\nBEGIN:VEVENT\r\n"
           "DTSTART;TZID=Europe/Istanbul:20261028T153000\r\nDTEND;TZID=Europe/Istanbul:20261028T160000\r\n"
           "SUMMARY:COMP 132 proje görüşmesi\r\nLOCATION:Ofis B-312\\, Mühendislik\r\n"
           "END:VEVENT\r\nEND:VCALENDAR\r\n")
    m.add_attachment(ics.encode(), maintype="text", subtype="calendar", filename="invite.ics")
    return m


def _forwarded():
    inner = EmailMessage()
    inner["From"] = "Dr. Ali Demir <ali.demir@istinye.edu.tr>"
    inner["Subject"] = "PHYS102 Ödev 3"
    inner["Date"] = format_datetime(datetime(2026, 10, 22, 10, 0, tzinfo=TZ))
    inner.set_content("PHYS102 Ödev 3 son teslim tarihi 2 Kasım 2026 saat 23:59'dur. Moodle'a yükleyiniz.")
    m = EmailMessage()
    m.set_content("Bilginize.")
    m.add_attachment(inner)                    # message/rfc822 olarak iletilmiş mail
    return m


def _win1254_qp():
    m = EmailMessage()
    m.set_content("Değerli öğrenciler,\nMATH101 vize notları açıklandı. İtiraz için son gün 27 Ekim Salı saat 17:00.\n",
                  charset="windows-1254", cte="quoted-printable")
    return m


def _hidden_preheader_html():
    html = ("<html><head><style>p{margin:0}</style></head><body>"
            "<div style='display:none;max-height:0;overflow:hidden'>Bu metin önizleme için gizli 30 Aralık</div>"
            "<table><tr><td><h2>GDG Haftalık Bülten</h2></td></tr>"
            "<tr><td>Workshop</td><td>Flutter'a Giriş</td></tr>"
            "<tr><td>Tarih</td><td>29 Ekim 2026, 18:00</td></tr></table>"
            "<p>Kayıt: <a href='https://forms.gle/AbcDef'>form</a></p></body></html>")
    m = EmailMessage()
    m.set_content(html, subtype="html", cte="base64")
    return m


def _attachment_only():
    m = EmailMessage()
    m.add_attachment(b"%PDF-1.4 sahte", maintype="application", subtype="pdf", filename="COE203_odev2.pdf")
    return m


def _outlook_html():
    url = ("https://eur01.safelinks.protection.outlook.com/?url=https%3A%2F%2Fteams.microsoft.com%2Fl%2Fmeetup-join%2F19abc"
           "&data=05%7C01")
    m = EmailMessage()
    m.set_content(f"<p>Sevgili öğrenciler,</p><p>Yarın 10:00'daki COE203 dersi online yapılacaktır.</p>"
                  f"<p><a href='{url}'>Toplantıya katıl</a></p>", subtype="html")
    return m


TYPED = [
    ("13_takvim_daveti", '"Dr. Ayşe Yılmaz" <ayse.yilmaz@istinye.edu.tr>', "Davet: COMP 132 proje görüşmesi",
     datetime(2026, 10, 23, 13, 0, tzinfo=TZ), _calendar_invite),
    ("14_iletilen_mail", '"Can" <can.ornek@istinye.edu.tr>', "Fwd: PHYS102 Ödev 3",
     datetime(2026, 10, 23, 12, 30, tzinfo=TZ), _forwarded),
    ("15_win1254_qp", '"MATH101 Asistan" <math.asistan@istinye.edu.tr>', "Vize notları",
     datetime(2026, 10, 23, 15, 0, tzinfo=TZ), _win1254_qp),
    ("16_gizli_onizleme_bulten", '"GDG" <gdg.ornek@gmail.com>', "GDG haftalık bülten",
     datetime(2026, 10, 23, 16, 0, tzinfo=TZ), _hidden_preheader_html),
    ("17_sadece_ek", '"Dr. Ayşe Yılmaz" <ayse.yilmaz@istinye.edu.tr>', "COE203 Ödev 2",
     datetime(2026, 10, 23, 17, 30, tzinfo=TZ), _attachment_only),
    ("18_tekrar_yanit", '"Dr. Ayşe Yılmaz" <ayse.yilmaz@istinye.edu.tr>', "RE: COE203 - Proje 1 Teslim Tarihi",
     datetime(2026, 10, 23, 18, 30, tzinfo=TZ),
     lambda: _plain("Hatırlatma: Proje 1 teslimi 30 Ekim 2026 saat 23:59. Soru olursa yazın.")),
    ("19_outlook_teams", '"Dr. Ali Demir" <ali.demir@istinye.edu.tr>', "COE203 online ders",
     datetime(2026, 10, 23, 19, 0, tzinfo=TZ), _outlook_html),
]


def _plain(text):
    m = EmailMessage()
    m.set_content(text)
    return m


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.eml"):
        old.unlink()
    for s in SAMPLES + BULK:
        msg = EmailMessage()
        msg["From"] = s["frm"]
        msg["To"] = "ogrenci@example.com"
        msg["Subject"] = s["subject"]
        msg["Date"] = format_datetime(s["date"])
        if s in BULK:
            msg["List-Id"] = "<duyuru.ku.edu.tr>"          # posta listesi maili
        if "html" in s:
            msg.set_content("HTML destekli bir istemci kullanın.")
            msg.add_alternative(s["html"], subtype="html")
            # düz metin kısmı anlamsız; HTML'in kullanılmasını test etmek için onu sil
            msg = _html_only(msg, s)
        else:
            msg.set_content(s["text"])
        (OUT / f"{s['name']}.eml").write_bytes(bytes(msg))
    for name, frm, subject, date, build in TYPED:
        msg = build()
        msg["From"] = frm
        msg["To"] = "ogrenci@example.com"
        msg["Subject"] = subject
        msg["Date"] = format_datetime(date)
        (OUT / f"{name}.eml").write_bytes(bytes(msg))
    print(f"{len(SAMPLES) + len(BULK) + len(TYPED)} örnek mail üretildi → {OUT}")


def _html_only(_msg, s):
    m = EmailMessage()
    for h in ("From", "To", "Subject", "Date"):
        m[h] = _msg[h]
    m.set_content(s["html"], subtype="html")
    return m


if __name__ == "__main__":
    main()
