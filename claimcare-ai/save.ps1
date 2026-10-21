param (
    [string]$msg = "작업 진행 로그 업데이트"
)

$today = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$logLine = "- [$today] $msg"

# docs/logs/history.log 파일에 작업 시간과 내역 누적 기록
Add-Content -Path "docs/logs/history.log" -Value $logLine -Encoding utf8

# Git 변경사항 모두 담기
git add .

# 커밋 및 푸시
git commit -m "$msg ($today)"
git push origin main

Write-Host "✅ [Git & 로그 자동 저장 완료] $msg" -ForegroundColor Green
