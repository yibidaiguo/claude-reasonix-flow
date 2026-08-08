"""从 Claude 驱动 Reasonix 干活的薄封装（全局版，不绑定任何项目）。

分工：Claude 做设计审查和验收（难判断），Reasonix 做实现和跑门禁（机械活）。
这个脚本是两者之间的接口。

用法：
    python ~/.claude/scripts/rx.py sub implementer - < 任务文件
    python ~/.claude/scripts/rx.py sub verifier   - < 任务文件
    python ~/.claude/scripts/rx.py run            - < 任务文件
    python ~/.claude/scripts/rx.py doctor                  # 环境自检，不花钱

    任务写 - 就从 stdin 读。任务长、带中文引号和换行时一律用这个，
    别在命令行里转义——必坏。

常用开关：
    --dir PATH         项目根，默认从当前目录往上找 .git / 项目指令文件
    --model NAME       provider 名，默认 reasonix 配置里的 default_model
    --max-steps N      卡工具调用轮数，防跑飞
    --permission-mode  manual|ask|auto|acceptEdits|dontAsk|bypassPermissions
                       无头调用不能用 plan（它要交互式会话）
    --timeout SEC      墙钟超时，默认 1800

为什么不直接敲 reasonix-cli.exe：
1. 它装在带版本号的目录里，升级后路径会变。这里每次现解析最新版。
2. 无头调用必须显式给 --permission-mode，否则会卡在等审批上直到超时。
3. 返回是 JSON 信封，得挑出 result 字段、按 is_error 定退出码，顺便把花费打出来。

成本提醒：一次调用光系统提示和环境摘要就 ~24k 输入 token。派活要合并，别拆碎。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# 项目根的判定依据，按优先级。找不到就用当前目录。
ROOT_MARKERS = (".git", "AGENTS.md", "CLAUDE.md", "reasonix.toml")

# 无头实现要写代码、跑自查，得能落盘。auto 是官方的 -y，自动批准普通写操作。
# 别用 bypassPermissions——那个连 deny 规则都不看。
DEFAULT_PERMISSION_MODE = "auto"


def find_cli() -> Path:
    """定位 reasonix CLI。顺序：环境变量 > PATH > 常见安装位置。"""
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

    raise SystemExit(
        "没找到 reasonix CLI。设 REASONIX_CLI 指向可执行文件，或把它加进 PATH。"
    )


def find_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        if any((candidate / marker).exists() for marker in ROOT_MARKERS):
            return candidate
    return here


def build_argv(args: argparse.Namespace, cli: Path, root: Path, task: str) -> list[str]:
    argv = [str(cli)]
    if args.mode == "sub":
        argv += ["subagent", "run", args.name]
    else:
        argv += ["run"]
    argv += ["--dir", str(root)]
    if args.model:
        argv += ["--model", args.model]
    if args.mode != "sub":
        # subagent run 不吃 --output-format / --permission-mode，档案自己带权限。
        argv += ["--output-format", "json", "--permission-mode", args.permission_mode]
    if args.max_steps:
        argv += ["--max-steps", str(args.max_steps)]
    argv += [task]
    return argv


def report(payload: dict) -> int:
    """把 JSON 信封拆开：正文给人看，账单单独一行，错误走 stderr。"""
    text = (payload.get("result") or "").strip()
    usage = payload.get("usage") or {}

    if payload.get("is_error"):
        print(f"Reasonix 执行失败：{text}", file=sys.stderr)
        return 1

    if text:
        print(text)

    bill = [
        f"in={usage.get('input_tokens', 0)}",
        f"out={usage.get('output_tokens', 0)}",
        f"cache_read={usage.get('cache_read_input_tokens', 0)}",
    ]
    if payload.get("total_cost_usd") is not None:
        bill.append(f"cost=${payload['total_cost_usd']}")
    if payload.get("session_id"):
        bill.append(f"session={payload['session_id']}")
    print(f"\n[rx] {' '.join(bill)}", file=sys.stderr)
    return 0


def run_doctor(cli: Path, root: Path) -> int:
    """环境自检：CLI 在哪、项目根在哪、Reasonix 那边配置对不对。不花钱。"""
    print(f"cli      : {cli}")
    print(f"root     : {root}")
    # doctor 不吃 --dir（只有 session / hook / task 子命令吃），只能靠 cwd 决定项目根。
    proc = subprocess.run(
        [str(cli), "doctor", "--json"],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    try:
        d = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(proc.stdout or proc.stderr)
        return 1
    print(f"config   : {d.get('config', {}).get('source_path')}")
    print(f"model    : {d.get('config', {}).get('default_model')}")
    print(f"perm     : {d.get('permission')}")
    print(f"write    : {d.get('sandbox', {}).get('write_roots')}")
    keys = [p["name"] for p in d.get("providers", []) if p.get("key_present")]
    print(f"providers: {keys or '（没有可用密钥）'}")
    for w in d.get("warnings") or []:
        print(f"warn     : {w}")
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(add_help=True)
    sub = parser.add_subparsers(dest="mode", required=True)

    p_sub = sub.add_parser("sub", help="派一个已注册的子代理档案")
    p_sub.add_argument("name")
    p_sub.add_argument("task")

    p_run = sub.add_parser("run", help="不走子代理，直接跑一个任务")
    p_run.add_argument("task")

    p_doc = sub.add_parser("doctor", help="环境自检，不花钱")

    for p in (p_sub, p_run):
        p.add_argument("--model", default=None)
        p.add_argument("--max-steps", type=int, default=0)
        p.add_argument("--permission-mode", default=DEFAULT_PERMISSION_MODE)
        p.add_argument("--timeout", type=int, default=1800)
    for p in (p_sub, p_run, p_doc):
        p.add_argument("--dir", default=None)

    args = parser.parse_args()
    cli = find_cli()
    root = find_root(args.dir)

    if args.mode == "doctor":
        return run_doctor(cli, root)

    if args.permission_mode == "plan":
        raise SystemExit("plan 模式要求交互式会话，无头调用用不了")

    task = sys.stdin.read().strip() if args.task == "-" else args.task.strip()
    if not task:
        raise SystemExit("任务是空的")

    try:
        proc = subprocess.run(
            build_argv(args, cli, root, task),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=args.timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"Reasonix 超时（{args.timeout}s）未返回，已放弃。", file=sys.stderr)
        return 1

    stdout = (proc.stdout or "").strip()

    # subagent run 是纯文本输出，run --output-format json 才是信封。
    if args.mode == "sub":
        if stdout:
            print(stdout)
        if proc.returncode != 0:
            print((proc.stderr or "").strip(), file=sys.stderr)
        return proc.returncode

    try:
        return report(json.loads(stdout))
    except json.JSONDecodeError:
        print(stdout or "(Reasonix 没有任何输出)")
        print((proc.stderr or "").strip(), file=sys.stderr)
        return proc.returncode or 1


if __name__ == "__main__":
    sys.exit(main())
