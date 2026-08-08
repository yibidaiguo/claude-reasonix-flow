# 把仓库里的配置铺到本机。已存在的文件先备份成 .bak，不会静默覆盖。
#
# 用法： .\install.ps1

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
$home_ = [Environment]::GetFolderPath("UserProfile")

$pairs = @(
    @{ src = "claude\skills\dev-cycle\SKILL.md";      dst = ".claude\skills\dev-cycle\SKILL.md" },
    @{ src = "claude\scripts\rx.py";                  dst = ".claude\scripts\rx.py" },
    @{ src = "agents\skills\implementer\SKILL.md";    dst = ".agents\skills\implementer\SKILL.md" },
    @{ src = "agents\skills\verifier\SKILL.md";       dst = ".agents\skills\verifier\SKILL.md" }
)

foreach ($p in $pairs) {
    $src = Join-Path $repo $p.src
    $dst = Join-Path $home_ $p.dst

    if (-not (Test-Path $src)) { Write-Error "仓库里缺文件: $src" }

    $dstDir = Split-Path $dst -Parent
    if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Force $dstDir | Out-Null }

    if (Test-Path $dst) {
        if ((Get-FileHash $src).Hash -eq (Get-FileHash $dst).Hash) {
            Write-Host "跳过（内容相同）: $($p.dst)"
            continue
        }
        Copy-Item $dst "$dst.bak" -Force
        Write-Host "已备份原文件: $($p.dst).bak"
    }

    Copy-Item $src $dst -Force
    Write-Host "已安装: $($p.dst)"
}

Write-Host ""
Write-Host "装完了。自检（不花钱）：" -ForegroundColor Green
Write-Host "    python ~/.claude/scripts/rx.py doctor"
