# 把本机上改过的配置同步回仓库（install.ps1 的反方向）。
#
# 用途：你在 ~/.claude 或 ~/.agents 里直接改了文件，想把改动收回版本控制。
#
# 用法： .\capture.ps1

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
$home_ = [Environment]::GetFolderPath("UserProfile")

$pairs = @(
    @{ repoPath = "claude\skills\dev-cycle\SKILL.md";   livePath = ".claude\skills\dev-cycle\SKILL.md" },
    @{ repoPath = "claude\scripts\rx.py";               livePath = ".claude\scripts\rx.py" },
    @{ repoPath = "agents\skills\implementer\SKILL.md"; livePath = ".agents\skills\implementer\SKILL.md" },
    @{ repoPath = "agents\skills\verifier\SKILL.md";    livePath = ".agents\skills\verifier\SKILL.md" }
)

$changed = 0
foreach ($p in $pairs) {
    $live = Join-Path $home_ $p.livePath
    $dst  = Join-Path $repo $p.repoPath

    if (-not (Test-Path $live)) {
        Write-Host "本机上没有，跳过: $($p.livePath)" -ForegroundColor Yellow
        continue
    }
    if ((Test-Path $dst) -and (Get-FileHash $live).Hash -eq (Get-FileHash $dst).Hash) {
        continue
    }

    $dstDir = Split-Path $dst -Parent
    if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Force $dstDir | Out-Null }
    Copy-Item $live $dst -Force
    Write-Host "已收回: $($p.repoPath)"
    $changed++
}

if ($changed -eq 0) {
    Write-Host "没有改动，仓库和本机一致。" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "收回了 $changed 个文件。检查后提交：" -ForegroundColor Green
    Write-Host "    git -C `"$repo`" diff"
}
