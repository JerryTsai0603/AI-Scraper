"""Stockings & Footjob Daily 爬蟲入口。"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from . import eporner, jable, missav
from .config import Config, load_config
from .filters import Video, match_keywords, passes_filters


SOURCE_MODULES = {
    "jable": jable,
    "missav": missav,
    "eporner": eporner,
}


def collect(cfg: Config) -> list[Video]:
    """跑所有啟用的來源，合併 Video 結果。"""
    all_videos: list[Video] = []
    for name, mod in SOURCE_MODULES.items():
        src_cfg = cfg.sources.get(name)
        if not src_cfg or not src_cfg.enabled:
            print(f"[skip] {name} 未啟用")
            continue
        print(f"[run]  {name} 開始爬取...")
        try:
            videos = list(mod.crawl(src_cfg))
        except Exception as e:  # noqa: BLE001
            print(f"[err]  {name} 整體失敗：{e}")
            continue
        print(f"[ok]   {name} 取得 {len(videos)} 部")
        all_videos.extend(videos)
    return all_videos


def apply_keyword_filter(videos: list[Video], cfg: Config) -> list[Video]:
    kws = cfg.all_keywords
    for v in videos:
        v.matched_keywords = match_keywords(v.title, kws)
    return [v for v in videos if v.matched_keywords]


def apply_rule_filter(videos: list[Video], cfg: Config) -> list[Video]:
    return [v for v in videos if passes_filters(v, cfg)]


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _build_markdown(date_str: str, videos: list[Video]) -> str:
    lines: list[str] = []
    lines.append(f"# Stockings & Footjob Daily — {date_str}")
    lines.append("")
    lines.append(f"共 **{len(videos)}** 部符合條件。")
    lines.append("")
    lines.append("| 來源 | 標題 | 時長 | 觀看 | 上傳 | 命中關鍵字 | 連結 |")
    lines.append("|---|---|---|---|---|---|---|")
    for v in videos:
        dur = f"{v.duration_min:.1f}m" if v.duration_min is not None else "-"
        views = f"{v.views:,}" if v.views is not None else "-"
        date = (v.uploaded_at or "")[:10] or "-"
        kw = ", ".join(v.matched_keywords)
        title = (v.title or "").replace("|", "\\|")
        lines.append(
            f"| {v.source} | {title} | {dur} | {views} | {date} | {kw} | [link]({v.url}) |"
        )
    lines.append("")
    return "\n".join(lines)


def write_results(cfg: Config, videos: list[Video], date_str: str | None = None) -> dict:
    """把結果寫到磁碟。回傳要 commit 的相對路徑清單。"""
    out_dir = Path(cfg.output.results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = date_str or _today()

    payload = {
        "date": date_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(videos),
        "videos": [v.to_dict() for v in videos],
    }
    latest_json = out_dir / "latest.json"
    latest_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    paths = [latest_json]
    if cfg.output.keep_history:
        dated = out_dir / f"{date_str}.json"
        dated.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths.append(dated)

    # index.json：列出所有歷史檔
    history = sorted(p.name for p in out_dir.glob("????-??-??.json"))
    (out_dir / "index.json").write_text(
        json.dumps({"history": history, "latest": "latest.json"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    paths.append(out_dir / "index.json")

    if cfg.output.write_markdown_report:
        md_path = out_dir / "latest.md"
        md_path.write_text(_build_markdown(date_str, videos), encoding="utf-8")
        paths.append(md_path)

    return {"paths": [str(p) for p in paths], "payload": payload}


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    cfg_path = argv[0] if argv else "config.yaml"
    cfg = load_config(cfg_path)
    print(f"[cfg]  讀取設定：{cfg_path}")
    print(f"[cfg]  關鍵字數：{len(cfg.all_keywords)}")

    raw = collect(cfg)
    print(f"[all]  原始影片數：{len(raw)}")

    # 除錯用：把原始標題列印出來，方便看為什麼 0 命中
    if os.environ.get("DEBUG_TITLES") == "1":
        print("--- 原始標題 ---")
        for v in raw[:30]:
            print(f"  {v.title}")

    matched = apply_keyword_filter(raw, cfg)
    print(f"[kw]   命中關鍵字：{len(matched)}")

    passed = apply_rule_filter(matched, cfg)
    print(f"[flt]  通過條件篩選：{len(passed)}")

    result = write_results(cfg, passed)
    print(f"[done] 輸出檔案：")
    for p in result["paths"]:
        print(f"       - {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
