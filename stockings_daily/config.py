"""讀取與解析 config.yaml。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SourceConfig:
    enabled: bool = True
    base_url: str = ""
    pages: int = 3
    request_delay_sec: float = 2.0
    entries: list[str] = field(default_factory=list)   # 入口 URL 清單（Playwright 模式用）
    per_entry_max: int = 12                              # 每個入口最多看幾部詳情頁
    queries: list[str] = field(default_factory=list)    # 關鍵字清單（API 模式用，如 eporner）
    per_query: int = 15                                  # 每個關鍵字抓幾部
    thumbs_size: str = "medium"                          # 封面尺寸


@dataclass
class FiltersConfig:
    min_views: int = 0
    min_duration_min: int = 0
    max_duration_min: int = 0
    uploaded_within_days: int = 0


@dataclass
class OutputConfig:
    results_dir: str = "results"
    write_markdown_report: bool = True
    keep_history: bool = True


@dataclass
class Config:
    keywords: dict[str, list[str]] = field(default_factory=dict)
    filters: FiltersConfig = field(default_factory=FiltersConfig)
    sources: dict[str, SourceConfig] = field(default_factory=dict)
    output: OutputConfig = field(default_factory=OutputConfig)

    @property
    def all_keywords(self) -> list[str]:
        """把 stockings 與 footjob 兩個分類合併，並去重、去空白。"""
        seen: set[str] = set()
        out: list[str] = []
        for group in self.keywords.values():
            for kw in group:
                k = kw.strip()
                if k and k not in seen:
                    seen.add(k)
                    out.append(k)
        return out


def load_config(path: str | Path = "config.yaml") -> Config:
    """讀取 YAML 並回傳 Config 物件。"""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"找不到設定檔：{p}")
    data: dict[str, Any] = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    filters_data = data.get("filters", {}) or {}
    sources_data = data.get("sources", {}) or {}
    output_data = data.get("output", {}) or {}

    sources: dict[str, SourceConfig] = {}
    for name, src in sources_data.items():
        sources[name] = SourceConfig(
            enabled=bool(src.get("enabled", True)),
            base_url=str(src.get("base_url", "")),
            pages=int(src.get("pages", 3)),
            request_delay_sec=float(src.get("request_delay_sec", 2.0)),
            entries=[str(x) for x in (src.get("entries") or [])],
            per_entry_max=int(src.get("per_entry_max", 12)),
            queries=[str(x) for x in (src.get("queries") or [])],
            per_query=int(src.get("per_query", 15)),
            thumbs_size=str(src.get("thumbs_size", "medium")),
        )

    return Config(
        keywords=data.get("keywords", {}) or {},
        filters=FiltersConfig(
            min_views=int(filters_data.get("min_views", 0)),
            min_duration_min=int(filters_data.get("min_duration_min", 0)),
            max_duration_min=int(filters_data.get("max_duration_min", 0)),
            uploaded_within_days=int(filters_data.get("uploaded_within_days", 0)),
        ),
        sources=sources,
        output=OutputConfig(
            results_dir=str(output_data.get("results_dir", "results")),
            write_markdown_report=bool(output_data.get("write_markdown_report", True)),
            keep_history=bool(output_data.get("keep_history", True)),
        ),
    )
