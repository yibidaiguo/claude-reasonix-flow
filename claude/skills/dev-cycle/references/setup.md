# 铺路细节（第 0 步展开）

主文件说「跑 `doctor`，没铺过就铺」。这份是铺的具体做法。
**每个项目只做一次**，铺过的项目直接跳到第 1 步。

## 先看 doctor 怎么说

```bash
python ~/.claude/scripts/rx.py doctor
```

两个后端一起查。按你要用的那个后端看对应段落。

## codex 后端：基本没事干

权限由每次调用显式带的 `--sandbox` 兜，**不需要项目级配置文件**。
只要 `codex` 段的 `overall` 是绿的就行。

### `config.load` 报 fail 时

**不许自己去改用户的 `~/.codex/config.toml`。** 那份是交互式用的，改了会波及桌面端。

正确做法是建一份执行后端专用的：`~/.codex-rx/config.toml`
（模板在仓库 `templates/codex-rx.config.toml`），`rx.py` 会自动认这个目录。
里面要填 provider 和密钥——**让用户自己填，你不碰密钥。**

## reasonix 后端：看两件事

| doctor 里看到 | 意思 | 怎么办 |
|---|---|---|
| `providers` 是空的 | 密钥没配 | 让用户自己跑 `reasonix setup`。**你不碰密钥。** |
| `config` 不是 `reasonix.toml`，或 `perm` 的 `allow_rules` 是 0 | 这个项目还没铺过 | 按下面铺 |

### 铺 reasonix.toml

先从项目里认出门禁命令，按这个优先级：
指令文件（`AGENTS.md` / `CLAUDE.md` / `CONTRIBUTING.md`）> `package.json` 的 scripts >
`Makefile` > `pyproject.toml` > CI 配置（`.github/workflows/`）。

在项目根写：

```toml
[permissions]
mode = "ask"          # 兜底仍然要问，放行的只有下面列出的
allow = [
    # 这个项目的门禁命令，一条一条列
    # 只读 git：status / diff / log / show / branch / rev-parse / ls-files
    # 提交：git add / git commit（到此为止）
]
deny = [
    'Bash(rm -rf*)',
    'Bash(git clean*)',
    'Bash(git push*)',
]
```

### Windows 上两种斜杠都要列

Reasonix 的 bash 工具走 Git Bash，`.venv\Scripts\python.exe` 这种反斜杠路径会被 shell
吞掉，**实际执行的是正斜杠形式**。只写文档里那种反斜杠写法会匹配不上，
子代理会卡在等审批直到超时。

同一条命令的正反斜杠两种写法都要进 `allow`。

### 写完给用户看一眼

这是在给另一个 AI 开权限，值得他扫一眼再往下走。

## 第 1 步的 explore 不受这一步阻塞

它是只读子代理，在没铺过 `reasonix.toml` 的项目里也能跑通（实测过）。
要铺路的是会写文件、会跑门禁的 `implementer` 和 `verifier`。
