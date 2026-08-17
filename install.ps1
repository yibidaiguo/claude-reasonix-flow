# 把仓库里的配置铺到本机。已存在的文件先备份成 .bak，不会静默覆盖。
#
# 用法： .\install.ps1

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
$home_ = [Environment]::GetFolderPath("UserProfile")

# Codex 的家目录可以被 CODEX_HOME 挪走（本机就挪到了 D 盘），不能写死 ~/.codex。
$codexHome = $env:CODEX_HOME
if (-not $codexHome) { $codexHome = Join-Path $home_ ".codex" }

# implementer / verifier / operator 的档案只装 ~/.agents/skills/ 一份，两个执行后端共用：
# Reasonix 按名字查这个目录，codex 后端由 rx.py 读同一份文件拼进提示词。
#
# explore 是例外——Reasonix 自带 builtin explore，档案装进 ~/.agents/skills/ 会盖掉它，
# 所以只铺到 roles/ 目录，那是 codex 后端专用的搜索路径。
# 任务书模板跟着技能走（装进技能目录的 templates/ 子目录），技能里用相对路径引它们。
# references/ 同理：主文件瘦身后，铺路细节和后端差异挪进去按需读，不进每次调用的上下文。
$pairs = @(
    @{ src = "claude\skills\dev-cycle\SKILL.md";      root = $home_;     dst = ".claude\skills\dev-cycle\SKILL.md" },
    @{ src = "claude\skills\dev-cycle\references\setup.md";    root = $home_; dst = ".claude\skills\dev-cycle\references\setup.md" },
    @{ src = "claude\skills\dev-cycle\references\backends.md"; root = $home_; dst = ".claude\skills\dev-cycle\references\backends.md" },
    @{ src = "templates\task-implementer.md";         root = $home_;     dst = ".claude\skills\dev-cycle\templates\task-implementer.md" },
    @{ src = "templates\task-verifier.md";            root = $home_;     dst = ".claude\skills\dev-cycle\templates\task-verifier.md" },
    @{ src = "templates\task-explore.md";             root = $home_;     dst = ".claude\skills\dev-cycle\templates\task-explore.md" },
    @{ src = "templates\task-operator.md";            root = $home_;     dst = ".claude\skills\dev-cycle\templates\task-operator.md" },
    @{ src = "claude\scripts\rx.py";                  root = $home_;     dst = ".claude\scripts\rx.py" },
    @{ src = "agents\skills\implementer\SKILL.md";    root = $home_;     dst = ".agents\skills\implementer\SKILL.md" },
    @{ src = "agents\skills\verifier\SKILL.md";       root = $home_;     dst = ".agents\skills\verifier\SKILL.md" },
    @{ src = "agents\skills\operator\SKILL.md";       root = $home_;     dst = ".agents\skills\operator\SKILL.md" },
    @{ src = "roles\explore.md";                      root = $home_;     dst = ".claude\roles\explore.md" },

    # Codex 侧。rx.py、explore 档案和模板各装两份，让 Codex 那边不依赖 ~/.claude 是否存在。
    @{ src = "codex\skills\dev-cycle\SKILL.md";       root = $codexHome; dst = "skills\dev-cycle\SKILL.md";  codex = $true },
    @{ src = "templates\task-implementer.md";         root = $codexHome; dst = "skills\dev-cycle\templates\task-implementer.md"; codex = $true },
    @{ src = "templates\task-verifier.md";            root = $codexHome; dst = "skills\dev-cycle\templates\task-verifier.md";    codex = $true },
    @{ src = "templates\task-explore.md";             root = $codexHome; dst = "skills\dev-cycle\templates\task-explore.md";     codex = $true },
    @{ src = "templates\task-operator.md";            root = $codexHome; dst = "skills\dev-cycle\templates\task-operator.md";    codex = $true },
    @{ src = "claude\scripts\rx.py";                  root = $codexHome; dst = "scripts\rx.py";              codex = $true },
    @{ src = "roles\explore.md";                      root = $codexHome; dst = "roles\explore.md";           codex = $true }
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
Write-Host "装完了。自检（不花钱，两个执行后端一起查）：" -ForegroundColor Green
Write-Host "    python ~/.claude/scripts/rx.py doctor"
Write-Host ""
Write-Host "只想用其中一个后端就固定下来：" -ForegroundColor Green
Write-Host '    $env:DEVCYCLE_BACKEND = "codex"     # 或 "reasonix"'
