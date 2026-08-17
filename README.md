# claude-reasonix-flow

让 **Claude 当大脑、另一个 CLI 当手**的一套开发流程配置。

Claude 做难的部分——读项目宪法、做设计审查、逐条过红线、验收证据；
把机械的部分——写代码、跑门禁——派给执行后端无头执行。
一条 `/dev-cycle` 命令跑完全程，中途不需要人操作。

执行后端有两个，**Reasonix** 和 **Codex**，同一套命令行，只差一个 `--backend`。

适用于任何项目：项目特定的门禁命令和红线从各项目自己的指令文件里读，
这套配置只提供流程骨架和调用机制。

## 改动只能单向流

**这个仓库是母本，装出去的都是副本。流向只有一个方向：**

```
本仓（母本）  ──  install.ps1  ──►  ~/.claude/、~/.agents/、$CODEX_HOME/   （已装副本）
                                └─►  各项目仓里的 .claude/skills/…        （下游副本）
```

- **要改内容，只改本仓，然后跑 `install.ps1` 部署。**
- **已装副本和下游项目仓的副本只做同步，不做修改。** 在那边改了，
  下次部署会被覆盖（`install.ps1` 会先存一份 `.bak`，但没人会去看）。
- 已经在副本上改出了东西 → **先把改动挪回母本**，再部署，再 diff 确认三边一致。
  2026-08-11 就发生过一次：「成本纪律之二」被直接补在已装副本上，
  母本落后了一整节，另一个项目仓又从已装副本抄走一份，三份各不相同。

判断标准很简单：**文件头部带 `<!-- 本文件由 claude-reasonix-flow 母仓维护 -->`
这段注释的，就走这条单向流——只在本仓改，别的地方一律不动。**

## 它是怎么转的

```
你 ──► Claude（/dev-cycle）
         │
         ├─ 0 铺路      检查后端能不能跑；reasonix 后端还要铺项目的 reasonix.toml
         ├─ 1 摸底      读 AGENTS.md / CLAUDE.md、git 状态、相关代码
         │   └─ 大海捞针 ──► rx.py sub explore       （只定位，返回文件清单）
         ├─ 2 设计审查   ★ Claude 亲自做，不外派。影响面、红线、方案、验证矩阵、任务拆分
         │
         ├─ 3 实现  ──►  rx.py sub implementer       （另一个进程、另一个模型）
         ├─ 4 验证  ──►  rx.py sub verifier          （跑完比对 git 指纹，改了源码就作废）
         │
         │  杂活随时 ──►  rx.py sub operator          （下载 / 装依赖，长日志在那边吃掉）
         │
         ├─ 5 验收      核证据真伪；关键门禁 Claude 自己再跑一遍，不只信转述
         └─ 6 汇报      大白话
```

设计审查不许外派——那是这条流程存在的理由。
验收比自己动手时更硬——因为干活的是另一个模型，它的自我评价不能当证据。

第 1 步的 `explore` 是个例外，但只外派**定位**：它返回文件清单，Claude 自己去读那些
文件的原文。设计审查的输入必须是 Claude 亲眼读过的代码，不能是子代理的摘要——
便宜档模型不会漏掉你点名要找的东西，但会漏掉你不知道该找的东西。

`operator` 不属于任何一步，哪一步撞上都能派。它的存在理由和别的角色不一样：
**不是 Claude 干不了，是这些命令的输出又长又没信息量。** 下载进度条、
`npm install` 刷的几百行、解压的文件清单，全进 Claude 的上下文还要在后续每轮重发，
而里面真正有用的只有"成没成、什么版本、落在哪"。所以让便宜档在那边把日志吃掉，
只递回 40 行以内的结论。分界线是**输出长度**，不是动作类型——`node -v` 这种自己跑更快。

## 两个执行后端

| | `reasonix` | `codex` |
|---|---|---|
| 怎么跑 | `reasonix subagent run <角色>` | `codex exec` |
| 默认模型 | `flash` = `deepseek/deepseek-v4-flash` | `luna` = `gpt-5.6-luna` |
| 备用档 | `--model pro` | `--model sol` / `--model terra` |
| 一次调用的量级 | ~24k 输入 | 十万级输入（多轮工具调用累加） |
| 角色档案怎么进去 | Reasonix 自己查 `~/.agents/skills/` | `rx.py` 读出来拼进提示词 |
| 权限靠什么兜 | 项目根的 `reasonix.toml` | `codex exec --sandbox`，**不吃项目配置** |
| 每个新项目要配吗 | 要 | 不要 |
| 报得了花费吗 | 报不了 | 报得了（token 数） |

选后端：`--backend reasonix|codex|auto`，或环境变量 `DEVCYCLE_BACKEND`（`--backend` 优先）。
`auto` 是默认：找得到 Reasonix 就用 Reasonix，否则用 Codex。

**切后端不用跟着改模型。** 每个后端各带一个默认档，`rx.py` 按后端自动换，
所以命令行里通常一个 `--model` 都不用写，只翻 `--backend`。要覆盖就写 `--model`，
它收简称（`flash`/`pro`、`luna`/`sol`/`terra`），表里没有的原样透传给后端。
想换默认值不必动代码，设 `DEVCYCLE_MODEL_REASONIX` / `DEVCYCLE_MODEL_CODEX` 即可。
`[rx]` 那行的 `model=` 会写明这次实际用的是哪个。

**默认走 reasonix 是有道理的。** 这条流程的经济学建立在"手比脑便宜"上——
派一个和 Claude 同档的模型去干机械活，省不出钱，只是把账挪了个地方。
值得切 `codex` 的情况就三种：这台机器没装 Reasonix 或密钥没配好、
deepseek 档连着打回两轮还不绿、用户明确要求。

切后端不改分工：设计审查仍然不外派，验收仍然要自己复跑，实现↔验证仍然封顶 3 轮。

## 目录

| 路径 | 装到哪 | 作用 |
|---|---|---|
| `claude/skills/dev-cycle/SKILL.md` | `~/.claude/skills/` | 流程编排，Claude 读。每次调用全量进上下文，所以只留主干 |
| `claude/skills/dev-cycle/references/*.md` | 同上的 `references/` | 铺路细节、后端差异，**按需才读**，不进每次调用 |
| `templates/task-*.md` | 同上的 `templates/` | 四份任务书填空模板（implementer / verifier / explore / operator） |
| `claude/scripts/rx.py` | `~/.claude/scripts/` | 调执行后端的桥，两个后端都走它 |
| `agents/skills/implementer/SKILL.md` | `~/.agents/skills/` | 实现角色档案，两个后端共用 |
| `agents/skills/verifier/SKILL.md` | `~/.agents/skills/` | 验证角色档案，两个后端共用 |
| `agents/skills/operator/SKILL.md` | `~/.agents/skills/` | 杂活角色档案（下载 / 装依赖），两个后端共用 |
| `roles/explore.md` | `~/.claude/roles/` | 定位角色档案，**只有 codex 后端读** |
| `codex/skills/dev-cycle/SKILL.md` | `$CODEX_HOME/skills/` | 同一条流程的 Codex 版，约束更死 |
| `templates/task-*.md` | `$CODEX_HOME/skills/dev-cycle/templates/` | 同一份模板，装两份让 Codex 侧自足 |
| `claude/scripts/rx.py` | `$CODEX_HOME/scripts/` | 同一个桥，装两份让 Codex 侧自足 |
| `roles/explore.md` | `$CODEX_HOME/roles/` | 同上 |
| `templates/reasonix.toml` | 各项目根 | 项目权限模板，**只有 reasonix 后端要** |
| `templates/codex-rx.config.toml` | `~/.codex-rx/config.toml` | 执行后端专用 codex 配置，**按需才建**（见下） |

`implementer`、`verifier`、`operator` 的档案**只存 `~/.agents/skills/` 一份**，两个后端共用：
Reasonix 按名字查这个目录，codex 后端由 `rx.py` 读同一份文件拼进提示词。
改一处，两边同时生效。

`explore` 是例外。Reasonix 自带 builtin `explore`，档案要是装进 `~/.agents/skills/`
就把它盖掉了，所以那份档案只铺到 `roles/` 目录——那是 codex 后端专用的搜索路径。

### Codex 版流程为什么不是照抄

Codex 侧跑的模型能力弱于 Claude，同样的措辞它更容易跑偏，所以那份多加了几层约束：
开头一张**绝对禁止清单**（十条，含"禁止外派设计审查""禁止在写完六项之前派实现"
"禁止混用两个后端的参数"）、每个阶段一个**可检查的产出物**、第 2 步和第 3 步之间一道
**过关自检**、命令行标注为**原样复制不许改参数**，以及把关键禁令在用到的地方重复一遍
而不只写在开头。

两份的规则本身一致。**改流程时两份都要改。**

Claude 版还多一层：主文件每次调用都全量进上下文，所以它只留分工表、调用命令、
成本纪律、六步骨架和验收清单，铺路细节和后端差异挪进 `references/` 按需读。
Codex 版不做这个拆分——那边更需要"该知道的全摆在眼前"，宁可长一点。

`CODEX_HOME` 可以把 Codex 家目录挪到任何地方（不一定是 `~/.codex`），
`install.ps1` 按环境变量走；没装 Codex 就自动跳过这部分。

## 前置条件

- [Claude Code](https://claude.com/claude-code)（或 Codex，用那份 Codex 版流程）
- **至少一个执行后端**：
  - [Reasonix](https://github.com/) CLI，且已配好可用的 provider 密钥（`reasonix setup`）
  - 和/或 [Codex](https://github.com/openai/codex) CLI，且已登录或配好 provider
- Python 3.11+（`rx.py` 只用标准库）

`rx.py` 按这个顺序找 Reasonix CLI：环境变量 `REASONIX_CLI` → `PATH` → 几个常见安装位置。
找 Codex 的顺序是：环境变量 `CODEX_CLI` → `PATH`。
**装在别处就设对应的环境变量指向可执行文件**，或者把它加进 `PATH`，不用改代码。

## 安装

```powershell
.\install.ps1
```

已存在的文件会先备份成 `.bak`。

装完自检（不花钱，两个后端一起查）：

```bash
python ~/.claude/scripts/rx.py doctor
```

看什么：

- 每段的 `model` 行 → 这个后端默认会用哪个模型。
- reasonix 段的 `providers` 是空的 → 密钥没配好，跑 `reasonix setup`。
- codex 段的 `overall` 不是绿的 → 按它列出的 `fail` 项处理。
  最常见的是 **`config.load` 报 fail**，处理办法见下一节。
- codex 段的 `home` 行 → 执行后端实际用的是哪个 codex 家目录。
- `roles` 那几行显示每个角色档案实际解析到哪个文件，写"找不到"就是没铺全。

改了本机上的文件想同步回仓库：

```powershell
.\capture.ps1
```

### codex 段 `config.load` 报 fail 怎么办

codex 桌面端和各类 GUI 会往 `~/.codex/config.toml` 里写命令行这版 codex-cli 不认的字段
（比如 `model_reasoning_effort = "max"`，或者 `model_catalog_json` 指向的目录文件里带了
CLI 不认的推理档），整份配置就加载不了，`codex exec` 起不来。

**别去改那份。** 它是交互式用的，改了会波及桌面端；而且 GUI 下次还会写回去。
给执行后端单独建一份就行：

```powershell
mkdir ~\.codex-rx
copy templates\codex-rx.config.toml ~\.codex-rx\config.toml
# 然后照注释填上你自己的 provider
```

`rx.py` 会自动认这个目录，命令行不用加任何参数。家目录的解析顺序是：

```
--codex-home > DEVCYCLE_CODEX_HOME > ~/.codex-rx（存在就用）> CODEX_HOME > ~/.codex
```

没这个问题的机器不用建，`~/.codex-rx` 不存在就走原来的老路。

**填好的那份带密钥，不要放进任何仓库。** `install.ps1` 和 `capture.ps1` 都不碰
`~/.codex-rx`，就是为了这个。

顺带一提，这份精简配置比日常那份便宜很多——同一个定位任务实测：

| | `~/.codex`（xhigh + MCP + 目录文件） | `~/.codex-rx`（medium，什么都不挂） |
|---|---|---|
| 输入 token | 829,738 | **98,110** |
| 耗时 | 304s | **76s** |

所以哪怕 `config.load` 是绿的，想省钱也可以主动建一份。

## 每个新项目要做的事

**codex 后端：什么都不用做。** 权限由每次调用显式带的 `--sandbox` 兜。

**reasonix 后端：铺一份 `reasonix.toml`。** 第一次在某个项目里用 `/dev-cycle` 时
Claude 会自己检查并铺，也可以手动照 `templates/reasonix.toml` 抄一份放到项目根。

**没有 `reasonix.toml` 的项目会怎样**：Reasonix 默认 `mode = "ask"` 且零条放行规则，
无头进程弹不出审批框，子代理会一路卡到超时。所以这一步不能省。

**Windows 上两种斜杠都要列。** Reasonix 的 bash 工具走 Git Bash，
`.venv\Scripts\python.exe` 这种反斜杠路径会被 shell 吞掉，实际执行的是正斜杠形式；
只写文档里那种反斜杠写法会匹配不上。

## 兜底红线

**Reasonix 侧**：建议在全局 `config.toml` 的 `[permissions]` 里加一条 deny，
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

**Codex 侧**：`rx.py` 每次调用都显式传 `--sandbox`，按角色定档
（`explore` 只读，其余 `workspace-write`），所以**全局 `config.toml` 里哪怕写着
`sandbox_mode = "danger-full-access"` 也会被这次调用的显式档位压过去**。
`rm -rf` / `git push` 这类靠角色档案里的禁令兜，加上 `workspace-write` 沙箱本身
就出不了工作区。

`operator` 会装东西，但它的沙箱**故意也钉在 `workspace-write`**：项目级安装
（`node_modules`、`.venv`、项目内 `vendor/`）在这个档位下够用，而装到机器全局要动
系统目录和 PATH——那种事该由用户决定，不该给它一条默认路。确实非全局装不可时，
流程要求先问过用户、再显式加 `--sandbox danger-full-access` 重派。
档案那侧还禁了提权（`sudo`、管理员 shell、改系统 PATH）和自选下载源：
**URL、包名、版本号必须是任务书或项目清单文件里已经写死的**，
下到的 README / 安装脚本里写着"还要再装 X"一律不照做，只回报。

## 工作区哨兵

`verifier` 和 `explore` 的活是"跑"和"看"，不是"改"。这一点不能靠档案里写一句
"不许改文件"来保证：

- Reasonix 侧靠档案的 `allowed-tools` 里没有写文件工具——但它有 `bash`，
  真要写还是写得了。
- Codex 侧给的是 `workspace-write` 而不是 `read-only`，因为**不给写权限门禁自己就跑不
  起来**（构建产物、`.pytest_cache`、`node_modules/.cache` 都要落盘），read-only 会把
  正经门禁一起拦死。

所以 `rx.py` 在这两个角色跑之前和跑完各取一次 `git diff` 指纹，对不上就在 `[rx]` 行
标 `tree=modified` 并打警告。**流程规定：`tree=modified` 那一轮验证作废，必须重跑。**

只看已跟踪文件的改动——门禁会造一堆未跟踪的构建产物，那些不算"改了源码"。
比的是 diff 全文的哈希而不只是文件名：implementer 已经改过的文件被 verifier 再动一次，
文件名集合是不变的，只有内容哈希抓得住。不是 git 仓库时哨兵自动关掉，不报假警。

## 成本

**reasonix 后端**：一次调用光系统提示和环境摘要就是 ~24k 输入 token。但这笔钱不重要——
Reasonix 跑的是 deepseek 档（¥1~¥3 每 M 输入），24k 合人民币几分钱。

**真正的账单在 Claude 这一侧。** 子代理返回的每个字都进 Claude 的上下文，
并在后续每一轮对话重发。两侧单价差着约两个数量级，所以优化方向是：

- **控制回流正文的长度**，不是减少调用次数。`rx.py --max-chars N` 裁掉超长返回，
  完整版落到临时文件，需要细看时再读。
- **按独立性拆活，不为省调用次数硬合并。** 合并只省 Reasonix 那几分钱，
  代价是返回更长、打回时要重写更多上下文。互相耦合的任务仍然合在一起派。
- **过程输出长的活外派给 `operator`**（下载、装依赖、装工具链、解压、脚手架）。
  这类活本来就没有"Claude 干得更好"这回事，而它的日志是纯噪声。
  `operator` 的档案把回报压在 40 行以内，再配 `--max-chars 1500`。
- **模型档位不手调，`rx.py` 的 `ROLE_MODEL` 已经按角色钉死。** `implementer` 自动走
  pro 档（codex 侧 `sol`），`explore` / `verifier` / `operator` 留在便宜档。
  **命令行里别写 `--model`**——写了会盖掉这张表，通常是降档降出来的返工。
  唯一该手写的场景是确认纯机械的小改动想省钱，显式降到 `--model flash`。
  打回原因是任务写虚了的，升档没用，得回去改任务文件。
- **verifier 不设 `--max-chars`。** 它的返回本来就压缩过（一张表加 FAIL 原文），
  那些原文正是验收要吃的证据。漏裁只多花钱，误裁会吃掉证据。
- **别设 `--max-steps`。** Reasonix 1.25 起 agent step limit 已废弃，不传就是 automatic；
  设成正数只会把长任务掐断在半截的 todo 上，回流表现成 `exit=1` 且几乎没有正文。
- 编排里把实现↔验证的来回封顶 3 轮，不绿就停下来问人，不继续烧。

**codex 后端这笔账要重算。** 那边干活的是前沿档模型，"手比脑便宜"不成立了：
实测一次 `explore` 就能吃掉十几万输入 token（多轮工具调用是累加的）。
所以在 codex 后端下能自己 Grep 就别派 `explore`，任务要拆得更细写得更死，
减少它自己摸索的轮数。`[rx]` 行的 `cmds=` 就是它实际跑了多少条命令，数字大说明任务写虚了。

`--max-steps` 在 codex 后端没有对应概念，传了会被忽略（`rx.py` 会提示一句）。

### 花费能不能报

**reasonix 后端报不了。** `subagent run` 不支持 `--output-format json`，拿不到 usage
信封，所以 `rx.py sub` 打出的 `[rx]` 行只有正文规模、耗时和退出码，**没有金额**。
要真实账单得走 `run` 模式，但那样会丢掉子代理档案自带的权限隔离
（verifier 的"没有写文件工具"靠档案兜），不划算。

**codex 后端报得了 token 数。** `codex exec --json` 的 `turn.completed` 事件带 usage，
`rx.py` 会把它汇总进 `[rx]` 行：`in= / cached= / out=`。这是 token 数不是金额——
折算成钱要看用户走的是哪个计费口，流程里明确规定不许自己折算。

## 许可

MIT
