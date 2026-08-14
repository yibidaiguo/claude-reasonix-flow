"""从 Claude（或 Codex）驱动一个**执行后端**干活的薄封装（全局版，不绑定任何项目）。

分工：调用方做设计审查和验收（难判断），执行后端做实现和跑门禁（机械活）。
这个脚本是两者之间的接口。

支持两个执行后端，命令行是同一套：

    reasonix   走 `reasonix subagent run <角色>`，角色档案在 ~/.agents/skills/
    codex      走 `codex exec`，角色档案由本脚本读出来拼进提示词

用法：
    python ~/.claude/scripts/rx.py sub implementer - < 任务文件
    python ~/.claude/scripts/rx.py sub verifier   - < 任务文件
    python ~/.claude/scripts/rx.py run            - < 任务文件
    python ~/.claude/scripts/rx.py doctor                  # 环境自检，不花钱

    任务写 - 就从 stdin 读。任务长、带中文引号和换行时一律用这个，
    别在命令行里转义——必坏。

选后端：
    --backend reasonix|codex|auto     默认 auto
    环境变量 DEVCYCLE_BACKEND         同上，--backend 优先
    auto 的顺序：找得到 reasonix 就用 reasonix，否则用 codex。

    **切后端不用跟着改 --model**：每个后端各带一个默认模型（见 DEFAULT_MODEL），
    reasonix 默认 flash 档、codex 默认 luna。所以命令行里通常一个 --model 都不用写，
    只翻 --backend 就够了。

    **档位也不用你记**：implementer 自动走 pro 档（reasonix）/ sol 档（codex），
    见 ROLE_MODEL；explore 和 verifier 留在便宜档。派活时不要手写 --model，
    `[rx]` 行的 model= 会告诉你这次实际用的是哪个。

两个后端都吃的开关：
    --dir PATH         项目根，默认从当前目录往上找 .git / 项目指令文件
    --model REF        覆盖本次的模型。收简称：reasonix 认 flash/pro，codex 认
                       luna/sol/terra；表里没有的原样透传，后端认什么就能填什么。
                       想改默认值不必动代码，设 DEVCYCLE_MODEL_REASONIX /
                       DEVCYCLE_MODEL_CODEX 就行。
    --max-chars N      裁剪回给调用方的正文，0 = 不裁（默认）。见下方"成本在哪一侧"
    --timeout SEC      墙钟超时，默认 1800

只有 reasonix 吃的：
    --max-steps N      卡工具调用轮数，防跑飞。**平时别设**：Reasonix 1.25 起
                       「agent step limits」已废弃（内置提示 "Deprecated agent step
                       limits were removed."），不传就是 automatic，等价于传 0。
                       设成正数只会人为掐断长任务，让它停在半截的 todo 上。
    --permission-mode  manual|ask|auto|acceptEdits|dontAsk|bypassPermissions
                       无头调用不能用 plan（它要交互式会话）

只有 codex 吃的：
    --sandbox MODE     read-only|workspace-write|danger-full-access
                       不给就按角色定：explore=read-only，其余=workspace-write
    --keep-mcp         默认会用 -c mcp_servers={} 把 MCP 服务器全关掉（执行角色只需要
                       文件和 shell，挂着的 MCP 只会拖慢启动、白烧上下文）。要用就加这个。
    --codex-config K=V 透传给 codex 的 -c，可重复
    --codex-home PATH  给执行后端单独指一个 CODEX_HOME。不给时按这个顺序找：
                       DEVCYCLE_CODEX_HOME → ~/.codex-rx（存在就用）→ CODEX_HOME → ~/.codex
                       日常那份 config.toml 被 GUI 写进了当前 codex 版本不认的字段时，
                       建一个 ~/.codex-rx 放精简配置就能绕开，不必去改那份。
    --role-file PATH   直接指定角色档案文件，跳过下面的搜索顺序

codex 侧的角色档案按这个顺序找（第一个存在的赢）：
    --role-file → $DEVCYCLE_ROLES/<角色>.md → ~/.agents/skills/<角色>/SKILL.md
    → $CODEX_HOME/roles/<角色>.md → ~/.claude/roles/<角色>.md → <本脚本>/../roles/<角色>.md

implementer 和 verifier 的档案两个后端共用 ~/.agents/skills/ 那份，不另存一遍，
省得改一处漏一处。explore 是例外：Reasonix 自带 builtin explore，档案只为 codex 准备，
所以放在 roles/ 里，不进 ~/.agents/skills/（放进去会盖掉 Reasonix 的 builtin）。

为什么不直接敲后端的可执行文件：
1. reasonix 装在带版本号的目录里，升级后路径会变。这里每次现解析最新版。
2. reasonix 无头调用必须显式给 --permission-mode，否则会卡在等审批上直到超时。
3. codex 没有子代理档案这个概念，角色约束得由调用方拼进提示词——这一步在这里做。
4. 两个后端的返回格式完全不同（一个 JSON 信封 / 一个 JSONL 事件流），
   这里统一成"正文走 stdout、账单走 stderr 的 [rx] 行"。

工作区哨兵：跑 verifier / explore 这类**不该改代码**的角色时，本脚本在跑之前和跑完各取
一次 `git diff` 指纹。对不上就在 [rx] 行标 tree=modified 并在 stderr 打警告——
验证过程改了源码，那一轮验证就是作废的，这事不能靠角色档案里写一句"不许改"来保证。

成本在哪一侧：执行后端跑的是便宜档（Reasonix 走 deepseek，¥1~¥3 每 M 输入），一次调用
的 ~14k~24k 系统提示合人民币几分钱。真正贵的是**调用方**的上下文——子代理返回的每一个
字都会进那边，并在后续每轮重发。所以省钱的手段不是少派活、把任务合并成大块，而是
**控制回流的正文长度**：用 --max-chars 裁 implementer 那种啰嗦的叙述型返回。

--max-chars 默认关闭，必须显式打开。理由是漏裁只多花钱，误裁会吃掉失败证据——
verifier 的返回（一张表加 FAIL 原文）本来就是压缩过的，别给它设上限。
裁掉的部分不会丢，完整正文落到临时文件，路径打在 [rx] 那行里。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# 项目根的判定依据，按优先级。找不到就用当前目录。
ROOT_MARKERS = (".git", "AGENTS.md", "CLAUDE.md", "reasonix.toml")

# 无头实现要写代码、跑自查，得能落盘。auto 是官方的 -y，自动批准普通写操作。
# 别用 bypassPermissions——那个连 deny 规则都不看。
DEFAULT_PERMISSION_MODE = "auto"

# 每个后端的默认模型。切后端时不用跟着改 --model，这张表替你换。
# 优先级：--model > DEVCYCLE_MODEL_REASONIX / DEVCYCLE_MODEL_CODEX 环境变量 > 这张表。
DEFAULT_MODEL = {
    "reasonix": "deepseek/deepseek-v4-flash",
    "codex": "gpt-5.6-luna",
}

# 角色 → 档位。比 DEFAULT_MODEL 更具体，命中就用它，优先级见 resolve_model。
# 这张表存在的理由：档位纪律不该靠人在每次派活时记得加 --model。
#
# implementer 走 pro：多文件改动上 flash 档会漏改、会把红灯测试直接改绿，
# 返工一轮要重写任务书 + 重跑门禁，成本远超 pro 那点差价。
# explore / verifier 留在 flash：一个是撒网找线索、一个是跑命令贴原文，
# 都不吃推理深度，升档纯属烧钱。
ROLE_MODEL = {
    "reasonix": {"implementer": "pro"},
    "codex": {"implementer": "sol"},
}

# --model 收简称，省得每次敲全名。表里没有的原样透传给后端，
# 所以后端认的任何模型名都能用，这里只是快捷方式。
# 名字来自各自的模型目录，换了 provider 就得跟着改。
MODEL_ALIAS = {
    "reasonix": {
        "flash": "deepseek/deepseek-v4-flash",
        "pro": "deepseek/deepseek-v4-pro",
    },
    "codex": {
        "luna": "gpt-5.6-luna",
        "sol": "gpt-5.6-sol",
        "terra": "gpt-5.6-terra",
    },
}

# codex 侧角色 → 沙箱档位。没列的按 DEFAULT_CODEX_SANDBOX。
#
# verifier 给的是 workspace-write 而不是 read-only：门禁本身要落盘（构建产物、
# .pytest_cache、node_modules/.cache），read-only 会把正经门禁一起拦死，那就白跑了。
# 「不许改源码」这条改由跑完的 git 指纹比对来兜（见 tree_fingerprint），
# 那比沙箱档位更贴合真实要求——允许写缓存，但改了源码一定被抓出来。
CODEX_ROLE_SANDBOX = {
    "explore": "read-only",
    "verifier": "workspace-write",
    "implementer": "workspace-write",
}
DEFAULT_CODEX_SANDBOX = "workspace-write"

# 这些角色跑完要比对工作区指纹。它们的活是"看"和"跑"，不是"改"。
TREE_GUARDED_ROLES = ("verifier", "explore")


# ──────────────────────────────────────────────────────────────────────
# 后端定位
# ──────────────────────────────────────────────────────────────────────

def find_reasonix_cli() -> Path | None:
    """定位 reasonix CLI。顺序：环境变量 > PATH > 常见安装位置。找不到返回 None。"""
    override = os.environ.get("REASONIX_CLI")
    if override and Path(override).exists():
        return Path(override)

    on_path = shutil.which("reasonix-cli") or shutil.which("reasonix")
    if on_path:
        return Path(on_path)

    search_roots = [
        Path(r"D:\SoftWare\Reasonix\versions"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Reasonix" / "versions",
        Path(os.environ.get("PROGRAMFILES", "")) / "Reasonix" / "versions",
        Path.home() / ".local" / "share" / "reasonix" / "versions",
    ]

    def version_key(path: Path) -> tuple[int, ...]:
        parts = []
        for chunk in path.parent.name.lstrip("v").split("."):
            digits = "".join(c for c in chunk if c.isdigit())
            parts.append(int(digits) if digits else 0)
        return tuple(parts)

    found = []
    for root in search_roots:
        if not root.is_dir():
            continue
        for name in ("reasonix-cli.exe", "reasonix-cli", "reasonix.exe", "reasonix"):
            found += [p for p in root.glob(f"v*/{name}") if p.is_file()]
    if found:
        return max(found, key=version_key)

    return None


def find_codex_cli() -> Path | None:
    """定位 codex CLI。顺序：环境变量 > PATH。找不到返回 None。"""
    override = os.environ.get("CODEX_CLI")
    if override and Path(override).exists():
        return Path(override)
    on_path = shutil.which("codex")
    return Path(on_path) if on_path else None


def codex_home(explicit: str | None = None) -> Path:
    """定位执行后端要用的 Codex 家目录。

    顺序：--codex-home > DEVCYCLE_CODEX_HOME > ~/.codex-rx（存在就用）> CODEX_HOME > ~/.codex

    `~/.codex-rx` 那一条是给"日常那份配置无头跑不了"的机器准备的：codex 桌面端和各类
    GUI 会往 ~/.codex/config.toml 里写命令行这版 codex 不认的字段，整份配置就加载失败。
    那份是交互式用的，不该为了无头调用去改它。建一个 ~/.codex-rx 放一份精简配置，
    两边各过各的；目录不存在就走原来的老路，不影响没这个问题的机器。
    """
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("DEVCYCLE_CODEX_HOME")
    if env:
        return Path(env).expanduser()
    dedicated = Path.home() / ".codex-rx"
    if dedicated.is_dir():
        return dedicated
    env = os.environ.get("CODEX_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".codex"


def resolve_backend(explicit: str | None) -> str:
    """--backend > DEVCYCLE_BACKEND > auto（有 reasonix 用 reasonix，否则 codex）。"""
    choice = (explicit or os.environ.get("DEVCYCLE_BACKEND") or "auto").lower()
    if choice in ("reasonix", "codex"):
        return choice
    if choice != "auto":
        raise SystemExit(f"不认识的后端：{choice}（只有 reasonix / codex / auto）")

    if find_reasonix_cli():
        return "reasonix"
    if find_codex_cli():
        return "codex"
    raise SystemExit(
        "reasonix 和 codex 都没找到。\n"
        "  装了 Reasonix：设 REASONIX_CLI 指向可执行文件，或把它加进 PATH。\n"
        "  装了 Codex：  把 codex 加进 PATH，或设 CODEX_CLI。"
    )


def resolve_model(backend: str, explicit: str | None, role: str = "") -> str | None:
    """--model > DEVCYCLE_MODEL_<后端> > ROLE_MODEL[角色] > DEFAULT_MODEL 表。

    简称按后端各自的别名表展开。角色档位排在环境变量之后：显式指定的东西
    （命令行、环境变量）永远压得过这张表，否则想临时降档就没办法了。
    """
    name = explicit or os.environ.get(f"DEVCYCLE_MODEL_{backend.upper()}") \
        or ROLE_MODEL.get(backend, {}).get(role) \
        or DEFAULT_MODEL.get(backend)
    if not name:
        return None
    return MODEL_ALIAS.get(backend, {}).get(name.lower(), name)


def role_model_line(backend: str) -> str:
    """doctor 里那一行：把角色档位显出来，省得靠人记得 implementer 该走 pro。"""
    overridden = os.environ.get(f"DEVCYCLE_MODEL_{backend.upper()}")
    if overridden:
        return (f"全被环境变量 DEVCYCLE_MODEL_{backend.upper()}={overridden} 盖掉了"
                "（角色档位不生效，想恢复就 unset 它）")
    roles = ROLE_MODEL.get(backend, {})
    if not roles:
        return "无角色特例，全部走上面这个默认档"
    shown = "，".join(f"{r}={resolve_model(backend, None, r)}" for r in sorted(roles))
    return f"{shown}；其余角色走上面这个默认档"


def find_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        if any((candidate / marker).exists() for marker in ROOT_MARKERS):
            return candidate
    return here


# ──────────────────────────────────────────────────────────────────────
# 角色档案（只有 codex 后端要用；reasonix 自己按名字查档案）
# ──────────────────────────────────────────────────────────────────────

def role_search_paths(role: str, home: Path) -> list[Path]:
    here = Path(__file__).resolve().parent
    paths = []
    roles_env = os.environ.get("DEVCYCLE_ROLES")
    if roles_env:
        paths.append(Path(roles_env).expanduser() / f"{role}.md")
    paths += [
        Path.home() / ".agents" / "skills" / role / "SKILL.md",
        home / "roles" / f"{role}.md",
        Path.home() / ".claude" / "roles" / f"{role}.md",
        here.parent / "roles" / f"{role}.md",
    ]
    return paths


def find_role_file(role: str, home: Path, override: str | None) -> Path:
    if override:
        p = Path(override).expanduser()
        if not p.is_file():
            raise SystemExit(f"--role-file 指的文件不存在：{p}")
        return p

    candidates = role_search_paths(role, home)
    for p in candidates:
        if p.is_file():
            return p

    tried = "\n".join(f"    {p}" for p in candidates)
    raise SystemExit(
        f"codex 后端找不到角色 `{role}` 的档案。找过这些位置：\n{tried}\n"
        "  跑一遍 install.ps1 把档案铺好，或者用 --role-file 直接指一个。"
    )


def strip_frontmatter(text: str) -> str:
    """角色档案是 SKILL.md 格式，开头那段 YAML frontmatter 对模型没用，去掉。"""
    if not text.startswith("---"):
        return text
    lines = text.splitlines()
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1:]).lstrip("\n")
    return text


def compose_role_prompt(role: str, role_text: str, task: str) -> str:
    """把角色档案和任务拼成一条提示词。

    codex 没有子代理档案这个概念，角色约束只能随提示词一起进去。顺序是角色在前、
    任务在后——任务里的具体约束要能压过档案里的通用说法。
    """
    return (
        f"你现在以 `{role}` 子代理的身份工作。下面先给你的角色档案，再给本次任务。\n"
        "角色档案里的规则优先于你自己的判断；任务里写死的具体约束优先于档案里的通用说法。\n"
        f"\n===== 角色档案：{role} =====\n\n{role_text.strip()}\n"
        f"\n===== 本次任务 =====\n\n{task.strip()}\n"
    )


# ──────────────────────────────────────────────────────────────────────
# 工作区哨兵
# ──────────────────────────────────────────────────────────────────────

def tree_fingerprint(root: Path) -> tuple[str, set[str]] | None:
    """取工作区已跟踪文件的改动指纹 (diff 哈希, 文件名集合)。

    不是 git 仓库、或者 git 不可用时返回 None（这时哨兵自动关掉，不报假警）。
    只看已跟踪文件：门禁跑起来会造一堆未跟踪的构建产物，那些不算"改了源码"。
    比的是 diff 全文的哈希而不只是文件名——implementer 已经改过的文件被 verifier
    再改一次，文件名集合是不变的，只有内容哈希抓得住。
    """
    def git(*args: str) -> str | None:
        try:
            p = subprocess.run(
                ["git", "-C", str(root), *args],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=120,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return p.stdout if p.returncode == 0 else None

    if git("rev-parse", "--git-dir") is None:
        return None

    # 有 HEAD 就比到 HEAD（已暂存 + 未暂存一起覆盖）；空仓库退回只比未暂存。
    base = ["diff", "HEAD"] if git("rev-parse", "--verify", "HEAD") is not None else ["diff"]
    text = git(*base)
    names = git(*base, "--name-only")
    if text is None or names is None:
        return None
    digest = hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()
    return digest, {n for n in names.splitlines() if n.strip()}


def report_tree_drift(role: str, before, after) -> str | None:
    """比对前后指纹，返回给 [rx] 行用的 tree= 值；有漂移时往 stderr 打警告。"""
    if before is None or after is None:
        return None
    if before[0] == after[0]:
        return "clean"

    added = sorted(after[1] - before[1])
    detail = (
        "新出现改动的文件：" + ", ".join(added)
        if added
        else "文件清单没变，是已有改动的文件内容又被动了"
    )
    print(
        f"\n[rx] 警告：`{role}` 运行期间工作区被改动了——本轮结果按作废处理。\n"
        f"     {detail}\n"
        f"     这个角色只该跑命令和读文件。要么让它重跑一次，要么查清是哪条命令写了文件。\n"
        f"     （`git diff HEAD` 看具体改了什么）",
        file=sys.stderr,
    )
    return "modified"


# ──────────────────────────────────────────────────────────────────────
# 回流正文处理
# ──────────────────────────────────────────────────────────────────────

def clip(text: str, limit: int) -> tuple[str, Path | None]:
    """超长正文保头保尾、中间折叠，完整版落到临时文件。

    尾部留得比头部多：implementer 的返回是按"改了哪些文件 → 证据 → 没做的部分 →
    新发现的 Bug → 撞到的约束冲突"排的，越靠后越是调用方必须看到的东西。
    """
    if limit <= 0 or len(text) <= limit:
        return text, None

    fd, name = tempfile.mkstemp(prefix="rx-out-", suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8", errors="replace") as f:
        f.write(text)
    full = Path(name)

    head = limit * 2 // 5
    tail = limit - head
    dropped = len(text) - limit
    fold = f"\n\n... [rx 折叠了中间 {dropped} 字，完整正文见 {full}] ...\n\n"
    return text[:head] + fold + text[-tail:], full


def emit(body: str, meter: list[str], max_chars: int) -> Path | None:
    """正文走 stdout，账单走 stderr 的 [rx] 行。两个后端共用。"""
    clipped, full = clip(body, max_chars)
    if clipped:
        print(clipped)
    sys.stdout.flush()  # 不 flush 的话账单行会插到正文前面，两个流缓冲策略不一样
    if full:
        meter.append(f"full={full}")
    print(f"\n[rx] {' '.join(meter)}", file=sys.stderr)
    return full


# ──────────────────────────────────────────────────────────────────────
# reasonix 后端
# ──────────────────────────────────────────────────────────────────────

def build_reasonix_argv(args, cli: Path, root: Path, task: str, model: str | None) -> list[str]:
    argv = [str(cli)]
    if args.mode == "sub":
        argv += ["subagent", "run", args.name]
    else:
        argv += ["run"]
    argv += ["--dir", str(root)]
    if model:
        argv += ["--model", model]
    if args.mode != "sub":
        # subagent run 不吃 --output-format / --permission-mode，档案自己带权限。
        argv += ["--output-format", "json", "--permission-mode", args.permission_mode]
    if args.max_steps:
        argv += ["--max-steps", str(args.max_steps)]
    argv += [task]
    return argv


def report_reasonix_envelope(payload: dict, max_chars: int, model: str | None) -> int:
    """run 模式返回的是 JSON 信封：正文给人看，账单单独一行，错误走 stderr。"""
    text = (payload.get("result") or "").strip()
    usage = payload.get("usage") or {}

    if payload.get("is_error"):
        # 失败正文不裁——那正是调用方要看的东西。
        print(f"执行失败：{text}", file=sys.stderr)
        return 1

    meter = [
        "backend=reasonix",
        f"model={model}",
        f"in={usage.get('input_tokens', 0)}",
        f"out={usage.get('output_tokens', 0)}",
        f"cache_read={usage.get('cache_read_input_tokens', 0)}",
    ]
    if payload.get("total_cost_usd") is not None:
        meter.append(f"cost=${payload['total_cost_usd']}")
    if payload.get("session_id"):
        meter.append(f"session={payload['session_id']}")
    emit(text, meter, max_chars)
    return 0


def run_reasonix(args, root: Path) -> int:
    cli = find_reasonix_cli()
    if cli is None:
        raise SystemExit(
            "没找到 reasonix CLI。设 REASONIX_CLI 指向可执行文件，或把它加进 PATH。\n"
            "  只装了 Codex 就加 --backend codex（或设 DEVCYCLE_BACKEND=codex）。"
        )
    if args.permission_mode == "plan":
        raise SystemExit("plan 模式要求交互式会话，无头调用用不了")

    role = args.name if args.mode == "sub" else ""
    model = resolve_model("reasonix", args.model, role)
    guard = role in TREE_GUARDED_ROLES
    before = tree_fingerprint(root) if guard else None

    started = time.monotonic()
    try:
        proc = subprocess.run(
            build_reasonix_argv(args, cli, root, args.task_text, model),
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=args.timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"Reasonix 超时（{args.timeout}s）未返回，已放弃。", file=sys.stderr)
        return 1
    elapsed = time.monotonic() - started

    stdout = (proc.stdout or "").strip()
    drift = report_tree_drift(role, before, tree_fingerprint(root)) if guard else None

    # subagent run 是纯文本输出，run --output-format json 才是信封。
    if args.mode == "sub":
        if proc.returncode != 0:
            print((proc.stderr or "").strip(), file=sys.stderr)
        # subagent run 不支持 --output-format json，拿不到 usage/cost 信封，
        # 所以这里只能给出规模和耗时，报不了钱。要账单就得走 run 模式，
        # 或者换 codex 后端（那边 turn.completed 事件自带 usage）。
        meter = [
            "backend=reasonix",
            f"agent={args.name}",
            f"model={model}",
            # task= 是派出去的任务书字数，chars= 是回流字数。两个摆在一起，
            # 调用方一眼能看出这轮是"任务写虚了"还是"回流太啰嗦"。
            f"task={len(args.task_text)}",
            f"chars={len(stdout)}",
            f"elapsed={elapsed:.0f}s",
            f"exit={proc.returncode}",
        ]
        if drift:
            meter.append(f"tree={drift}")
        emit(stdout, meter, args.max_chars)
        return proc.returncode

    try:
        return report_reasonix_envelope(json.loads(stdout), args.max_chars, model)
    except json.JSONDecodeError:
        print(stdout or "(Reasonix 没有任何输出)")
        print((proc.stderr or "").strip(), file=sys.stderr)
        return proc.returncode or 1


# ──────────────────────────────────────────────────────────────────────
# codex 后端
# ──────────────────────────────────────────────────────────────────────

def codex_sandbox_for(args) -> str:
    if args.sandbox:
        return args.sandbox
    if args.mode == "sub":
        return CODEX_ROLE_SANDBOX.get(args.name, DEFAULT_CODEX_SANDBOX)
    return DEFAULT_CODEX_SANDBOX


def build_codex_argv(args, cli: Path, root: Path, last_msg: Path, model: str | None) -> list[str]:
    argv = [
        str(cli), "exec",
        "--json",
        "--skip-git-repo-check",
        "-C", str(root),
        "-s", codex_sandbox_for(args),
        "-o", str(last_msg),
    ]
    if model:
        argv += ["-m", model]
    if not args.keep_mcp:
        # 执行角色只需要文件和 shell。挂着的 MCP 服务器每次都要连、要塞工具定义，
        # 连不上还会按 startup_timeout 干等——白花时间和上下文。
        argv += ["-c", "mcp_servers={}"]
    for override in args.codex_config or []:
        argv += ["-c", override]
    argv += ["-"]  # 提示词从 stdin 读
    return argv


def parse_codex_events(stdout: str) -> dict:
    """把 `codex exec --json` 的 JSONL 事件流收拢成一份结果。

    0.134 的事件形状是 {"type": "..."} 那种；更早的版本是 {"id":.., "msg":{"type":..}}。
    两种都认，认不出来的行直接跳过——事件流的格式会变，别让它把整次调用弄失败。
    """
    out = {
        "message": "",
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "commands": 0,
        "errors": [],
    }
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue

        # 老形状：真正的事件裹在 msg 里。
        if "msg" in ev and isinstance(ev.get("msg"), dict):
            ev = ev["msg"]

        kind = ev.get("type") or ""

        if kind in ("item.completed", "item.started"):
            item = ev.get("item") or {}
            itype = item.get("type")
            if itype == "agent_message" and kind == "item.completed":
                out["message"] = item.get("text") or out["message"]
            elif itype == "command_execution" and kind == "item.started":
                out["commands"] += 1
        elif kind == "agent_message":
            out["message"] = ev.get("message") or out["message"]
        elif kind in ("turn.completed", "turn.failed"):
            usage = ev.get("usage") or {}
            out["input_tokens"] += usage.get("input_tokens", 0) or 0
            out["cached_input_tokens"] += usage.get("cached_input_tokens", 0) or 0
            out["output_tokens"] += usage.get("output_tokens", 0) or 0
            out["reasoning_tokens"] += usage.get("reasoning_output_tokens", 0) or 0
            if kind == "turn.failed":
                err = ev.get("error") or {}
                out["errors"].append(str(err.get("message") or err or "turn failed"))
        elif kind == "token_count":
            info = (ev.get("info") or {}).get("total_token_usage") or {}
            out["input_tokens"] = info.get("input_tokens", out["input_tokens"])
            out["cached_input_tokens"] = info.get(
                "cached_input_tokens", out["cached_input_tokens"])
            out["output_tokens"] = info.get("output_tokens", out["output_tokens"])
        elif kind == "error":
            out["errors"].append(str(ev.get("message") or ev))
    return out


def run_codex(args, root: Path) -> int:
    cli = find_codex_cli()
    if cli is None:
        raise SystemExit(
            "没找到 codex CLI。把 codex 加进 PATH，或者设 CODEX_CLI 指向可执行文件。\n"
            "  只装了 Reasonix 就加 --backend reasonix（或设 DEVCYCLE_BACKEND=reasonix）。"
        )

    home = codex_home(args.codex_home)
    role = args.name if args.mode == "sub" else ""
    model = resolve_model("codex", args.model, role)

    if role:
        role_file = find_role_file(role, home, args.role_file)
        role_text = strip_frontmatter(
            role_file.read_text(encoding="utf-8", errors="replace"))
        prompt = compose_role_prompt(role, role_text, args.task_text)
    else:
        prompt = args.task_text

    if args.max_steps:
        print("[rx] 提示：codex 后端没有 --max-steps 这个概念，已忽略。", file=sys.stderr)

    # 一律显式钉住，别让子进程按自己的 CODEX_HOME 走——上面那套优先级就白算了。
    env = os.environ.copy()
    env["CODEX_HOME"] = str(home)

    fd, name = tempfile.mkstemp(prefix="rx-codex-last-", suffix=".txt")
    os.close(fd)
    last_msg = Path(name)

    guard = role in TREE_GUARDED_ROLES
    before = tree_fingerprint(root) if guard else None

    started = time.monotonic()
    try:
        proc = subprocess.run(
            build_codex_argv(args, cli, root, last_msg, model),
            input=prompt,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=args.timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        last_msg.unlink(missing_ok=True)
        print(f"Codex 超时（{args.timeout}s）未返回，已放弃。", file=sys.stderr)
        return 1
    elapsed = time.monotonic() - started

    parsed = parse_codex_events(proc.stdout or "")

    # 正文优先取 -o 落的最终消息（版本最稳），拿不到再退回事件流里最后一条 agent_message。
    body = ""
    try:
        body = last_msg.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        pass
    finally:
        last_msg.unlink(missing_ok=True)
    if not body:
        body = parsed["message"].strip()

    drift = report_tree_drift(role, before, tree_fingerprint(root)) if guard else None

    if proc.returncode != 0 or parsed["errors"]:
        stderr_tail = (proc.stderr or "").strip()
        if stderr_tail:
            print(stderr_tail, file=sys.stderr)
        for e in parsed["errors"]:
            print(f"Codex 报错：{e}", file=sys.stderr)

    meter = [
        "backend=codex",
        f"agent={role or 'run'}",
        f"model={model}",
        f"task={len(args.task_text)}",
        f"chars={len(body)}",
        f"elapsed={elapsed:.0f}s",
        f"exit={proc.returncode}",
        f"in={parsed['input_tokens']}",
        f"cached={parsed['cached_input_tokens']}",
        f"out={parsed['output_tokens']}",
        f"cmds={parsed['commands']}",
        f"sandbox={codex_sandbox_for(args)}",
    ]
    if drift:
        meter.append(f"tree={drift}")
    # 失败正文不裁——那正是调用方要看的东西。
    emit(body, meter, 0 if proc.returncode != 0 else args.max_chars)
    return proc.returncode


# ──────────────────────────────────────────────────────────────────────
# doctor
# ──────────────────────────────────────────────────────────────────────

def doctor_reasonix(root: Path) -> None:
    cli = find_reasonix_cli()
    print("── reasonix ──")
    if cli is None:
        print("  cli      : （没找到，这个后端用不了）")
        return
    print(f"  cli      : {cli}")
    # doctor 不吃 --dir（只有 session / hook / task 子命令吃），只能靠 cwd 决定项目根。
    try:
        proc = subprocess.run(
            [str(cli), "doctor", "--json"],
            cwd=str(root), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120,
        )
        d = json.loads(proc.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        print("  状态     : doctor 跑不通或返回不是 JSON")
        return
    print(f"  config   : {d.get('config', {}).get('source_path')}")
    print(f"  model    : {resolve_model('reasonix', None)}"
          f"（本桥默认；Reasonix 自己的默认是 {d.get('config', {}).get('default_model')}）")
    print(f"  档位     : {role_model_line('reasonix')}")
    print(f"  perm     : {d.get('permission')}")
    print(f"  write    : {d.get('sandbox', {}).get('write_roots')}")
    keys = [p["name"] for p in d.get("providers", []) if p.get("key_present")]
    print(f"  providers: {keys or '（没有可用密钥）'}")
    for w in d.get("warnings") or []:
        print(f"  warn     : {w}")


def doctor_codex(root: Path, home: Path, role_file_override: str | None) -> None:
    cli = find_codex_cli()
    print("── codex ──")
    if cli is None:
        print("  cli      : （没找到，这个后端用不了）")
        return
    print(f"  cli      : {cli}")
    dedicated = " ← 执行后端专用，日常那份 ~/.codex 不受影响" \
        if home == Path.home() / ".codex-rx" else ""
    print(f"  home     : {home}{dedicated}")
    print(f"  model    : {resolve_model('codex', None)}（本桥默认）")
    print(f"  档位     : {role_model_line('codex')}")

    env = os.environ.copy()
    env["CODEX_HOME"] = str(home)
    try:
        proc = subprocess.run(
            [str(cli), "doctor", "--json"],
            cwd=str(root), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=180, env=env,
        )
        raw = proc.stdout or ""
        start = raw.find("{")
        d = json.loads(raw[start:]) if start >= 0 else {}
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        d = {}

    if not d:
        print("  状态     : codex doctor 跑不通或返回不是 JSON")
    else:
        print(f"  version  : {d.get('codexVersion')}")
        print(f"  overall  : {d.get('overallStatus')}")
        bad = [c for c in (d.get("checks") or {}).values() if c.get("status") != "ok"]
        for c in bad:
            print(f"  {c.get('status'):<9}: {c.get('id')} —— {c.get('summary')}")
            if c.get("remediation"):
                print(f"             ↳ {c['remediation']}")
        if not bad:
            print("  checks   : 全绿")

    # config.toml 加载不了是最常见也最难自己看出来的坑：GUI 写进去的字段，
    # 命令行这版 codex 不一定认。上面 doctor 的 config.load 会报，这里再钉一句出路。
    print("  roles    :")
    for role in ("implementer", "verifier", "explore"):
        try:
            p = find_role_file(role, home, role_file_override)
            print(f"    {role:<12}: {p}")
        except SystemExit:
            print(f"    {role:<12}: （找不到档案，跑 install.ps1 铺一下）")


def run_doctor(args, root: Path) -> int:
    print(f"root     : {root}")
    try:
        chosen = resolve_backend(args.backend)
    except SystemExit as e:
        chosen = "（都没找到）"
        print(f"backend  : {chosen}")
        print(str(e))
        return 1
    print(f"backend  : {chosen}"
          f"{'（--backend 指定）' if args.backend else '（auto）'}")
    print()
    doctor_reasonix(root)
    print()
    doctor_codex(root, codex_home(args.codex_home), args.role_file)
    return 0


# ──────────────────────────────────────────────────────────────────────

def main() -> int:
    # 三个流都必须钉成 UTF-8。Windows 上默认是 GBK：
    # - stdin 不钉，管道进来的中文任务会被按 GBK 解码打碎，模型收到的是残句；
    # - stdout/stderr 不钉，后端返回的中文和账单行写出去会抛 UnicodeEncodeError。
    # 这三个都踩过，别删。
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(add_help=True)
    sub = parser.add_subparsers(dest="mode", required=True)

    p_sub = sub.add_parser("sub", help="派一个角色（implementer / verifier / explore …）")
    p_sub.add_argument("name")
    p_sub.add_argument("task")

    p_run = sub.add_parser("run", help="不带角色，直接跑一个任务")
    p_run.add_argument("task")

    p_doc = sub.add_parser("doctor", help="环境自检，不花钱")

    for p in (p_sub, p_run):
        p.add_argument("--model", default=None,
                       help="覆盖本次模型，收简称（flash/pro、luna/sol/terra）。"
                            "不给就用该后端的默认模型")
        p.add_argument("--max-steps", type=int, default=0, help="仅 reasonix")
        p.add_argument("--max-chars", type=int, default=0)
        p.add_argument("--permission-mode", default=DEFAULT_PERMISSION_MODE,
                       help="仅 reasonix")
        p.add_argument("--timeout", type=int, default=1800)
        p.add_argument("--sandbox", default=None,
                       choices=["read-only", "workspace-write", "danger-full-access"],
                       help="仅 codex，不给就按角色定")
        p.add_argument("--keep-mcp", action="store_true",
                       help="仅 codex，保留 config.toml 里的 MCP 服务器")
        p.add_argument("--codex-config", action="append", default=None,
                       metavar="K=V", help="仅 codex，透传给 codex 的 -c，可重复")
    for p in (p_sub, p_run, p_doc):
        p.add_argument("--dir", default=None)
        p.add_argument("--backend", default=None, choices=["reasonix", "codex", "auto"])
        p.add_argument("--codex-home", default=None)
        p.add_argument("--role-file", default=None, help="仅 codex")

    args = parser.parse_args()
    root = find_root(args.dir)

    if args.mode == "doctor":
        return run_doctor(args, root)

    args.task_text = sys.stdin.read().strip() if args.task == "-" else args.task.strip()
    if not args.task_text:
        raise SystemExit("任务是空的")

    backend = resolve_backend(args.backend)
    if backend == "codex":
        return run_codex(args, root)
    return run_reasonix(args, root)


if __name__ == "__main__":
    sys.exit(main())
