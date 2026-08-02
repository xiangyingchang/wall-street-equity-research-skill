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
