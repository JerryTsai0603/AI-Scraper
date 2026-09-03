# Stockings & Footjob Daily 爬蟲

每日自動爬取 [Jable.tv](https://jable.tv/) 與 [MissAV](https://missav.com/) 上標題含有 **絲襪 / 腳交** 相關關鍵字的影片，依據觀看數、時長、上傳日期等條件篩選，並將結果存成 JSON 與 Markdown 報告，透過 GitHub Actions 每日自動執行。

> ⚠️ **免責聲明**：本工具僅用於個人研究與資料整理目的。請尊重著作權與各站點之 `robots.txt` 與服務條款。所有資料版權歸原網站與原作者所有。

---

## 功能

- 每日定時（GitHub Actions cron）自動爬取 Jable.tv 與 MissAV 的最新影片列表。
- 標題關鍵字過濾（中文 / 英文 / 日文），可在 `config.yaml` 自訂詞彙。
- 額外篩選條件：
  - 最少觀看數（`min_views`）
  - 時長區間（`min_duration_min` / `max_duration_min`）
  - 上傳日期區間（`uploaded_within_days`）
- 結果同時輸出為：
  - `results/latest.json` — 最新一次結果（給前端 / Pages 讀取用）
  - `results/YYYY-MM-DD.json` — 每日歷史結果
  - `results/latest.md` — 最新一次可閱讀報告
  - `results/index.json` — 每日結果索引
- 自動 commit 回 repo（透過 `github-actions[bot]`）。

---

## 專案結構

```
stockings-daily/
├── .github/
│   └── workflows/
│       └── daily.yml           # 每日 cron + 自動 commit
├── stockings_daily/
│   ├── __init__.py
│   ├── config.py               # 讀取 config.yaml
│   ├── filters.py              # 關鍵字 + 觀看/時長/日期篩選
│   ├── jable.py                # Jable.tv 爬蟲
│   ├── missav.py               # MissAV 爬蟲
│   └── main.py                 # 入口
├── config.yaml                 # 篩選條件與來源設定
├── requirements.txt
├── results/                    # 每日結果輸出
└── README.md
```

---

## 本地執行

需求：Python 3.10+

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python -m stockings_daily.main
```

執行完會在 `results/` 看到 `latest.json`、`latest.md` 以及當天日期的 JSON。

---

## 部署到 GitHub

1. 在 GitHub 建立一個新的 **public** repo（例如 `stockings-daily`）。
2. 把本資料夾內容 push 上去：
   ```bash
   git init
   git add .
   git commit -m "init: stockings & footjob daily crawler"
   git branch -M main
   git remote add origin git@github.com:<你的帳號>/stockings-daily.git
   git push -u origin main
   ```
3. GitHub Actions 會在每日 **UTC 18:00**（台北時間凌晨 2 點）自動跑；亦可從 Actions 分頁手動觸發 `Run workflow`。
4. **啟用 GitHub Pages**（顯示網頁）：
   - repo → **Settings** → **Pages** → **Source** 選 **GitHub Actions**（不要選 branch，否則會跟我們的 workflow 衝突）
   - 之後每次 Actions 跑完會自動 deploy；網址會出現在 Actions 的 deploy job 結果中
   - 首次若還沒跑過 workflow，可手動觸發一次讓 Pages 初始化

## 網頁功能（`index.html`）

打開 GitHub Pages 連結可以看到：

- **搜尋 / 篩選面板**
  - 標題關鍵字即時搜尋
  - 來源切換（Jable.tv / MissAV）
  - 主題切換（絲襪 / 腳交，根據命中關鍵字分類）
  - 快速標籤 chips（顯示前 12 個最常命中關鍵字，可一鍵套用 / 取消）
  - 數值條件：最少觀看數、最短 / 最長時長、近 N 天上傳
  - 排序：上傳日期 / 觀看數 / 時長 / 標題
  - 每頁顯示張數 + 分頁
- **卡片內容**（每部影片一張卡）
  - 封面圖（hover 變色，點擊前往原站）
  - 來源 badge、總時長
  - 標題（hover 顯示完整標題）
  - 主題、上傳日期、觀看數
  - 自動產生的「影片描述」（來源 / 觀看 / 時長 / 上傳 / 命中關鍵字）
  - Tag 列表（命中關鍵字高亮）
  - 動作按鈕：前往原站 / Google 搜尋
- **資料來源區塊** 與頁尾版權聲明

---

## 設定（`config.yaml`）

```yaml
keywords:
  stockings:        # 絲襪類
    - 絲襪
    - stockings
    - pantyhose
    - パンスト
    - タイツ
    - ストッキング
    - 黒タイツ
  footjob:          # 腳交類
    - 腳交
    - 足交
    - footjob
    - foot fetish
    - 足コキ
    - 足フェチ
    - 足裏

filters:
  min_views: 1000                # 最少觀看數
  min_duration_min: 5            # 最短時長（分鐘）
  max_duration_min: 120          # 最長時長（分鐘）
  uploaded_within_days: 30       # 只取最近 N 天上傳的

sources:
  jable:
    enabled: true
    pages: 3                     # 爬最新 N 頁
  missav:
    enabled: true
    pages: 3
```

---

## 注意事項

- 若站點改版導致 selector 失效，請更新對應 `stockings_daily/jable.py` 或 `missav.py` 內的 `parse_*` 函式。
- 兩個站點對於高頻請求都可能觸發 rate-limit；GitHub Actions 預設 IP 為微軟資料中心，仍請保持禮貌（每頁之間 sleep）。
- 爬蟲程式碼以 `requests` + `BeautifulSoup` 為主；如站點改為純前端渲染，需改用 Playwright（已預留擴充點）。
