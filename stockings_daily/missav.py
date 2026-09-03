"""MissAV 爬蟲。

站點結構（2024 觀察）：
- 最新列表： https://missav.com/new  （分頁 ?page=N）
- 卡片元素： <article ... data-code="..."> 內含 <a href="/.../xxx"> 與 <img> 與 .text-secondary
- 詳情頁可抓到 duration 與日期

⚠️ 若站點改版導致 0 結果，請依下方註解更新 `parse_listing` 與 `parse_detail`。
"""
from __future__ import annotations

import re
import time
from typing import Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .filters import Video


UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8,ja;q=0.7",
        }
    )
    return s


def fetch_listing_page(session: requests.Session, base_url: str, page: int) -> str:
    """抓 MissAV 最新列表第 N 頁。"""
    if page <= 1:
        url = f"{base_url.rstrip('/')}/new"
    else:
        url = f"{base_url.rstrip('/')}/new?page={page}"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_listing(html: str, base_url: str) -> list[dict]:
    """從列表頁 HTML 抽出影片基本資料。

    ⚙️ 站點改版修正點：
    - 卡片預設 selector：`article a[href]`，標題在 `<img alt>` 或 `<h2>`。
    - 影片 id 取自 URL 末段 e.g. /<slug>-<id>
    """
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict] = []
    seen: set[str] = set()
    for a in soup.select("article a[href]"):
        href = a.get("href", "")
        if not href or "/dm" in href or "/actress" in href or "/genre" in href:
            continue
        url = urljoin(base_url, href)
        # 抓末段 id
        m = re.search(r"-([A-Za-z0-9]+)$", href.rstrip("/"))
        if not m:
            continue
        vid = m.group(1)
        if vid in seen:
            continue
        seen.add(vid)

        img = a.find("img")
        title = (img.get("alt") if img else "") or a.get("title", "") or ""
        if not title:
            h = a.find(["h2", "h3"])
            if h:
                title = h.get_text(strip=True)
        cover = ""
        if img:
            cover = img.get("data-src") or img.get("data-original") or img.get("src") or ""
            if cover and not cover.startswith("http"):
                cover = urljoin(base_url, cover)

        items.append({"video_id": vid, "title": title.strip(), "url": url, "cover": cover})
    return items


def parse_detail(session: requests.Session, video: dict) -> Video:
    """從詳情頁補齊 duration、tags、uploaded_at。"""
    resp = session.get(video["url"], timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text("\n", strip=True)

    duration_min: float | None = None
    m = re.search(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b", text)
    if m:
        parts = [int(x) for x in m.group(1).split(":")]
        if len(parts) == 3:
            duration_min = parts[0] * 60 + parts[1] + parts[2] / 60
        elif len(parts) == 2:
            duration_min = parts[0] + parts[1] / 60

    uploaded_at: str | None = None
    date_pat = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", text)
    if date_pat:
        uploaded_at = f"{date_pat.group(1)}-{date_pat.group(2)}-{date_pat.group(3)}T00:00:00+00:00"

    tags = [t.get_text(strip=True) for t in soup.select("a[href*='/genre/'], a[href*='/tags/']")]

    return Video(
        source="missav",
        video_id=video["video_id"],
        title=video["title"],
        url=video["url"],
        cover=video.get("cover", ""),
        duration_min=round(duration_min, 2) if duration_min else None,
        views=None,  # MissAV 列表通常不顯示觀看數
        uploaded_at=uploaded_at,
        tags=tags[:20],
    )


def crawl(cfg_source) -> Iterable[Video]:
    base_url = cfg_source.base_url
    pages = cfg_source.pages
    delay = cfg_source.request_delay_sec
    session = _session()

    collected: list[Video] = []
    for p in range(1, max(pages, 1) + 1):
        try:
            html = fetch_listing_page(session, base_url, p)
        except Exception as e:  # noqa: BLE001
            print(f"[missav] list page {p} 失敗：{e}")
            continue

        for item in parse_listing(html, base_url):
            try:
                v = parse_detail(session, item)
            except Exception as e:  # noqa: BLE001
                print(f"[missav] detail {item.get('url')} 失敗：{e}")
                continue
            collected.append(v)

        if delay and p < pages:
            time.sleep(delay)

    return collected
