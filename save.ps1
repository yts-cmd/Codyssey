param (
    [string]$msg = "과제 진행 내역 업데이트"
)

$today = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# 로그 폴더 생성 및 기록
New-Item -ItemType Directory -Force -Path "claimcare-ai\docs\logs" | Out-Null
$logLine = "- [$today] $msg"
Add-Content -Path "claimcare-ai\docs\logs\history.log" -Value $logLine -Encoding utf8

# Git 자동 추가, 커밋, 푸시
git add .
git commit -m "$msg ($today)"
git push

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ 깃허브 자동 저장 및 업로드 완료!" -ForegroundColor Green
Write-Host "메시지: $msg" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan
