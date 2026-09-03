# 除錯指南：頁面顯示「無法讀取 results/latest.json」

頁面前端會去抓 `results/latest.json`，找不到時會顯示 HTTP 404。**這是資料尚未產生的訊號**，不是頁面壞掉。常見原因與解法如下：

---

## 1. Actions 還沒跑過第一次

剛 push 完 repo，預設排程是 `0 18 * * *` UTC（台北凌晨 2 點），在那之前不會有資料。

**立刻觸發一次**：
1. 進到你的 GitHub repo
2. 上方 **Actions** 頁籤
3. 左側選 **Daily Crawl**
4. 右側 **Run workflow** → 選 `main` branch → 綠色 **Run workflow**
5. 等約 1–3 分鐘，跑完看結果

---

## 2. Actions 跑失敗（最常見）

到 **Actions** 頁籤點進去最近一次 run，看哪個 step 紅燈：

### 2.1 爬蟲 0 結果
兩個站點有時會擋自動化請求、或臨時改版，這時 `results/latest.json` 會是空陣列但**檔案存在**，頁面會顯示「共 0 筆」。
**解法**：開 `stockings_daily/jable.py` 或 `missav.py`，依檔內註解更新 selector；或降低 `config.yaml` 的 `pages`、拉長 `request_delay_sec`。

### 2.2 pip install 失敗
通常是 `PyYAML` 之類相依套件版本衝到。改 `requirements.txt` 把該行刪掉 `>=` 改成 `==` 鎖版，或升級 `actions/setup-python` 版本。

### 2.3 commit 沒推上去
如果 `git push` 步驟失敗（多半是權限），需要：
- repo → **Settings** → **Actions** → **General** → **Workflow permissions**
- 改成 **Read and write permissions**
- 儲存後再重跑一次 workflow

### 2.4 看不到 deploy-pages job
- Pages 還沒啟用：repo → **Settings** → **Pages** → **Source** 一定要選 **GitHub Actions**（不是 `Deploy from a branch`）
- 第一次啟用後要等 repo 初始化 GitHub Pages 環境，再重跑 workflow 一次

---

## 3. 網址打錯 / 路徑不對

GitHub Pages 預設網址：

| Pages 來源 | 網址 |
|---|---|
| 從 `main` 分支（**不要用這個**） | `https://<user>.github.io/<repo>/` |
| 從 GitHub Actions 部署（本專案用這個） | `https://<user>.github.io/<repo>/` |

> 兩種來源網址**看起來一樣**，但行為不同：選 branch 會把整包 repo 公開，選 Actions 才會用 `actions/deploy-pages`。

確認實際網址：repo → **Settings** → **Pages** → 上面會顯示「Your site is live at https://...」。

---

## 4. 本地先確認 JSON 存在

```bash
ls results/
# 應該看到：  index.json  latest.json  latest.md  YYYY-MM-DD.json  .gitkeep
```

如果只有 `.gitkeep`，代表 `python -m stockings_daily.main` 沒跑或被前面步驟中斷。本地手動跑一次確認沒問題再 push。

---

## 5. 最快的「先讓畫面有東西」方法

直接把範例 JSON 放進 `results/latest.json` commit 上去（已附在專案根目錄示範版），可以立刻看到完整 UI，但**這只是占位**。等 Actions 第一次跑完會被真實結果覆蓋。

---

## 6. 還是 404？打開瀏覽器 DevTools 看實際請求

1. 在頁面上按 `F12` → **Network** 分頁 → 重新整理
2. 看 `latest.json` 那列：
   - **404** → 檔案真的不存在，照上面步驟處理
   - **CORS error** → 不可能，這是同源
   - **Mixed content** → 你可能用 `http://` 開啟（請用 `https://` 或 Pages 網址）
   - **200 但內容是 HTML** → 靜態伺服器把 404 頁面回成 200，確認 Pages 設定

---

## 7. 工作流診斷清單

跑 workflow 前請依序確認：

- [ ] repo 是 **public**（或你有 GitHub Pro/Team 讓 private repo 能用 Pages）
- [ ] `Settings → Actions → General → Workflow permissions` = **Read and write**
- [ ] `Settings → Pages → Source` = **GitHub Actions**
- [ ] `stockings_daily/`、`config.yaml`、`requirements.txt` 都有被 commit
- [ ] `.github/workflows/daily.yml` 路徑正確（注意不能多一層資料夾）
- [ ] Actions 跑完兩個 job（`crawl` + `deploy-pages`）都是綠燈
