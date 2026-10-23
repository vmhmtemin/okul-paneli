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
    print(f"{len(SAMPLES) + len(BULK)} örnek mail üretildi → {OUT}")


def _html_only(_msg, s):
    m = EmailMessage()
    for h in ("From", "To", "Subject", "Date"):
        m[h] = _msg[h]
    m.set_content(s["html"], subtype="html")
    return m


if __name__ == "__main__":
    main()
