"""本地煙霧測試：載入 config、套用 filters 不打網路。"""
from datetime import datetime, timezone, timedelta

from stockings_daily.config import load_config
from stockings_daily.filters import Video, match_keywords, passes_filters


def main() -> int:
    cfg = load_config("config.yaml")
    print(f"[cfg] keywords total = {len(cfg.all_keywords)}")
    print(f"[cfg] sample keywords = {cfg.all_keywords[:6]}")
    print(f"[cfg] min_views={cfg.filters.min_views} "
          f"duration=[{cfg.filters.min_duration_min}, {cfg.filters.max_duration_min}] "
          f"uploaded_within_days={cfg.filters.uploaded_within_days}")

    # 假資料
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    old = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")

    samples = [
        Video(source="jable", video_id="abc", title="絲襪 OL 誘惑",
              url="https://jable.tv/v/abc", views=5000, duration_min=20,
              uploaded_at=f"{today}T00:00:00+00:00"),
        Video(source="jable", video_id="def", title="Random Movie",
              url="https://jable.tv/v/def", views=5000, duration_min=20,
              uploaded_at=f"{today}T00:00:00+00:00"),
        Video(source="missav", video_id="ghi", title="足コキ痴女",
              url="https://missav.com/x-ghi", views=1500, duration_min=60,
              uploaded_at=f"{today}T00:00:00+00:00"),
        Video(source="missav", video_id="jkl", title="Stockings Fun",
              url="https://missav.com/x-jkl", views=2000, duration_min=200,
              uploaded_at=f"{today}T00:00:00+00:00"),
        Video(source="missav", video_id="mno", title="古早片",
              url="https://missav.com/x-mno", views=2000, duration_min=20,
              uploaded_at=f"{old}T00:00:00+00:00"),
    ]

    for s in samples:
        s.matched_keywords = match_keywords(s.title, cfg.all_keywords)
        print(f"  - '{s.title}' hits={s.matched_keywords} views={s.views} dur={s.duration_min}")

    matched = [s for s in samples if s.matched_keywords]
    passed = [s for s in matched if passes_filters(s, cfg)]

    print(f"\n[result] matched={len(matched)} passed={len(passed)}")
    for s in passed:
        print(f"  KEEP: {s.title}  ({s.source})  views={s.views} dur={s.duration_min} kw={s.matched_keywords}")

    # 預期：絲襪 OL 誘惑 與 足コキ痴女 會留下
    # Stockings Fun 會被 max_duration 濾掉 (200>120)
    # 古早片會被 uploaded_within_days 濾掉
    expected_titles = {"絲襪 OL 誘惑", "足コキ痴女"}
    got = {s.title for s in passed}
    assert expected_titles.issubset(got), f"預期命中 {expected_titles}，實際 {got}"
    print("\n[ok] 篩選邏輯符合預期")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
