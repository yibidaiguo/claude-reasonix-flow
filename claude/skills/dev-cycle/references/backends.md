# 两个执行后端的差异

主文件说「默认走 reasonix，不加 `--backend`」。这份是要切的时候看的。

## 差异表

| | `reasonix` | `codex` |
|---|---|---|
| 默认模型 | `flash`（deepseek 档，比你便宜约两个数量级） | `luna`（前沿档，和你同级） |
| 备用档 | `--model pro` | `--model sol` / `--model terra` |
| 一次调用的量级 | ~24k 输入 | 十万级输入（多轮工具调用累加） |
| 角色档案 | Reasonix 自己查 `~/.agents/skills/` | `rx.py` 读出来拼进提示词 |
| 权限靠什么兜 | 项目根的 `reasonix.toml` | codex 的 `--sandbox`，**不需要项目级配置** |
| 报得了花费吗 | 报不了 | 报得了（token 数） |

不加 `--backend` 时：找得到 Reasonix 就用 Reasonix，否则用 Codex。
`DEVCYCLE_BACKEND` 环境变量可以固定，`--backend` 优先级更高。

## 什么时候值得切 codex

这条流程的经济学建立在「手比脑便宜」上——派一个和你同档的模型去干机械活，
省不出钱，只是把账挪了个地方。所以默认走 reasonix，只有这三种情况切：

- 这台机器没装 Reasonix，或者它的密钥没配好（`doctor` 里 `providers` 是空的）。
- 任务对代码质量敏感，deepseek 档连打回两轮还不绿——这时贵一次比来回三轮便宜。
- 项目没铺 `reasonix.toml`，又不想现铺。codex 后端不吃项目配置。

**切后端不改分工。** 设计审查仍然是你的，验收仍然要自己复跑，轮数上限仍然是 3。

## 切了以后这笔账要重算

codex 那边干活的是前沿档模型，「手比脑便宜」不成立了——一次 explore 就能吃掉
十几万输入 token。所以在 codex 后端下：

- **能自己 Grep 就别派 explore。**
- 任务要拆得更细、写得更死，减少它自己摸索的轮数
  （`[rx]` 行的 `cmds=` 就是它跑了多少条命令）。

## 全部开关

两个后端都吃的：

| 开关 | 作用 |
|---|---|
| `--max-chars N` | 裁回流正文，0=不裁 |
| `--dir PATH` | 默认从当前目录往上找项目根 |
| `--timeout SEC` | 默认 1800 |
| `--model` | 覆盖默认档。reasonix 认 `flash`/`pro`，codex 认 `luna`/`sol`/`terra` |

只有 reasonix 吃的：`--max-steps N`（卡轮数防跑飞）、`--permission-mode`。

只有 codex 吃的：

| 开关 | 作用 |
|---|---|
| `--sandbox` | 不给就按角色定：explore 只读、其余可写工作区 |
| `--codex-config K=V` | 透传 codex 的 `-c` |
| `--codex-home PATH` | 换一份 codex 配置跑 |

## codex 侧的花费怎么报

`[rx]` 行里的 `in= / cached= / out=` 是真的，照抄即可。
**不要自己按单价折算成钱**——你不知道用户走的是哪个计费口。

reasonix 侧报不了：`subagent run` 不支持 `--output-format json`，拿不到 usage 信封，
`[rx]` 那行只有正文规模、耗时和退出码。编一个数字出来比不报更糟。
要真实账单只能走 `run` 模式，但那样会丢掉档案自带的权限隔离
（verifier 的「没有写文件工具」就是靠档案兜的），不值得换。
