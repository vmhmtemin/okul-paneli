# 📚 Okul Paneli — Gmail'den otomatik ders & kulüp özeti

Her gün **08:00 ve 20:00**'de (İstanbul) Gmail gelen kutunu tarar.
Ders ve kulüp maillerini **yapay zeka kullanmadan, kurallarla** ayıklar ve iki şey yapar:

1. **Şifreli bir web paneli** yayınlar (GitHub Pages). Telefonda açınca özet, yapılacaklar listesi ve ders/kulüp kartları görünür.
2. Yeni ilgili mail varsa sana **kısa bir özet e-postası** atar. Gmail bildirimin açıksa telefona bildirim olarak düşer.

Mail şifren GitHub'ın şifreli **Secrets** kasasında durur. Kodda veya panelde görünmez. Panel herkese açık bir adreste yayınlansa da içeriği şifrelidir, şifreyi bilmeyen hiçbir şey göremez.

---

## Kurulum (yaklaşık 15 dakika, bir kere yapılır)

### 1) Gmail "Uygulama Şifresi" oluştur
Normal Gmail şifren **kullanılmaz**. Sadece bu sistem için ayrı bir şifre oluşturacaksın:

1. Google hesabında **2 Adımlı Doğrulama** açık olmalı: <https://myaccount.google.com/security>
2. <https://myaccount.google.com/apppasswords> adresine git → ad olarak `Okul Paneli` yaz → **Oluştur**.
3. Çıkan **16 harfli şifreyi** bir yere not et. Sadece bir kez gösterilir.

> **"Bu ayar kullanılamıyor" diyorsa** (okul hesaplarında, ör. `@ku.edu.tr`, okul bunu kapatmış olabilir):
> 1. Okul Gmail'inde **Ayarlar → Tüm ayarları gör → Yönlendirme ve POP/IMAP → Yönlendirme adresi ekle** → kişisel Gmail adresini yaz, kişisel Gmail'e gelen onay kodunu gir, "Gelen postanın bir kopyasını … adresine yönlendir" seçip **Kaydet**.
> 2. Uygulama şifresini **kişisel Gmail** hesabında oluştur ve sistemde kişisel Gmail'i kullan. Yönlendirilen maillerde gönderen (hoca, `@ku.edu.tr`) korunduğu için sınıflandırma aynen çalışır.
> 3. Yönlendirme seçeneği de kapalıysa bu yöntem çalışmaz; o durumda haber ver.
> İstediğin zaman aynı sayfadan uygulama şifresini silip sistemin erişimini kesebilirsin.

### 2) GitHub deposunu oluştur
1. <https://github.com/new> → isim: `okul-paneli` → **Public** seç → **Create repository**.
   (Ücretsiz hesapta GitHub Pages için depo Public olmalı. Depoda sadece kod var, hiçbir mail verisi yok.)
2. **Add file → Upload files** ile bu klasördeki tüm dosyaları yükle (`.github` klasörü dahil).

### 3) Secrets'ları gir
Depo → **Settings → Secrets and variables → Actions → New repository secret**:

| Ad | Değer |
|---|---|
| `GMAIL_USER` | Gmail adresin (örn. `adin@gmail.com`) |
| `GMAIL_APP_PASSWORD` | 1. adımdaki 16 harfli şifre (boşluklar önemsiz) |
| `PANEL_PASSWORD` | Paneli açarken gireceğin şifre (uzun bir şey seç) |
| `STATICRYPT_SALT` | 32 karakterlik rastgele kod, aşağıdaki gibi üret |
| `NOTIFY_TO` | *(isteğe bağlı)* Özet mailinin gideceği başka bir adres |

`STATICRYPT_SALT` üretmek için bilgisayarında şunu çalıştır ve çıkan satırı yapıştır:
```bash
python3 -c "import secrets; print(secrets.token_hex(16))"
```
Bu değer sabit kaldığı sürece telefon şifreni 30 gün hatırlar. Değiştirirsen tekrar sorar.

### 4) GitHub Pages'i aç
Depo → **Settings → Pages → Build and deployment → Source: GitHub Actions**.

### 5) İlk çalıştırma
Depo → **Actions** sekmesi → (istenirse "I understand… enable" de) → **Okul Paneli** → **Run workflow**.
Yaklaşık 1 dakika sonra yeşil ✓ görünür. Panelin adresi:

```
https://KULLANICI-ADIN.github.io/okul-paneli/
```

### 6) Telefonda
- Linki aç → şifreyi gir → **Bu cihazda hatırla**'yı işaretle.
- Safari'de **Paylaş → Ana Ekrana Ekle**, Chrome'da **⋮ → Ana ekrana ekle** dersen uygulama gibi açılır.
- Gmail uygulamasında bildirimlerin açık olsun.
  - Kendine gönderilen maillerde bildirim gelmezse `NOTIFY_TO` Secret'ına başka bir adresini yaz.

---

## Görev ekleme, takvim ve cihazlar arası senkron (isteğe bağlı)

Panelde **＋ Görev ekle** ile kendi görevlerini (başlık, tarih, saat, not) ekleyebilir; **Takvim**'de mail teslimleri ve kendi görevlerin günlerin üstünde renkli noktalarla görünür. Bir güne dokununca o günün listesi açılır.

Görevlerin telefon ve bilgisayarda **aynı** görünmesi için ücretsiz bir Supabase veritabanı kullanılır:

1. Supabase'de bir proje aç, **SQL Editor**'e `supabase/schema.sql` dosyasının içeriğini yapıştırıp **Run** de.
2. GitHub'a 3 Secret daha ekle:

| Ad | Değer |
|---|---|
| `SUPABASE_URL` | Proje adresi (örn. `https://xxxx.supabase.co`) |
| `SUPABASE_KEY` | **Project Settings → API Keys**'teki `sb_publishable_...` anahtarı |
| `SYNC_KEY` | 64 karakterlik rastgele kod: `python3 -c "import secrets; print(secrets.token_hex(32))"` |

Güvenlik: Veritabanı tablolarına doğrudan erişim kapalıdır; sayfa sadece `SYNC_KEY`'i bilen 4 fonksiyonu çağırabilir. `SYNC_KEY` sadece şifreli panelin içinde durur.
Bu Secret'lar yoksa görev ekleme yine çalışır, sadece görevler eklendiği cihazda saklanır.
İnternet yokken eklenen görevler cihazda bekler, bağlantı gelince otomatik gönderilir.

## Kendi okuluna / kulüplerine göre ayarla: `config.yaml`

- `academic.sender_domains`: hoca ve bölüm maillerinin alan adı (Koç için hazır: `ku.edu.tr`)
- `academic.keywords`: konu satırında geçince akademik sayılacak kelimeler
- `clubs`: **kendi kulüplerini yaz** — her kulüp için ad + o kulübü tanıtan kelimeler / gönderen adresleri (şu an örnek değerler var)
- `ignore`: reklam vb. yok sayılacak gönderen ve konu kelimeleri
- `lookback_days`: yapılacaklar listesi kaç günlük maillerden oluşsun (varsayılan 14)

Değişikliği GitHub'da dosyayı düzenleyip kaydederek yapabilirsin. Bir sonraki taramada uygulanır.

## Nasıl çalışıyor?

| Adım | Dosya | Ne yapar |
|---|---|---|
| Oku | `mail_panel/fetch.py` | Gmail'e IMAP ile **salt-okunur** bağlanır. Mailleri "okundu" yapmaz. |
| Temizle | `mail_panel/textutil.py` | HTML'i metne çevirir. İmza, yasal uyarı ve alıntılanmış eski mesajları atar. Zoom/Meet/Form linklerini bulur. |
| Tarih | `mail_panel/dates.py` | "25 Ekim'e kadar", "haftaya Salı 10:00", "yarın 14:30", "30.10.2026" gibi ifadeleri gerçek tarihe çevirir. Erteleme maillerinde yeni tarihi seçer. |
| Sınıflandır | `mail_panel/classify.py` | Gönderen ve anahtar kelimelere göre Akademik / Kulüp ayırır. Ders kodunu (COE203) bulur. Türü belirler: Ödev, Sınav, Toplantı, Yanıt/Takip, İptal. |
| Raporla | `mail_panel/report.py` | Özet cümleleri yazar. Yapılacakları aciliyete göre sıralar (48 saat / bu hafta / sonra / tarihsiz), süresi geçenleri gizler. |
| Göster | `templates/panel.html.j2` | Mobil öncelikli panel. İşaretlenen kutular telefonda hatırlanır. |
| Bildir | `mail_panel/notify.py` | Kendi adresine kısa özet e-postası gönderir. |

**Sınırlar (yapay zeka olmadığı için):**
- Mailleri gerçekten özetlemez, mailin ilk birkaç cümlesini gösterir.
- Tarih ve kelime kurallarına uymayan çok serbest yazılmış mailleri yanlış sınıflandırabilir. Kuralları `config.yaml`'dan genişletebilirsin.
- GitHub zamanlanmış görevleri bazen 5-30 dakika gecikmeli çalıştırır.

## Bilgisayarda deneme (şifre gerekmez)
```bash
pip install -r requirements.txt
python tests/make_samples.py                                   # sahte örnek mailler
python main.py --source eml --config tests/test_config.yaml --now 2026-10-23T20:00   # → site/index.html
python -m pytest -q tests/test_core.py                         # birim testleri
pip install playwright && python tests/check_mobile.py site/index.html   # 360/390/430px testi
SUPABASE_URL=https://example.supabase.co SUPABASE_KEY=x SYNC_KEY=$(python3 -c "import secrets;print(secrets.token_hex(32))") \
  python main.py --source eml --config tests/test_config.yaml && python tests/check_tasks.py site/index.html   # görev/senkron testi
```

## Sistemi durdurmak
- Geçici: **Actions → Okul Paneli → ⋯ → Disable workflow**
- Tamamen: Google'da uygulama şifresini sil (<https://myaccount.google.com/apppasswords>) ve depoyu sil.
