# claude-reasonix-flow

让 **Claude 当大脑、Reasonix 当手**的一套开发流程配置。

Claude 做难的部分——读项目宪法、做设计审查、逐条过红线、验收证据；
把机械的部分——写代码、跑门禁——派给 Reasonix 无头执行。
一条 `/dev-cycle` 命令跑完全程，中途不需要人操作。

适用于任何项目：项目特定的门禁命令和红线从各项目自己的指令文件里读，
这套配置只提供流程骨架和调用机制。

## 它是怎么转的

```
你 ──► Claude（/dev-cycle）
         │
         ├─ 0 铺路      检查项目有没有 reasonix.toml，没有就按项目门禁生成一份
         ├─ 1 摸底      读 AGENTS.md / CLAUDE.md、git 状态、相关代码
         ├─ 2 设计审查   ★ Claude 亲自做，不外派。影响面、红线、方案、验证矩阵、任务拆分
         │
         ├─ 3 实现  ──►  reasonix subagent run implementer   （另一个进程、另一个模型）
         ├─ 4 验证  ──►  reasonix subagent run verifier      （无写文件工具，改不了源码）
         │
         ├─ 5 验收      核证据真伪；关键门禁 Claude 自己再跑一遍，不只信转述
         └─ 6 汇报      大白话，含本轮花费
```

设计审查不许外派——那是这条流程存在的理由。
验收比自己动手时更硬——因为干活的是另一个模型，它的自我评价不能当证据。

## 目录

| 路径 | 装到哪 | 作用 |
|---|---|---|
| `claude/skills/dev-cycle/SKILL.md` | `~/.claude/skills/` | 流程编排，Claude 读 |
| `claude/scripts/rx.py` | `~/.claude/scripts/` | 调 Reasonix 的桥 |
| `agents/skills/implementer/SKILL.md` | `~/.agents/skills/` | 实现子代理档案，Reasonix 读 |
| `agents/skills/verifier/SKILL.md` | `~/.agents/skills/` | 验证子代理档案，Reasonix 读 |
| `templates/reasonix.toml` | 各项目根 | 项目权限模板，按项目门禁改 |

## 前置条件

- [Claude Code](https://claude.com/claude-code)
- [Reasonix](https://github.com/) CLI，且已配好可用的 provider 密钥（`reasonix setup`）
- Python 3.11+（`rx.py` 只用标准库）

`rx.py` 按这个顺序找 Reasonix CLI：环境变量 `REASONIX_CLI` → `PATH` →
几个常见安装位置。**装在别处就设 `REASONIX_CLI` 指向可执行文件**，
或者把它加进 `PATH`，不用改代码。

## 安装

```powershell
.\install.ps1
```

把四个文件铺到 `~/.claude/` 和 `~/.agents/`。已存在的会先备份成 `.bak`。

装完自检（不花钱）：

```bash
python ~/.claude/scripts/rx.py doctor
```

`providers` 是空的说明密钥没配好，跑 `reasonix setup`。

改了本机上的文件想同步回仓库：

```powershell
.\capture.ps1
```

## 每个新项目要做的事

第一次在某个项目里用 `/dev-cycle` 时，Claude 会自己检查并铺 `reasonix.toml`。
也可以手动照 `templates/reasonix.toml` 抄一份放到项目根。

**没有 `reasonix.toml` 的项目会怎样**：Reasonix 默认 `mode = "ask"` 且零条放行规则，
无头进程弹不出审批框，子代理会一路卡到超时。所以这一步不能省。

**Windows 上两种斜杠都要列。** Reasonix 的 bash 工具走 Git Bash，
`.venv\Scripts\python.exe` 这种反斜杠路径会被 shell 吞掉，实际执行的是正斜杠形式；
只写文档里那种反斜杠写法会匹配不上。

## 全局兜底红线

建议在 Reasonix 全局 `config.toml` 的 `[permissions]` 里加一条 deny，
让危险操作在任何项目都拦得住：

```toml
deny = [
    'Bash(rm -rf*)',      # 不可恢复删除
    'Bash(git clean*)',   # 同上，会连未跟踪文件一起清掉
    'Bash(git push*)',    # 推送始终由人来做
]
```

放行规则（allow）刻意**不**放全局——每个项目的门禁命令不一样，那归各项目的
`reasonix.toml` 管。全局只管"哪些事在任何项目都不许干"。

## 成本

一次 Reasonix 调用，光系统提示和环境摘要就是 **~24k 输入 token**，
什么都不干也要付。所以：

- **派活要合并。** 三个小改动写成一个任务文件派一次，比拆三次便宜得多。
- 用 `--max-steps` 卡轮数防跑飞。
- 编排里把实现↔验证的来回封顶 3 轮，不绿就停下来问人，不继续烧。

## 许可

MIT
