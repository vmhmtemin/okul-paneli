"""Paneli gerçek bir tarayıcıda telefon genişliklerinde test eder.

Kontroller:
  1. Yatay taşma yok (sayfa genişliği ≤ ekran genişliği)
  2. Tüm checkbox satırları, butonlar ve linkler en az 44×44px dokunma alanına sahip
  3. Checkbox işaretlenince durum sayfa yenilense de korunuyor
Ekran görüntüleri: tests/screens/

Kullanım:  python tests/check_mobile.py site/index.html [--password ŞİFRE]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

WIDTHS = [360, 390, 430]
MIN_TARGET = 44

MEASURE_JS = """
(min) => {
  const doc = document.documentElement;
  const overflow = doc.scrollWidth - doc.clientWidth;
  const wide = [...document.querySelectorAll('body *')]
    .filter(el => el.getBoundingClientRect().right > doc.clientWidth + 1)
    .slice(0, 5).map(el => el.tagName + '.' + el.className);
  // Dokunma hedefi: checkbox'ın dokunma alanı onu saran <label>'dır
  const targets = [...document.querySelectorAll('a, button, .todo label')];
  const small = targets.map(el => {
    const r = el.getBoundingClientRect();
    return {name: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 40),
            w: Math.round(r.width), h: Math.round(r.height)};
  }).filter(t => t.w > 0 && (t.w < min || t.h < min));
  return {overflow, wide, count: targets.length, small};
}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("page", type=Path)
    ap.add_argument("--password", help="StatiCrypt şifreli sayfa için")
    args = ap.parse_args()
    url = args.page.resolve().as_uri()
    shots = Path(__file__).parent / "screens"
    shots.mkdir(exist_ok=True)

    failures = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w in WIDTHS:
            ctx = browser.new_context(viewport={"width": w, "height": 800}, device_scale_factor=2,
                                      is_mobile=True, has_touch=True)
            page = ctx.new_page()
            page.goto(url)
            if args.password:
                # Şifre ekranının da mobilde taşmadığını kontrol et
                login = page.evaluate(MEASURE_JS, MIN_TARGET)
                print(f"\n[{w}px] şifre ekranı taşma: {'YOK ✓' if login['overflow'] <= 0 else 'VAR ✗'}")
                failures += login["overflow"] > 0
                page.screenshot(path=str(shots / f"sifre_{w}.png"))
                page.fill("#staticrypt-password", args.password)
                if page.locator("#staticrypt-remember").count():
                    page.check("#staticrypt-remember")     # yenilemede tekrar sormasın
                page.click("#staticrypt-form button[type=submit], #staticrypt-form input[type=submit]")
                page.wait_for_selector("#todo-list", timeout=10000)
                print(f"[{w}px] doğru şifreyle panel açıldı ✓")
            page.wait_for_timeout(300)

            m = page.evaluate(MEASURE_JS, MIN_TARGET)
            ok_overflow = m["overflow"] <= 0
            ok_targets = not m["small"]
            print(f"\n[{w}px] yatay taşma: {'YOK ✓' if ok_overflow else str(m['overflow']) + 'px ✗ ' + str(m['wide'])}")
            print(f"[{w}px] dokunma hedefi: {m['count']} öğe, 44px altı: "
                  f"{'YOK ✓' if ok_targets else m['small']}")
            failures += (not ok_overflow) + (not ok_targets)

            # Checkbox durumu yenilemeden sonra korunuyor mu?
            first = page.locator(".check").first
            if first.count():
                page.locator(".todo label").first.click()
                page.reload()
                if args.password:
                    page.wait_for_selector("#todo-list", timeout=10000)
                kept = page.locator(".check").first.is_checked()
                print(f"[{w}px] işaret yenileme sonrası korunuyor: {'EVET ✓' if kept else 'HAYIR ✗'}")
                failures += not kept
                page.locator(".todo label").first.click()          # geri al
                page.wait_for_timeout(100)

            page.screenshot(path=str(shots / f"panel_{w}.png"), full_page=True)
            page.screenshot(path=str(shots / f"panel_{w}_ilk_ekran.png"))
            ctx.close()
        browser.close()

    print("\nSONUÇ:", "TÜM KONTROLLER GEÇTİ ✓" if failures == 0 else f"{failures} kontrol başarısız ✗")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
