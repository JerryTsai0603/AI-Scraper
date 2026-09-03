# 一鍵上傳到 GitHub（推薦用 git，不要用網頁拖檔）

> ⚠️ **不要用「Add files via upload」拖整包 zip 進去** — GitHub 網頁上傳會自動跳過隱藏資料夾（`.github/`），導致 workflow 沒被上傳，Actions 永遠不會跑。

---

## 方法 A：用 `git push`（最穩，30 秒搞定）

打開 PowerShell，把下面整段貼上執行（**只要改 `<你的帳號>`**）：

```powershell
# 切到解壓縮後的資料夾
Set-Location "C:\Users\jerrytsai\Downloads\stockings-daily"

# 1. 初始化 git
git init
git add .
git status    # 確認清單裡有 .github/workflows/daily.yml（這步最重要）

# 2. 提交
git commit -m "init: stockings & footjob daily crawler"
git branch -M main

# 3. 接到你的 GitHub repo（請把下面網址換成你自己的）
git remote remove origin 2>$null
git remote add origin https://github.com/JerryTsai0603/AI-Scraper.git

# 4. 推上去（會問你 GitHub 帳號密碼 / PAT）
git push -u origin main --force
```

> 第一次 push 會要你登入 GitHub。建議先用 **Personal Access Token (PAT)**：
> 1. https://github.com/settings/tokens → **Generate new token (classic)**
> 2. 勾選 `repo` 全部權限
> 3. 產生後複製 token，把它當密碼貼

`git status` 那一行最關鍵：請截圖給我看，或自己確認有看到 `.github/workflows/daily.yml` 在清單裡。

---

## 方法 B：雙重保險 — 單獨再 Add 一次 workflow 檔

如果方法 A 因網路 / 認證失敗，做這招備援：

1. 在 GitHub repo 網頁，**Add file** → **Create new file**
2. 檔名輸入：`.github/workflows/daily.yml`（含資料夾，GitHub 會自動建）
3. 內容打開本專案的 `.github/workflows/daily.yml`，全選複製貼上
4. 下方 **Commit new file**

這個方法可確保 workflow 一定會被加進去，不用依賴 git。

---

## 推上去之後的設定

無論用哪個方法，最後都要做這兩步：

### 1. 啟用 GitHub Actions 寫入權限
- repo → **Settings** → **Actions** → **General**
- 拉到最下面 **Workflow permissions**
- 選 **Read and write permissions**
- 按 **Save**

### 2. 啟用 Pages（用 Actions，不是 branch）
- repo → **Settings** → **Pages**
- **Source** 改為 **GitHub Actions**（原本是「Deploy from a branch」）
- 儲存

---

## 觸發第一次執行

- repo → **Actions** 分頁
- 左邊會出現 **Daily Crawl** workflow
- 點進去 → 右邊 **Run workflow** → 選 main → 綠色按鈕
- 等 1–3 分鐘，跑完應該有兩個綠色 job：`crawl` + `deploy-pages`
- 然後到 **Settings → Pages** 看上面會出現網址：
  `https://JerryTsai0603.github.io/AI-Scraper/`

---

## 怎麼知道哪裡出問題

如果 `Daily Crawl` workflow 沒出現在左邊 = workflow 檔案沒上傳成功，回到方法 A 或 B。
如果出現了但跑失敗：點進去那個紅色 run，看是哪個 step 紅燈，把 log 截圖丟給我。
