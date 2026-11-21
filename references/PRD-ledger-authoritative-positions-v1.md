# PRD：Ledger 权威持仓与行情取数边界 v1

状态：完成
日期：2026-08-02

## 背景

Obsidian 中的旧 Dashboard 已经过时，股票报告仍可能把 Dashboard 当作当前仓位来源。Ledger 项目才是当前交易记录、持仓数量和组合资产的运行时来源。与此同时，AI-伯克希尔的财务数据 Skill 没有通用且稳定的美股行情接口：FinMind 工具只覆盖台股；它真正可复用的能力是双源交叉验证和 `financial_rigor.py` 精确验算。

## 目标

1. 将 Ledger 明确为当前持仓事实的唯一优先来源，禁止报告默认引用旧 Dashboard。
2. 提供一个只读的 Ledger 持仓预检脚本，输出持仓数量、代码、市场、货币、价格、价格时间和来源元数据，不保存认证令牌。
3. 将 Ledger 持仓数据与行情数据分层：Ledger 负责回答“持有什么、多少、当前快照是什么”；公司 IR、监管文件和市场行情源负责回答“公司价值和最新市场价格”。
4. 借鉴 AI-伯克希尔的双源交叉验证、差异标记和 `financial_rigor.py` 市值/估值验算规则。

## 规则

- 当前持仓状态使用鉴权后的 Ledger `/api/stocks`；只把 `amount > 0` 的记录认定为 active position。零数量记录保留为历史记录，不得当作持仓。
- Ledger `/api/allocation` 可用于组合桶和配置快照，但必须记录读取时间和 warning；由于该接口当前使用保存的 `Stock.currentPrice`，不能单独作为实时市值或实时仓位比例来源。
- Ledger 行情只能作为持仓快照和价格交叉验证，不能替代 SEC/公司 IR 或独立市场行情源。
- Ledger 连接失败、认证失败、快照为空、价格没有时间戳或快照超过有效期时，报告必须写明“持仓未核验”，不得对 existing position 给出 Reduce/Sell 的确定动作；只能给 new-money research action。
- 关键财务数据至少有两个独立来源；差异超过 1% 标记复核，超过 5% 必须回到原始财报。市值和估值使用精确十进制重算。

## 交付物

- `scripts/ledger_portfolio_preflight.py`
- 更新 `SKILL.md`、`references/report-contract.md`、`references/source-map.md` 和模板中的持仓来源说明。
- `tests/test_ledger_portfolio_preflight.py`
- 变更记录集成到 `references/change-log.md`。

## 验收标准

- 无 token 时脚本安全失败并给出认证提示；token 不出现在输出、日志或文件中。
- `/api/stocks` 返回混合 active/zero 记录时，只输出 active position，并保留 `retrieved_at`、endpoint、price timestamp 和 warning。
- Ledger `/api/allocation` 失败时，持仓数量仍可独立读取；脚本明确标记 allocation unavailable。
- 未提供 Ledger 快照时，报告契约明确禁止把旧 Dashboard 或记忆中的仓位写成当前事实。
- `python3 -m py_compile scripts/*.py tests/*.py`、完整 unittest、lint self-test、fixtures 和 `git diff --check` 全部通过。

## 完成记录

- 新增 Ledger 预检脚本和 9 个单元测试，覆盖 active position 过滤、缺失/过期时间戳、分配接口降级、异常/空 payload 和 URL 凭据保护。
- 已更新 Skill、报告契约、来源地图、方法论和模板；已同步到 `.agents` 与 `.codex` 的本机安装目录。
- 已完成 `py_compile`、完整 unittest、lint self-test、fixtures、无 token fail-closed 和 `git diff --check` 验证。

## 非目标

- 本 PRD 不把 AI-伯克希尔的 FinMind 接口扩展成美股行情接口。
- 本 PRD 不修改 Ledger 的生产行情提供商；Ledger 的 Sina 行情仍需按 Tier 2 / 快照数据处理。
- 本 PRD 不把认证 token 写入 Skill、报告、仓库或变更记录。

## 2026-10-22 后续：稳定只读认证

### 问题

研究预检切换到 Ledger `/api/stocks` 后只接受短期 `LEDGER_AUTH_TOKEN`，但投研运行环境没有持续注入该登录令牌；脚本还默认访问 `localhost:3000`。Ledger 已有长期、只读的 `ledger-research-token` Keychain 凭证和 `/api/research/holdings` 接口，旧预检却没有使用它们。

### 改动

- 单股票报告优先从 macOS Keychain 的 `ledger-research-token` 读取长期只读凭证，并通过 `X-Ledger-Research-Token` 查询 `/api/research/holdings`。
- 只有 Keychain 凭证不存在或被 Ledger 拒绝时，才使用 `LEDGER_AUTH_TOKEN` 会话回退；不接受命令行 token，不输出或保存 token。
- 默认 API 地址设为当前 Ledger 生产服务；保留 `LEDGER_API_BASE_URL` 覆盖，并把请求超时设为 30 秒，对临时网络失败最多重试一次。
- 把“持仓是否存在”和“价格/市值/组合权重是否可靠”分开。认证接口返回正持仓即可确认 `held`；报价过期或缺少组合资产/汇率时，当前权重仍为空且可执行动作继续受 REVIEW 闸门限制。
- 组合闸门在 `held` 但 `current_weight` 缺失时强制 `REVIEW`；只有已确认持仓的 thesis-break `SELL` 可以在没有权重时通过，避免把无法执行的 `HOLD` 或 `REDUCE` 当成已核实的组合动作。

### 验收

- Keychain 读取和真实只读接口均可在不打印 token 的情况下成功。
- 活跃持仓数量在报价缺失或过期时仍保留；相关价格和权重必须标记为不可用。
- 已确认持仓但当前权重缺失时，组合动作必须为 `REVIEW`；已确认持仓且触发 thesis-break 时，独立 `SELL` 仍可执行。
- 未认证、认证失败、无活跃快照、异常 payload 和网络超时继续失败关闭；不能据此推断用户没有持仓。
- 重跑预检单测、完整仓库验证、腾讯只读预检和 `git diff --check`。

## 2026-10-22 后续：补上股票池占比，保留总资产权重边界

### 原因

只读研究接口只返回持仓数量和证券信息；它不返回现金、其他资产或总资产净值。完整 `/api/allocation` 需要普通登录会话，且用 Ledger 保存的股票价格计算市值。研究令牌权限不能读这个接口，保存价格也可能过期。因此报告缺少的是“总资产这个分母”，不是持仓数量。不能把全部股票中的比例冒充总资产权重。

### 改动

- 另外计算 `stock_pool_weight`：单只股票人民币市值 ÷ 所有活跃股票人民币市值。每个持仓都要有两家独立、带报价时间或交易日期的行情；优先选择 Yahoo、Nasdaq、腾讯和新浪中可用且相差不超过 1% 的来源组合。缺失报价日期、价格过旧、价格来自未来或双源差异超过 1% 时，不输出结果。
- 港币与美元折算校验 Frankfurter、open.er-api、currency-api 三个独立每日汇率源；任意两家新鲜来源相差不超过 1% 才可计算，并检查更新时间。任一来源断连时仍尝试另外两家。
- `current_weight` 仍只表示该股票市值 ÷ 已核实的全部资产净值。只读令牌拿不到该分母时，保持 `null`。`target_weight` 不推断，缺失时现有仓位动作保持 REVIEW。
- Reader 用直白文字标记“占全部股票市值的比例”，说明现金及其他资产不在分母内；行情时间不同则显示日期范围。

### 验收

- 断网、单源、过时报价、未来时间戳、币种不一致或汇率差异超限时均失败关闭。
- Yahoo 不可用时，可由另外两家独立、有效的报价源完成交叉核对。
- Reader 可显示股票池比例，但 `current_weight` 和总资产可执行动作不因此被填值或放行。
- 真实只读持仓预检仍能确认全部活跃持仓；报告明确标记总资产权重未知。

## 2026-10-22 后续：Ledger 净资产摘要

- 生产 Ledger 增加只读 `GET /api/research/portfolio-summary`，仅使用现有研究令牌的新独立 scope。接口只返回 CNY 净资产总额、估值日期、各类输入的新鲜度和公开汇率，不返回账户名或单项金额。
- 预检用全部活跃股票的双源新鲜报价替换净资产摘要内 Ledger 保存的股票市值，再计算 `current_weight`。现金、期权、加密资产、负债或汇率任一来源过期、缺时点或不可估值时，仍把 `current_weight` 留空并保持 REVIEW。
- Reader 必须写明“占组合净资产的比例”和净资产估值日期。目标权重仍需用户明确提供，不能从现有持仓推断。
