# V3.2 生产入口与窄契约

对应复盘 P0-1/2/3。schema_version 仍是 report-spec-v3.1；v3.2 是其必需决策字段。

1. `python3 scripts/new_report.py --format v3-spec --ticker MU --company Micron --market US --date 2026-11-06 --out /new/run/spec.json`。只创建新路径，绝不使用测试公司数值。骨架自动生成唯一 ID、保留引用和 action 绑定模板。null/TODO 需要逐项填写；可按实际财报重建四季/情景行，不要沿用骨架行数作为研究要求。
2. 先填 Sources（HTTPS URL/date/locator/scope/publisher/tier），再填 Facts（value/unit/as_of/period/period_end/source_ids；可选 `uncertainty` 仅限非负十进制数，默认 `"0"`，文字说明须放 `note`）和 assumptions（value/rationale/confidence）。财务金额以 report.currency 的亿为单位；每股量以上市货币。财年季度和现金流口径遵照 report-spec-v2.md。
3. scenario 的 base/bear/bull、决策/研究图结构见骨架；主观假设、容差、阈值、数量和估值参数均未默认。合法 enum 与长度：operating.metrics.direction=higher_is_better/lower_is_better；sensitivity.drivers.direction=positive/negative/mixed（`variable` 至少 8 字）；moat.trajectory=strengthening/stable/weakening，`moat.dimensions[].score` 为整数 1..5 且 `name` 至少 12 字；`risks.items[]` 的 `risk/mechanism/trigger/mitigant/action` 至少 12 字，`probability/impact` 取 low/low_medium/medium/medium_high/high/very_high；evidence role=supports/context/counter_evidence，accounting_basis=reported/adjusted，position_status=unknown/held/none（以原契约为准）。
4. `value_refs` 指向编译 Bundle 的 JSON Pointer，例如 `/decision/new_money_action` + format=action，`/decision/valuation/base_irr`，`/derived/ttm/revenue/value`。`assumption_ref` 指向 `/assumptions/<ASM-ID>/value`；BUNDLE: 前缀只用于 evidence/value_ref 契约允许的位置。不要靠猜测拼路径；预检保留原编译器全部检查。
5. 最终总结、持有=买入、debate adjudication、每个 Theme decision impact 都保留 action 模板绑定。v3.2 必填：report.cash_valuation 的 decisive_basis/reason、每种利润 accounting_basis；decision_support 的 peers≥3、risks≥5、ROIC、cash_flow_escalation、归一化 method、trigger existing_action；每个分配资金阶梯有 ladder_premises.conditions。
6. `python3 scripts/spec_precheck.py --spec spec.json` 会一起报告可独立发现的缺失及占位符，并执行原编译校验。它不代替 build/verify/lint；编译依赖链上的错误仍可能在填补后显示。

## 证据与顺序运行

按 research-pack-v1.md 的 V3 adapter 创建证据包。每个 research 子任务只给任务、所需契约、相关 Fact/原文摘录和输出路径；不传旧会话或全 Spec/Audit。保留完整 business/financial/challenge/risk 视角与全文读者审阅。

`run_reports.py --queue /run/queue.json --max-jobs 1` 是实际外层启动器；默认一次只开一份，队列从不并行。每个 job 字段：id、workdir、research_command（argv 数组，如 codex exec 的参数）、spec、output、evidence_pack、completion、semantic_review（全部绝对路径）。research_command 的提示词须明确：同目录断点恢复、写全五产物、完整读 Reader、保留研究视角、不得改旧报告；不能继承全上下文。研究负责人固定 Sol/medium；窄机械任务经同输入验收后按 SKILL 的模型路由表执行，使用 run_model_task.py 固定模型与 effort，候选输出不得自动合并。

semantic_review JSON：`status: PASS`、`reader_sha256`（全文审阅后实际 Reader SHA256）、`perspectives: [business, financial, challenge, risk]`，并写审阅发现及最强反方/反证阈值；缺失或 hash 改变阻断 done。completion 是队列研究阶段的本地完成信号，用户要求的最终完成信号须在交付后另写。它们是模型/人工签署的语义记录，不是机器证明事实正确。

启动器在 research 成功后做静态预检→有需要才 build→检查语义记录→完整 verify→独立 lint，所有阶段状态原子写入 queue-state.json，日志追加不覆盖。断点恢复先校验 Spec、证据、编译器/模板指纹；仍执行完整 verify/lint。research 失败时同 argv 重启，提示词必须要求复用同目录中有效证据而不是重新开目录。已有输出的新 job 被拒绝；已完成 job 重跑只验证，不重新研究。

`--stop-file /run/STOP` 在当前报告完成本地校验后阻止开下一份；额度接近上限时设置该文件。不能读取精确剩余额度，默认 max-jobs=1；调用方负责在研究中及时保存证据/Spec。运行耗时、退出码和日志位置追加到 run-metrics.jsonl；token 仍从 codex 日志尾数或唯一 usage 事件读取，不将缓存总量混用。


## v3.4 Notion 交付

新队列任务可仅提供 `id` 和 `research_command`（argv）。其他产物默认为 `<queue-dir>/<id>/{spec.json,reader.md,evidence.json,completion.json,semantic-review.json}`，也可指定该目录内的绝对路径。已有队列状态的显式路径历史任务延续本地校验。新任务默认进入 Notion，明确设 `notion_delivery: false` 可只做本地验证。旧 `vault_output` 已退役，已完成的历史任务会跳过，未完成的任务用新 ID 配置。

本地验收结束的队列状态为 `awaiting_notion`。调用方依 [Notion 交付](notion-delivery.md) 通过原生 MCP 写入、回读和执行清理。队列再次运行时可用回执和 Reader 的 SHA-256 确认已交付，无需恢复已清理产物。独立 build 和 verify 仍支持显式路径。
