"""影片資料模型與篩選邏輯。"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable

from .config import Config


@dataclass
class Video:
    """單部影片的最小資料結構。"""

    source: str                # "jable" / "missav"
    video_id: str
    title: str
    url: str
    cover: str = ""
    duration_min: float | None = None
    views: int | None = None
    uploaded_at: str | None = None   # ISO 8601
    tags: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_text(s: str) -> str:
    return (s or "").lower()


def match_keywords(title: str, keywords: Iterable[str]) -> list[str]:
    """回傳標題中所有命中的關鍵字（不分大小寫）。"""
    t = normalize_text(title)
    hits: list[str] = []
    for kw in keywords:
        k = normalize_text(kw)
        if k and k in t:
            hits.append(kw)
    return hits


def passes_filters(video: Video, cfg: Config) -> bool:
    """套用 config.filters 中的所有條件。"""
    f = cfg.filters

    if f.min_views and (video.views is None or video.views < f.min_views):
        return False

    if video.duration_min is not None:
        if f.min_duration_min and video.duration_min < f.min_duration_min:
            return False
        if f.max_duration_min and video.duration_min > f.max_duration_min:
            return False

    if f.uploaded_within_days and video.uploaded_at:
        try:
            ua = datetime.fromisoformat(video.uploaded_at.replace("Z", "+00:00"))
            if ua.tzinfo is None:
                ua = ua.replace(tzinfo=timezone.utc)
            cutoff = datetime.now(timezone.utc) - timedelta(days=f.uploaded_within_days)
            if ua < cutoff:
                return False
        except ValueError:
            # 日期格式無法解析就放行，不阻擋
            pass

    return True
