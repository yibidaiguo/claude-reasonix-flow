# 把本机上改过的配置同步回仓库（install.ps1 的反方向）。
#
# 用途：你在 ~/.claude 或 ~/.agents 里直接改了文件，想把改动收回版本控制。
#
# 用法： .\capture.ps1

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
$home_ = [Environment]::GetFolderPath("UserProfile")

# 和 install.ps1 一致：Codex 家目录可以被 CODEX_HOME 挪走。
$codexHome = $env:CODEX_HOME
if (-not $codexHome) { $codexHome = Join-Path $home_ ".codex" }

# 注意：rx.py 在 Codex 侧只是一份副本，权威在 claude\scripts\rx.py。
# 这里不从 Codex 侧收回 rx.py，免得两个来源打架。
$pairs = @(
    @{ repoPath = "claude\skills\dev-cycle\SKILL.md";   root = $home_;     livePath = ".claude\skills\dev-cycle\SKILL.md" },
    @{ repoPath = "claude\scripts\rx.py";               root = $home_;     livePath = ".claude\scripts\rx.py" },
    @{ repoPath = "agents\skills\implementer\SKILL.md"; root = $home_;     livePath = ".agents\skills\implementer\SKILL.md" },
    @{ repoPath = "agents\skills\verifier\SKILL.md";    root = $home_;     livePath = ".agents\skills\verifier\SKILL.md" },
    @{ repoPath = "codex\skills\dev-cycle\SKILL.md";    root = $codexHome; livePath = "skills\dev-cycle\SKILL.md" }
)

$changed = 0
foreach ($p in $pairs) {
    $live = Join-Path $p.root $p.livePath
    $dst  = Join-Path $repo $p.repoPath

    if (-not (Test-Path $live)) {
        Write-Host "本机上没有，跳过: $live" -ForegroundColor Yellow
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
