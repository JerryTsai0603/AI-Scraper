"""eporner.com 公開 API 爬蟲（不需要 Playwright，純 HTTP）。

API: https://www.eporner.com/api/v2/video/search/?query=<KEYWORD>&format=json&per_page=20&page=1
回傳 JSON 含 videos[]，每部影片欄位：
  id, title, length_min, length_sec, views, rate, keywords, url, default_thumb.src, thumbs[]
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Iterable

from .filters import Video


UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

API_BASE = "https://www.eporner.com/api/v2/video/search/"


def _http_get_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/json",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def _to_video(v: dict) -> Video:
    """把 eporner API 單部影片轉成 Video。"""
    vid = str(v.get("id", "")).strip()
    title = (v.get("title") or "").strip()
    url = v.get("url") or f"https://www.eporner.com/v/{vid}"
    if not url.startswith("http"):
        url = "https://www.eporner.com" + url

    # 封面：default_thumb.src 或 thumbs[0].src
    cover = ""
    dt = v.get("default_thumb")
    if isinstance(dt, dict):
        cover = dt.get("src", "") or ""
    if not cover:
        thumbs = v.get("thumbs") or []
        if thumbs and isinstance(thumbs[0], dict):
            cover = thumbs[0].get("src", "") or ""

    # 時長：length_min 是字串 "10:35" 或數字（兩種格式都有遇過）
    duration_min: float | None = None
    raw_len = v.get("length_min")
    if isinstance(raw_len, (int, float)) and raw_len > 0:
        duration_min = float(raw_len)
    elif isinstance(raw_len, str) and raw_len:
        # 嘗試解析 "10:35" 格式
        s = raw_len.strip()
        if ":" in s:
            parts = s.split(":")
            try:
                if len(parts) == 3:
                    duration_min = int(parts[0]) * 60 + int(parts[1]) + int(parts[2]) / 60
                elif len(parts) == 2:
                    duration_min = int(parts[0]) + int(parts[1]) / 60
            except ValueError:
                pass
        else:
            try:
                duration_min = float(s)
            except ValueError:
                pass
    if not duration_min:
        secs = v.get("length_sec")
        if isinstance(secs, (int, float)) and secs > 0:
            duration_min = float(secs) / 60.0
    if duration_min is not None:
        duration_min = round(duration_min, 2)

    views: int | None = None
    try:
        if v.get("views") is not None:
            views = int(v["views"])
    except (TypeError, ValueError):
        pass

    keywords = (v.get("keywords") or "").strip()
    tags = [k.strip() for k in keywords.split(",") if k.strip()]
    return Video(
        source="eporner",
        video_id=vid,
        title=title,
        url=url,
        cover=cover,
        duration_min=duration_min,
        views=views,
        uploaded_at=None,  # eporner API 不直接提供日期
        tags=tags[:20],
    )


def crawl(cfg_source) -> Iterable[Video]:
    """依 cfg_source.queries 跑多組關鍵字，每組抓 N 筆。"""
    queries: list[str] = list(getattr(cfg_source, "queries", []) or [])
    if not queries:
        # 向後相容：若用 base_url + pages 舊版設定
        queries = ["stockings", "footjob"]
    per_query: int = int(getattr(cfg_source, "per_query", 15) or 15)
    delay: float = float(getattr(cfg_source, "request_delay_sec", 1.0) or 1.0)
    thumbs_size: str = str(getattr(cfg_source, "thumbs_size", "medium") or "medium")

    collected: list[Video] = []
    seen: set[str] = set()
    for q in queries:
        url = (
            f"{API_BASE}?query={urllib.parse.quote(q)}"
            f"&format=json&per_page={per_query}&page=1&thumbsize={thumbs_size}"
        )
        print(f"[eporner] query={q}")
        try:
            data = _http_get_json(url)
        except Exception as e:  # noqa: BLE001
            print(f"[eporner] err {q}: {e}")
            continue
        n_total = data.get("total_count", 0)
        videos = data.get("videos", []) or []
        print(f"  -> {len(videos)} cards (total {n_total} on site)")
        for raw in videos:
            v = _to_video(raw)
            if v.video_id and v.video_id not in seen:
                seen.add(v.video_id)
                collected.append(v)
        if delay:
            time.sleep(delay)
    return collected
