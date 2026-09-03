"""啟動本地伺服器並用 Playwright 驗證 index.html 篩選流程。"""
import http.server
import socketserver
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.resolve()
PORT = 8766


def serve():
    import os
    os.chdir(ROOT)
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    httpd.serve_forever()


def main() -> int:
    t = threading.Thread(target=serve, daemon=True)
    t.start()
    time.sleep(0.5)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="networkidle")

        # 1) 初始載入：6 部影片卡片
        page.wait_for_selector(".card")
        n0 = page.locator(".card").count()
        print(f"[init] cards = {n0}")
        assert n0 == 6, f"預期 6 張卡，實際 {n0}"

        meta = page.locator("#meta").inner_text()
        print(f"[meta] {meta}")
        assert "筆數 6" in meta

        # 截圖初始
        page.screenshot(path=str(ROOT / "_test_initial.png"), full_page=True)

        # 2) 篩選：主題 = 腳交
        page.select_option("#topic", "footjob")
        time.sleep(0.2)
        n1 = page.locator(".card").count()
        print(f"[topic=footjob] cards = {n1}")
        # 預期: b1(足コキ), b2(foot fetish), b3(足交/footjob) = 3
        assert n1 == 3, f"預期 3 張卡，實際 {n1}"

        # 3) 加最少觀看數 3000
        page.fill("#minViews", "3000")
        time.sleep(0.2)
        n2 = page.locator(".card").count()
        print(f"[topic=footjob & minViews=3000] cards = {n2}")
        # 預期: b1(3400), b2(2300 不過), b3(600 不過) = 1
        assert n2 == 1, f"預期 1 張卡，實際 {n2}"

        # 4) 重置 + 來源 = jable
        page.click("#resetBtn")
        time.sleep(0.2)
        page.select_option("#source", "jable")
        time.sleep(0.2)
        n3 = page.locator(".card").count()
        print(f"[source=jable] cards = {n3}")
        # 預期: a1, a2, a3 = 3
        assert n3 == 3, f"預期 3 張卡，實際 {n3}"

        # 5) 排序：觀看數高→低
        page.select_option("#sort", "views_desc")
        time.sleep(0.2)
        titles = page.locator(".card .card__title").all_inner_texts()
        print(f"[sort=views_desc] titles = {titles}")
        # 預期順序：12000(a1), 8000(a2), 4500(a3)
        assert titles[0].startswith("絲襪 OL"), f"排序錯誤，第一張={titles[0]}"
        assert "黒タイツ" in titles[1], f"排序錯誤，第二張={titles[1]}"

        # 6) 搜尋：標題含「古早」
        page.fill("#q", "古早")
        time.sleep(0.2)
        n4 = page.locator(".card").count()
        print(f"[q=古早] cards = {n4}")
        assert n4 == 1

        # 7) chips 快速標籤：點選「絲襪」
        page.click("#resetBtn")
        time.sleep(0.2)
        # 找 chips 內含「絲襪」字樣的按鈕
        chip = page.locator(".chip", has_text="絲襪").first
        chip.click()
        time.sleep(0.2)
        n5 = page.locator(".card").count()
        print(f"[chip=絲襪] cards = {n5}")
        # 預期: a1, a3 = 2
        assert n5 == 2, f"預期 2 張卡，實際 {n5}"

        # 截圖篩選後狀態
        page.screenshot(path=str(ROOT / "_test_filtered.png"), full_page=True)

        browser.close()
    print("\n[ok] 全部前端互動測試通過")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
