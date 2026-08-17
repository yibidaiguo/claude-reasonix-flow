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

在项目根写（完整可抄的版本在 `templates/reasonix.toml`，**优先直接复制那份**）：

```toml
[permissions]
mode = "ask"          # 兜底仍然要问，放行的只有下面列出的
allow = [
    # 这个项目的门禁命令，一条一条列
    # 只读 git：status / diff / log / show / branch / rev-parse / ls-files
    # 提交：git add / git commit（到此为止）
    'Edit(**)',       # 文件写入，见下一节，漏了这条整条流程就是死的
]
deny = [
    'Bash(rm -rf*)',
    'Bash(git clean*)',
    'Bash(git push*)',
    'read_file(**/.env)', 'Edit(**/.env)',   # 凭据不许读，也不许写
    'Edit(.git/**)', 'Edit(**/.git/**)',     # hooks / config 是 push 红线的后门
]
```

### 最容易漏的一条：文件写入

**`allow` 里没有 `Edit(**)`，`implementer` 就一个字也写不出来。** 这是最贵的一种失败——
它不报权限错，而是表现成「跑了三分钟、`chars=0`、`exit=1`」，回流里才看得到
`write_file — declined`。

为什么 `rx.py` 的 `--permission-mode auto` 救不了：**`subagent run` 根本不吃这个参数**
（子代理档案自带权限），所以兜底直接落回 `mode = "ask"`，无头进程没人可问 → blocked。

**族名别凭感觉写**，写错了不会报错，只会静默不匹配：

| 要放行/禁止的事 | 规则写法 | 别写成 |
|---|---|---|
| 改文件（含新建、改、移动、删符号） | `Edit(<glob>)` | ~~`write_file(...)`~~ ~~`Write(...)`~~ |
| 读文件 | `read_file(<glob>)` | ~~`Read(...)`~~ |
| 跑命令 | `Bash(<前缀>:*)` | ~~`bash(...)`~~ |

Reasonix 把七个写工具（`write_file` / `edit_file` / `multi_edit` / `move_file` /
`notebook_edit` / `delete_range` / `delete_symbol`）**统一收进 `Edit` 这一族**，
审批也是按 `Edit(<path>)` 存的；而读那一族**没有**大写别名。

**开 `Edit(**)` 不算把口子开大**：Reasonix 的 sandbox 已经把写盘限死在 `write_roots`
（= 项目根，`doctor` 里看得见），这条放行出不了仓库。但**必须同时在 `deny` 里补写侧红线**
（`Edit(**/.env)`、`Edit(.git/**)`），否则 `Edit(**)` 会把「凭据不进 Git」和
「不许 push」这两条一起架空——`deny > ask > allow`，deny 压得住。

### 要派 operator 就得放行安装命令

`operator` 干的是下载和装依赖，那些命令不在门禁清单里，**默认没人给它放行**。
派出去会卡在等审批直到超时——表现和写入被拦一样：跑很久、`chars=0`。

按这个项目实际用的包管理器补几条，只补它真会用到的：

```toml
allow = [
    'Bash(npm install:*)', 'Bash(npm ci:*)', 'Bash(pnpm install:*)',
    'Bash(uv:*)', 'Bash(pip install:*)', 'Bash(curl:*)',
]
```

**别图省事写 `Bash(*)`**。那等于把 deny 之外的一切都开了，
`operator` 的"不提权、不换源"就只剩档案里那句话在兜。

装到机器全局的东西不归这条管——`operator` 被禁止提权，那种事先问用户。

### Windows 上两种斜杠都要列

Reasonix 的 bash 工具走 Git Bash，`.venv\Scripts\python.exe` 这种反斜杠路径会被 shell
吞掉，**实际执行的是正斜杠形式**。只写文档里那种反斜杠写法会匹配不上，
子代理会卡在等审批直到超时。

同一条命令的正反斜杠两种写法都要进 `allow`。

### 写完自己验一次，别假设铺对了

`doctor` 只数规则条数，**不会告诉你族名写错了**。花一毛钱验一次真的无头写入：

```bash
python ~/.claude/scripts/rx.py sub implementer - <<'EOF'
在仓库根建一个文件 rx-perm-probe.txt，内容就一行 OK，然后停手。不要跑门禁，不要提交。
EOF
```

文件真出现了才算铺通，**验完把探针文件删掉**。回流里出现 `declined` 或者
`chars=0`，就是 `allow` 里的族名写错了，回上一节对表。

### 写完给用户看一眼

这是在给另一个 AI 开权限，值得他扫一眼再往下走。

## 第 1 步的 explore 不受这一步阻塞

它是只读子代理，在没铺过 `reasonix.toml` 的项目里也能跑通（实测过）。
要铺路的是会写文件、会跑门禁的 `implementer` 和 `verifier`。
