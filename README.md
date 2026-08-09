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
         │   └─ 大海捞针 ──► reasonix subagent run explore  （只定位，返回文件清单）
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

第 1 步的 `explore` 是个例外，但只外派**定位**：它返回文件清单，Claude 自己去读那些
文件的原文。设计审查的输入必须是 Claude 亲眼读过的代码，不能是子代理的摘要——
便宜档模型不会漏掉你点名要找的东西，但会漏掉你不知道该找的东西。

## 目录

| 路径 | 装到哪 | 作用 |
|---|---|---|
| `claude/skills/dev-cycle/SKILL.md` | `~/.claude/skills/` | 流程编排，Claude 读 |
| `claude/scripts/rx.py` | `~/.claude/scripts/` | 调 Reasonix 的桥 |
| `agents/skills/implementer/SKILL.md` | `~/.agents/skills/` | 实现子代理档案，Reasonix 读 |
| `agents/skills/verifier/SKILL.md` | `~/.agents/skills/` | 验证子代理档案，Reasonix 读 |
| `codex/skills/dev-cycle/SKILL.md` | `$CODEX_HOME/skills/` | 同一条流程的 Codex 版，约束更死 |
| `claude/scripts/rx.py` | `$CODEX_HOME/scripts/` | 同一个桥，装两份让 Codex 侧自足 |
| `templates/reasonix.toml` | 各项目根 | 项目权限模板，按项目门禁改 |

### Codex 版为什么不是照抄

Codex 侧跑的模型能力弱于 Claude，同样的措辞它更容易跑偏，所以那份多加了几层约束：
开头一张**绝对禁止清单**（八条，含"禁止外派设计审查""禁止在写完六项之前派实现"）、
每个阶段一个**可检查的产出物**、第 2 步和第 3 步之间一道**过关自检**、
命令行标注为**原样复制不许改参数**，以及把关键禁令在用到的地方重复一遍而不只写在开头。

两份的规则本身一致。**改流程时两份都要改。**

`CODEX_HOME` 可以把 Codex 家目录挪到任何地方（不一定是 `~/.codex`），
`install.ps1` 按环境变量走；没装 Codex 就自动跳过这部分。

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

一次 Reasonix 调用，光系统提示和环境摘要就是 **~24k 输入 token**。但这笔钱不重要——
Reasonix 跑的是 deepseek 档（¥1~¥3 每 M 输入），24k 合人民币几分钱。

**真正的账单在 Claude 这一侧。** 子代理返回的每个字都进 Claude 的上下文，
并在后续每一轮对话重发。两侧单价差着约两个数量级，所以优化方向是：

- **控制回流正文的长度**，不是减少调用次数。`rx.py --max-chars N` 裁掉超长返回，
  完整版落到临时文件，需要细看时再读。
- **按独立性拆活，不为省调用次数硬合并。** 合并只省 Reasonix 那几分钱，
  代价是返回更长、打回时要重写更多上下文。互相耦合的任务仍然合在一起派。
- **implementer 用 `--model deepseek/deepseek-v4-pro`。** 比默认 flash 档每次贵约 ¥0.05，
  但少一次"写崩→打回→重审"就赚回来了——那一轮走的是 Claude 的价。
- **verifier 不设 `--max-chars`。** 它的返回本来就压缩过（一张表加 FAIL 原文），
  那些原文正是验收要吃的证据。漏裁只多花钱，误裁会吃掉证据。
- 用 `--max-steps` 卡轮数防跑飞。
- 编排里把实现↔验证的来回封顶 3 轮，不绿就停下来问人，不继续烧。

### 报不了花费

`subagent run` 不支持 `--output-format json`，拿不到 usage 信封，所以 `rx.py sub`
打出的 `[rx]` 行只有正文规模、耗时和退出码，**没有金额**。要真实账单得走 `run` 模式，
但那样会丢掉子代理档案自带的权限隔离（verifier 的"没有写文件工具"靠档案兜），不划算。

## 许可

MIT
