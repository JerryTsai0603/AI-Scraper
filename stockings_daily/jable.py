"""Jable.tv 爬蟲（Playwright 版，搜尋頁 + 女優頁為入口）。

策略：Jable 的標籤頁容易被 Cloudflare 攔下，但「搜尋頁」與「女優頁」放行度較高。
本爬蟲從 `config.yaml` 讀取多個「入口 URL」，每個入口抓 1 頁，合併去重後再進入詳情頁補資料。
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone
from typing import Iterable, Sequence
from urllib.parse import urljoin

try:
    from playwright.sync_api import Browser, Page, sync_playwright  # noqa: F401
    HAS_PLAYWRIGHT = True
except Exception:  # noqa: BLE001
    Browser = Page = sync_playwright = None  # type: ignore
    HAS_PLAYWRIGHT = False

from .filters import Video


UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)


# ---------------- helpers ----------------
def _make_page(browser: Browser) -> Page:
    ctx = browser.new_context(
        user_agent=UA,
        locale="zh-TW",
        viewport={"width": 1280, "height": 900},
        ignore_https_errors=True,
    )
    page = ctx.new_page()
    page.set_default_timeout(45000)
    return page


def _wait_for_unblock(page: Page, max_loops: int = 10, sleep_ms: int = 1200) -> bool:
    """等 Cloudflare challenge 過。"""
    for _ in range(max_loops):
        page.wait_for_timeout(sleep_ms)
        t = page.title() or ""
        if "請稍候" not in t and "Just a moment" not in t and "Verify" not in t:
            return True
    return False


# ---------------- listing ----------------
def _collect_from_listing(page: Page) -> list[tuple[str, str]]:
    """從當前頁面抽出 (url, title) 清單。"""
    page.wait_for_timeout(1200)
    try:
        page.wait_for_selector("div.video-img-box", timeout=8000)
    except Exception:
        pass
    raw = page.eval_on_selector_all(
        "div.video-img-box",
        """els => els.map(box => {
            const a = box.querySelector('a[href*="/videos/"]');
            if (!a) return null;
            const tEl = box.querySelector('.video-title, h6, .title, .video-title-color');
            const img = box.querySelector('img');
            const title = (a.getAttribute('title')
                        || (tEl && tEl.textContent)
                        || (img && img.getAttribute('alt'))
                        || '').trim();
            return { href: a.href, title };
        }).filter(Boolean)""",
    )
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for r in raw:
        href = (r.get("href") or "").split("?")[0].rstrip("/")
        if href and href not in seen and "/videos/" in href:
            seen.add(href)
            out.append((href, (r.get("title") or "").strip()))
    return out


def fetch_from_entry(browser: Browser, entry_url: str) -> tuple[list[tuple[str, str]], Page]:
    """打開單一入口，回傳 (清單, page)。page 由呼叫端負責關閉。"""
    page = _make_page(browser)
    page.goto(entry_url, wait_until="load", timeout=45000)
    if not _wait_for_unblock(page):
        print(f"[jable] Cloudflare stuck: {entry_url}")
        return [], page
    items = _collect_from_listing(page)
    return items, page


# ---------------- detail ----------------
def parse_detail(page: Page, url: str, fallback_title: str = "") -> Video:
    # 直接 goto，不嚴格等 selector（等不到就 evaluate 抓不到，自然 None）
    try:
        page.goto(url, wait_until="load", timeout=30000)
    except Exception:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
    # 給 Cloudflare challenge 更多時間（Actions 機房 IP 容易被擋）
    _wait_for_unblock(page, max_loops=8, sleep_ms=1000)
    page.wait_for_timeout(1500)

    # 標題
    title = ""
    for sel in ["h4.video-title", "h1", "meta[property='og:title']"]:
        try:
            el = page.locator(sel).first
            if el.count() == 0:
                continue
            if sel.startswith("meta"):
                title = (el.get_attribute("content") or "").strip()
            else:
                title = (el.inner_text() or "").strip()
            if title:
                break
        except Exception:
            continue
    if not title:
        title = fallback_title

    text = page.inner_text("body")

    # 觀看數：抓標題旁的純數字；若 evaluate 失敗就 reload 重試最多 2 次
    views: int | None = None
    for attempt in range(2):
        try:
            v = page.evaluate(
                """() => {
                    const h = document.querySelector('h4.video-title') ||
                              Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6'))
                                  .find(x => /[A-Z]{2,}-[0-9]/.test(x.textContent || ''));
                    if (!h) return null;
                    let n = h;
                    for (let i = 0; i < 4; i++) {
                        if (!n.parentElement) break;
                        n = n.parentElement;
                    }
                    const nums = Array.from(n.querySelectorAll('span, p, div'))
                        .map(e => (e.textContent || '').trim())
                        .filter(t => /^[\\d,]+$/.test(t))
                        .map(t => parseInt(t.replace(/,/g, ''), 10))
                        .filter(n => n > 10 && n < 1e9);
                    if (nums.length === 0) return null;
                    return Math.max(...nums);
                }"""
            )
            if v:
                views = int(v)
            break
        except Exception:
            break

    # 上傳時間
    uploaded_at: str | None = None
    m = re.search(r"上市於\s*(20\d{2}-\d{2}-\d{2})", text)
    if m:
        uploaded_at = f"{m.group(1)}T00:00:00+00:00"
    else:
        m2 = re.search(r"(\d+)\s*小時前", text)
        if m2:
            uploaded_at = (datetime.now(timezone.utc) - timedelta(hours=int(m2.group(1)))).isoformat()
        else:
            m3 = re.search(r"(\d+)\s*天前", text)
            if m3:
                uploaded_at = (datetime.now(timezone.utc) - timedelta(days=int(m3.group(1)))).isoformat()

    # 時長：plyr 播放器 aria-valuemax 是秒，失敗就 reload 重試
    duration_min: float | None = None
    for attempt in range(2):
        try:
            secs = page.evaluate(
                """() => {
                    const inp = document.querySelector("input[data-plyr='seek']");
                    if (inp) {
                        const v = parseFloat(inp.getAttribute('aria-valuemax') || '0');
                        if (v > 30) return v;
                    }
                    const t = document.querySelector('.plyr__time--duration');
                    if (t) {
                        const txt = (t.textContent || '').trim();
                        const m = txt.match(/^(?:(\\d+):)?(\\d+):(\\d+)$/);
                        if (m) {
                            const h = parseInt(m[1] || '0', 10);
                            const mn = parseInt(m[2], 10);
                            const s = parseInt(m[3], 10);
                            return h * 3600 + mn * 60 + s;
                        }
                    }
                    return 0;
                }"""
            )
            if secs and secs > 30:
                duration_min = float(secs) / 60.0
            break
        except Exception:
            break
    if duration_min is None:
        m = re.search(r"\b(\d{1,2}):(\d{2}):(\d{2})\b", text)
        if m:
            duration_min = int(m.group(1)) * 60 + int(m.group(2)) + int(m.group(3)) / 60

    # tags
    tags: list[str] = []
    try:
        for el in page.locator("a.tag, .tag, .tags a, a[href*='/tags/']").all():
            t = el.inner_text().strip()
            if t and t not in tags:
                tags.append(t)
    except Exception:
        pass

    # 封面
    cover = ""
    try:
        og = page.locator("meta[property='og:image']").first
        if og.count():
            cover = og.get_attribute("content") or ""
    except Exception:
        pass

    vid = url.rstrip("/").split("/")[-1]
    return Video(
        source="jable",
        video_id=vid,
        title=title,
        url=url,
        cover=cover,
        duration_min=round(duration_min, 2) if duration_min else None,
        views=views,
        uploaded_at=uploaded_at,
        tags=tags[:20],
    )


# ---------------- main crawl ----------------
def crawl(cfg_source) -> Iterable[Video]:
    """入口由 cfg_source.entries 提供，每個 entry 一頁。"""
    entries: Sequence[str] = list(getattr(cfg_source, "entries", []) or [])
    if not entries:
        # 向下相容：舊版用 pages 當作「最新頁 1 頁」
        base = cfg_source.base_url
        entries = [base.rstrip("/") if cfg_source.pages >= 1 else ""]
        entries = [e for e in entries if e]

    delay = cfg_source.request_delay_sec
    per_entry_max = int(getattr(cfg_source, "per_entry_max", 12) or 12)

    collected: list[Video] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            for entry in entries:
                print(f"[jable] entry: {entry}")
                # listing 用獨立 page，結束就關（避免資源累積）
                items: list[tuple[str, str]] = []
                try:
                    items, listing_page = fetch_from_entry(browser, entry)
                except Exception as e:  # noqa: BLE001
                    print(f"[jable] entry err {entry}: {e}")
                    continue
                try:
                    listing_page.context.close()
                except Exception:
                    pass

                print(f"  -> {len(items)} cards (will visit first {per_entry_max})")
                for url, title in items[:per_entry_max]:
                    detail_page = _make_page(browser)
                    try:
                        v = parse_detail(detail_page, url, fallback_title=title)
                        collected.append(v)
                    except Exception as e:  # noqa: BLE001
                        print(f"  detail err {url}: {e}")
                    finally:
                        try:
                            detail_page.context.close()
                        except Exception:
                            pass
                if delay:
                    time.sleep(delay)
        finally:
            browser.close()
    return collected
