# 把仓库里的配置铺到本机。已存在的文件先备份成 .bak，不会静默覆盖。
#
# 用法： .\install.ps1

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
$home_ = [Environment]::GetFolderPath("UserProfile")

# Codex 的家目录可以被 CODEX_HOME 挪走（本机就挪到了 D 盘），不能写死 ~/.codex。
$codexHome = $env:CODEX_HOME
if (-not $codexHome) { $codexHome = Join-Path $home_ ".codex" }

$pairs = @(
    @{ src = "claude\skills\dev-cycle\SKILL.md";      root = $home_;     dst = ".claude\skills\dev-cycle\SKILL.md" },
    @{ src = "claude\scripts\rx.py";                  root = $home_;     dst = ".claude\scripts\rx.py" },
    @{ src = "agents\skills\implementer\SKILL.md";    root = $home_;     dst = ".agents\skills\implementer\SKILL.md" },
    @{ src = "agents\skills\verifier\SKILL.md";       root = $home_;     dst = ".agents\skills\verifier\SKILL.md" },

    # Codex 侧。rx.py 装两份，让 Codex 那边的 skill 不依赖 ~/.claude 是否存在。
    @{ src = "codex\skills\dev-cycle\SKILL.md";       root = $codexHome; dst = "skills\dev-cycle\SKILL.md";  codex = $true },
    @{ src = "claude\scripts\rx.py";                  root = $codexHome; dst = "scripts\rx.py";              codex = $true }
)

$codexPresent = Test-Path $codexHome
if (-not $codexPresent) {
    Write-Host "没找到 Codex 家目录（$codexHome），跳过 Codex 部分。" -ForegroundColor Yellow
    Write-Host "装了 Codex 但目录在别处，就设好 CODEX_HOME 再跑一次。" -ForegroundColor Yellow
}

foreach ($p in $pairs) {
    if ($p.codex -and -not $codexPresent) { continue }

    $src = Join-Path $repo $p.src
    $dst = Join-Path $p.root $p.dst

    if (-not (Test-Path $src)) { Write-Error "仓库里缺文件: $src" }

    $dstDir = Split-Path $dst -Parent
    if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Force $dstDir | Out-Null }

    if (Test-Path $dst) {
        if ((Get-FileHash $src).Hash -eq (Get-FileHash $dst).Hash) {
            Write-Host "跳过（内容相同）: $dst"
            continue
        }
        Copy-Item $dst "$dst.bak" -Force
        Write-Host "已备份原文件: $dst.bak"
    }

    Copy-Item $src $dst -Force
    Write-Host "已安装: $dst"
}

Write-Host ""
Write-Host "装完了。自检（不花钱）：" -ForegroundColor Green
Write-Host "    python ~/.claude/scripts/rx.py doctor"
