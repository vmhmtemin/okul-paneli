"""Görev ekleme / senkron / takvim testini sahte bir Supabase sunucusuyla yapar.

İki ayrı "cihaz" (tarayıcı bağlamı) aynı sahte sunucuya bağlanır:
  1. A cihazında görev eklenir → B cihazında görünür
  2. B'de mail işi "bitti" işaretlenir → A'da da bitti görünür
  3. Görev düzenlenir, takvimde doğru günde görünür
  4. Sunucu çökükken eklenen görev cihazda bekler, sunucu dönünce gönderilir
  5. Görev silinir
Kullanım:  python tests/check_tasks.py site/index.html
(site/index.html, SUPABASE_URL=https://example.supabase.co ile üretilmiş olmalı)
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

DB = {"tasks": {}, "mail_done": set(), "note": None, "down": False, "calls": 0}


def handle(route):
    req = route.request
    DB["calls"] += 1
    if DB["down"]:
        return route.fulfill(status=503, body="down")
    fn = req.url.rsplit("/", 1)[-1]
    body = json.loads(req.post_data or "{}")
    assert len(body.get("p_key", "")) >= 32, "sync key gönderilmedi"
    if fn == "panel_sync":
        out = {"tasks": list(DB["tasks"].values()), "mail_done": sorted(DB["mail_done"]), "note": DB["note"]}
        return route.fulfill(status=200, content_type="application/json", body=json.dumps(out))
    if fn == "panel_task_upsert":
        tid = body["p_id"] or str(uuid.uuid4())
        DB["tasks"][tid] = {"id": tid, "title": body["p_title"], "due_date": body["p_due_date"],
                            "due_time": body["p_due_time"], "note": body["p_note"], "done": body["p_done"]}
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"id": tid}))
    if fn == "panel_task_delete":
        DB["tasks"].pop(body["p_id"], None)
        return route.fulfill(status=204, body="")
    if fn == "panel_note_set":
        DB["note"] = body["p_body"]
        return route.fulfill(status=204, body="")
    if fn == "panel_mail_done_set":
        (DB["mail_done"].add if body["p_done"] else DB["mail_done"].discard)(body["p_item_id"])
        return route.fulfill(status=204, body="")
    return route.fulfill(status=404, body="?")


def check(cond, msg):
    print(("✓ " if cond else "✗ ") + msg)
    if not cond:
        check.failed += 1


check.failed = 0


def main() -> int:
    url = Path(sys.argv[1]).resolve().as_uri()
    target = (date.today() + timedelta(days=3)).isoformat()
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        def device():
            ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
            ctx.route("https://example.supabase.co/rest/v1/rpc/*", handle)
            page = ctx.new_page()
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url)
            page.wait_for_function("document.getElementById('sync-status').className.includes('ok')", timeout=5000)
            return page

        a, b = device(), device()
        check("Senkronize" in a.inner_text("#sync-status"), "Açılışta senkron durumu 'Senkronize'")

        # 1) A'da görev ekle
        a.click("#add-task")
        a.fill("#f-title", "Business Club sunum hazırlığı")
        a.fill("#f-date", target)
        a.fill("#f-time", "18:30")
        a.fill("#f-note", "slaytlar + bütçe")
        a.click("#f-save")
        a.wait_for_function("document.getElementById('sync-status').className.includes('ok')")
        check(any(t["title"] == "Business Club sunum hazırlığı" for t in DB["tasks"].values()), "Görev sunucuya kaydedildi")
        check("Business Club sunum hazırlığı" in a.inner_text("#todo-list"), "Görev A'nın listesinde")
        check("Business Club sunum hazırlığı" in a.inner_text("#cal-day"), "Takvim görevin gününe gitti ve görevi gösteriyor")
        check(a.locator(".cal-cell.selected .dot.own").count() == 1, "Takvim hücresinde mor 'kendi görevim' noktası var")

        # B yenilenince görür
        b.reload(); b.wait_for_function("document.getElementById('sync-status').className.includes('ok')")
        check("Business Club sunum hazırlığı" in b.inner_text("#todo-list"), "Görev B cihazında da görünüyor (senkron)")

        # 2) B'de mail işini bitti yap → A'da görünsün
        first_mail = b.locator(".todo:has(.tag:not(.own)) .check").first
        first_mail.check()
        b.wait_for_function("document.getElementById('sync-status').className.includes('ok')")
        a.reload(); a.wait_for_function("document.getElementById('sync-status').className.includes('ok')")
        check(a.locator(".todo.done").count() >= 1, "B'de bitirilen mail işi A'da da bitmiş görünüyor")

        # 3) Düzenle
        a.locator(".todo:has-text('Business Club sunum') .todo-open").click()
        check(a.input_value("#f-title") == "Business Club sunum hazırlığı", "Düzenle formu mevcut bilgilerle açıldı")
        a.fill("#f-title", "Business Club sunumu (güncel)")
        a.click("#f-save")
        a.wait_for_function("document.getElementById('sync-status').className.includes('ok')")
        check(any(t["title"] == "Business Club sunumu (güncel)" for t in DB["tasks"].values()), "Düzenleme sunucuya gitti")

        # Boş başlık doğrulaması
        a.click("#add-task"); a.fill("#f-title", "   "); a.click("#f-save")
        check("boş olamaz" in a.inner_text("#f-error"), "Boş başlık engellendi")
        a.click("#task-sheet .sheet-actions [data-close]")

        # 4) Çevrimdışı ekle → bekle → bağlanınca gönder
        DB["down"] = True
        a.click("#add-task"); a.fill("#f-title", "Çevrimdışı görev"); a.click("#f-save")
        a.wait_for_function("document.getElementById('sync-status').className.includes('offline')")
        check("Çevrimdışı görev" in a.inner_text("#todo-list"), "Sunucu kapalıyken görev cihazda görünüyor")
        check(not any(t["title"] == "Çevrimdışı görev" for t in DB["tasks"].values()), "…ve sunucuya henüz gitmedi")
        DB["down"] = False
        a.reload(); a.wait_for_function("document.getElementById('sync-status').className.includes('ok')")
        check(any(t["title"] == "Çevrimdışı görev" for t in DB["tasks"].values()), "Bağlantı dönünce bekleyen görev gönderildi")

        # 5) Sil (iki adımlı onay)
        a.locator(".todo:has-text('Çevrimdışı görev') .todo-open").click()
        a.click("#f-delete")
        check(a.inner_text("#f-delete") == "Emin misin? Sil", "Silme ikinci dokunuşta onay istiyor")
        a.click("#f-delete")
        a.wait_for_function("document.getElementById('sync-status').className.includes('ok')")
        check(not any(t["title"] == "Çevrimdışı görev" for t in DB["tasks"].values()), "Görev sunucudan silindi")

        # Takvim gezinme
        before = a.inner_text("#cal-title")
        a.click("#cal-next")
        check(a.inner_text("#cal-title") != before, "Takvimde sonraki aya geçildi")

        # 6) Not kağıdı
        check(a.inner_text(".note-title") == "kevaşe başkan", "Not kağıdının başlığı 'kevaşe başkan'")
        a.fill("#note", "yarın 9'da kütüphane")
        a.locator("#note").blur()
        a.wait_for_function("document.getElementById('note-status').textContent.includes('Kaydedildi')")
        check(DB["note"] == "yarın 9'da kütüphane", "Not sunucuya kaydedildi")
        b.reload(); b.wait_for_function("document.getElementById('sync-status').className.includes('ok')")
        check(b.input_value("#note") == "yarın 9'da kütüphane", "Not diğer cihazda da görünüyor")

        # 7) Mail okuma penceresi
        a.click("#cal-prev")
        row = a.locator(".mail-row").first
        subj = row.locator(".mail-subject").inner_text()
        row.click()
        a.wait_for_selector("#mail-viewer[open]")
        check(a.inner_text("#mv-subject") == subj, "Maile dokununca tam içerik penceresi açıldı")
        check(len(a.inner_text("#mv-body")) > 80, "Pencerede mail metni var")
        ov = a.evaluate("document.querySelector('#mail-viewer').scrollWidth <= document.querySelector('#mail-viewer').clientWidth + 1")
        check(ov, "Mail penceresi yatay taşmıyor")
        a.screenshot(path=str(Path(__file__).parent / "screens" / "mail_pencere_390.png"))
        a.click("#mail-viewer [data-close]")
        check(a.locator("#mail-viewer[open]").count() == 0, "Pencere kapat tuşuyla kapandı")

        # Takvim davetli mailde yer bilgisi
        a.locator(".mail-row:has-text('COMP 132 proje görüşmesi')").first.click()
        check("Ofis B-312" in a.inner_text("#mv-body"), "Takvim davetinin yeri gösteriliyor")
        a.click("#mail-viewer [data-close]")

        # 8) Filtre: sadece kulüpler
        a.click(".chip[data-filter='club']")
        groups = a.locator(".group-head .gname").all_inner_texts()
        check(groups and all(g.startswith("🎪") for g in groups), "Kulüp filtresinde sadece kulüp mailleri var")
        a.click(".chip[data-filter='all']")

        # 9) Kategori gizle
        a.click("#open-cats")
        a.locator(".cat-row:has-text('COE203') .check").uncheck()
        a.click("#cat-sheet [data-close]")
        check("COE203" not in " ".join(a.locator(".group-head .gname").all_inner_texts()), "Gizlenen kategori maillerden kalktı")
        check("COE203" not in a.inner_text("#todo-list"), "Gizlenen kategori yapılacaklardan kalktı")
        check("1 gizli" in a.inner_text("#open-cats"), "Kategoriler düğmesi gizli sayısını gösteriyor")
        a.click("#open-cats"); a.click("#cats-all"); a.click("#cat-sheet [data-close]")

        # 10) Bölüm küçültme
        a.click("[data-sec='cal'] .sec-head")
        check(not a.is_visible("#cal-grid"), "Takvim bölümü küçültüldü")
        a.reload(); a.wait_for_function("document.getElementById('sync-status').className.includes('ok')")
        check(not a.is_visible("#cal-grid"), "Küçültme yenilemeden sonra da hatırlandı")
        a.click("[data-sec='cal'] .sec-head")

        # 11) 360px'te pencereler taşmıyor
        a.set_viewport_size({"width": 360, "height": 740})
        a.click("#add-task")
        w = a.evaluate("[document.querySelector('#task-sheet').scrollWidth, document.querySelector('#task-sheet').clientWidth]")
        check(w[0] <= w[1] + 1, f"360px'te görev formu taşmıyor {w}")
        a.screenshot(path=str(Path(__file__).parent / "screens" / "gorev_formu_360.png"))
        a.click("#task-sheet .sheet-actions [data-close]")
        a.set_viewport_size({"width": 390, "height": 844})

        a.screenshot(path=str(Path(__file__).parent / "screens" / "gorevler_390.png"), full_page=True)
        browser.close()

    real_errors = [e for e in errors if "503" not in e and "Failed to load resource" not in e]
    check(not real_errors, f"Konsolda JavaScript hatası yok {real_errors[:3] if real_errors else ''}")
    print("\nSONUÇ:", "TÜM KONTROLLER GEÇTİ ✓" if check.failed == 0 else f"{check.failed} kontrol başarısız ✗")
    return 1 if check.failed else 0


if __name__ == "__main__":
    sys.exit(main())
