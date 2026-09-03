# 一鍵 push 到 GitHub
# 用法：
#   1. 把下面 $RepoUrl 改成你的 repo 網址
#   2. 在 PowerShell 執行：  .\push-to-github.ps1
#
# 需要：已安裝 git

$ErrorActionPreference = 'Stop'

# ★ 請改成你的 repo 網址
$RepoUrl = 'https://jerrytsai0603.github.io/AI-Scraper/'

# 1. 切到本腳本所在目錄
Set-Location -Path $PSScriptRoot
Write-Host "==> 工作目錄：$((Get-Location).Path)" -ForegroundColor Cyan

# 2. 確認 git
try { git --version | Out-Null }
catch { Write-Error "找不到 git，請先安裝：https://git-scm.com/download/win"; exit 1 }

# 3. 確認關鍵檔案存在
$workflowPath = '.github\workflows\daily.yml'
if (-not (Test-Path $workflowPath)) {
    Write-Error "找不到 $workflowPath，請確認你在解壓縮後的 stockings-daily 資料夾裡"
    exit 1
}
Write-Host "==> 找到 workflow 檔：$workflowPath" -ForegroundColor Green

# 4. 初始化
if (-not (Test-Path '.git')) {
    git init | Out-Null
    Write-Host "==> git init 完成"
}
git add .
Write-Host "==> 即將提交的檔案：" -ForegroundColor Cyan
git status --short

# 5. 確認 workflow 真的在清單裡
$status = git status --short
if ($status -notmatch [regex]::Escape($workflowPath.Replace('\','/'))) {
    Write-Warning "⚠️  workflow 檔 $workflowPath 不在 git 清單裡，可能 .gitignore 擋到了"
    Write-Warning "    請打開 .gitignore 確認沒有 '*.yml' 之類的規則"
    $ans = Read-Host "是否仍要繼續？ (y/N)"
    if ($ans -ne 'y') { exit 1 }
}

# 6. 提交
git commit -m "init: stockings & footjob daily crawler" | Out-Null
git branch -M main

# 7. 接 remote
$existing = git remote get-url origin 2>$null
if ($existing) {
    Write-Host "==> 已存在 remote origin：$existing"
    $ans = Read-Host "是否覆蓋為 $RepoUrl ? (y/N)"
    if ($ans -eq 'y') {
        git remote remove origin
        git remote add origin $RepoUrl
    }
} else {
    git remote add origin $RepoUrl
}
Write-Host "==> remote origin = $RepoUrl" -ForegroundColor Green

# 8. push
Write-Host "==> 開始 push..." -ForegroundColor Cyan
git push -u origin main --force

Write-Host ""
Write-Host "==> ✅ 完成！" -ForegroundColor Green
Write-Host ""
Write-Host "下一步："
Write-Host "  1. 開 GitHub repo → Settings → Actions → General → Workflow permissions"
Write-Host "     改為 Read and write permissions → Save"
Write-Host "  2. Settings → Pages → Source 改為 GitHub Actions"
Write-Host "  3. Actions → Daily Crawl → Run workflow"
Write-Host ""
Write-Host "完成後網址： https://JerryTsai0603.github.io/AI-Scraper/"
