# PRD：Data → Reasoning → Decision Reader v3.1

## 状态

完成 — 2026-08-01

## 问题

v3.0 的计算与审计能力比历史报告更强，但 Reader 反而更难用于决策：Research Graph 被直接摊平成固定三主题、固定三组 Bull/Bear，以及每个主题七个重复标签；关键假设藏在 Audit；来源缺少可点击 URL；经营闸门写死为 TTM FCF；缺少真实持仓权重时，Compiler 仍可直接输出 `REDUCE`。

这使报告看起来完整，却削弱了逻辑性、可参考性、实用性与可读性。根因不是字数或语气，而是数据、推理和写作三层没有清楚分工。

## 不变原则

最终投资判断继续由三条原则约束：

1. **持有等于买入**：若今天没有仓位，是否仍愿意按现价买入；
2. **机会成本**：单股回报必须胜过可投资替代方案并补偿集中风险；
3. **10 年回本**：用可复现的现金流或盈利路径检验现价要求，而不是把回本模型当口号。

Action Matrix 仍是唯一可执行交易口径；正文不能覆盖 Compiler 动作。

## 目标架构

```text
Tier 1 / market / portfolio sources
        ↓
Source Registry → Facts → Derived calculations → Assumptions
        ↓
Observations → competing explanations → resolution → falsification
        ↓
Three-principle decision gates → portfolio-context gate
        ↓
Reader Report + Audit Appendix + Bundle + Verification
```

### 1. 数据层

- v3.1 Source 必须有真实 URL、日期、发布者、文档类型、精确 locator 与 scope；拒绝 `Index provider`、`Peer investor relations`、`peer filings` 等占位来源。
- 关键 Fact 继续要求 Tier 1；市场价格可使用明确标注的 Tier 2。
- TTM 派生序列必须保持同类单位，避免把不同币种或量纲直接相加。
- 计算、假设和事实继续分离；Base/Bear/Bull 输出由 Decimal runtime 生成，不允许正文手算覆盖。
- Base 关键假设必须在 Reader 可见，并保留到 Audit 的完整注册表。
- 重新分析必须读取上一份可比报告；旧报告的“报告值”和 runtime 复算值分开保存，避免把历史计算错误当基线真相。首次覆盖必须写明没有基线的原因。

### 2. 推理层

- Themes 改为按公司材料动态生成 2–6 个，不再为了数量制造主题；每个 Theme 至少一个有效 Observation。
- Bull/Bear 各 2–6 个独立论点；Sensitivity 2–6 个变量，至少一个 high。
- Theme links 只需覆盖完整决策链：公司事实、估值、机会成本、仓位与最终判决；不再强迫每个九模块都映射到 Graph。
- Graph 继续保存在 Audit；Reader 将节点综合为自然段，不逐项输出七个编译器标签。

### 3. 决策层

- Operating policy 改为动态 `metrics[]`：每个指标声明 `value_ref`、方向、hold/reduce 阈值、容差、不确定性与确认期。可选 FCF、利润率、用户、订单、同店销售、库存、资本回报等公司特有指标。
- Compiler 分开输出“研究候选动作”和“可执行动作”。
- `portfolio_context` 必须明确 `held / not_held / unknown`。当候选动作为 `REDUCE`，但当前权重或目标权重缺失时，可执行动作降级为 `REVIEW`；不得伪造减仓幅度。
- `not_held` 的已有仓位动作输出 `NOT_APPLICABLE`；thesis-break 仍优先于估值闸门，但必须基于真实持仓状态解释执行。

### 4. Reader

第一页必须直接给出：

- 一个当前决策摘要，以及一个且仅一个六动作 Action Matrix（买入、加仓、持有、复核、减仓、卖出）；
- 当前价、Base IRR、门槛回报、目标回报价和安全边际价；
- 三条原投资原则逐条结论；
- Base 情景关键假设；
- 持仓数据完整性与任何执行限制。
- 与上一版相比的评级、关键指标、投资逻辑和方法变化；旧 IRR 若被复算，必须同时展示报告值与复算值。

正文保持九模块，但 Theme 用连续叙事组织：证据发生了什么、哪种解释更强、反方为何仍值得重视、什么事实会改变判断。Bull/Bear 改为紧凑对照，Sensitivity 显示实际 Base 值。主要来源必须可点击。

Reader 不再用行数下限伪装质量；只设置合理上限并检查决策内容、链接、假设、内部标识泄漏和旧式重复标签。

## 兼容边界

- v2/v2.1 旧编译路径保持可运行；v3.1 使用新 schema 和新 gate。
- 不自动联网、不伪造组合数据、不编辑生成后的 Markdown。
- 不改变现有估值和 10 年回本公式；本批次改输入质量、经营指标选择、动作可执行性和 Reader 组织。
- 不做隐式跨币种换算；如确需换算，必须在后续独立契约中增加 FX Fact、日期和公式。

## 验收标准

1. META v3.1 Reader 不包含七个旧标签，第一页可见三原则、Base 假设和唯一 Action Matrix。
2. META 来源均有真实 URL；占位来源或无 URL Source 构建失败。
3. Operating policy 可改用非 FCF 指标且能正确得出 hold/review/reduce。
4. 候选 `REDUCE` + 持仓未知或缺目标权重时，可执行动作必须为 `REVIEW`；上下文完整时才可 `REDUCE`。
5. Graph 接受动态 Theme、Bull/Bear 与 sensitivity 数量，同时继续验证反证、裁决和证据闭环。
6. Verification 的 source/calculation/portfolio checks 来自真实 bundle 检查，不写死 PASS。
7. META 历史报告中的 Base IRR 报告值 9.5% 与 runtime 复算值 1.64% 分开显示；伪造复算值构建失败。
8. Reader/Audit/Bundle/Verification 任一被修改后 verify 失败。
9. 全量单元测试、self-tests、fixtures、v2.1.2 E2E、v3.1 E2E、skill quick validation 和 Git diff check 全部通过。

## 非目标

- 本批次不重写全部估值引擎；
- 不用固定篇幅、固定 Theme 数量或大师人格评分代替判断；
- 不保证结构化推理本身正确，只保证证据、假设、计算、反证和动作边界可检查。

## 本地验证结果

- Python syntax：PASS；
- financial rigor / audit / lint self-tests：PASS；
- lint fixtures：PASS；
- 全量 unittest：184 / 184 PASS；
- v2.1.2 build + verify：PASS；
- v3.1 build + verify + integrated report lint：PASS；
- META Reader：261 行，旧七标签计数为 0，Action Matrix 计数为 1；
- source URLs / calculations / prior-report runtime / Reader / Audit / tamper checks：PASS；
- portfolio context：REVIEW（fixture 故意不提供真实权重，正确阻断候选 REDUCE）；
- skill quick validation：PASS；
- `git diff --check`：PASS。

## 独立审阅与远端验证

最终审阅发现并修复：

1. 低价规则可能在 thesis-break 已触发时仍允许新资金 BUY；
2. 初版 Action Matrix 只有当前动作，没有完整 Buy/Add/Hold/Review/Reduce/Sell 决策标准；
3. Reduce 文案未体现 valuation neutral band 对 operating trigger 的优先级；
4. 动态经营指标可声明与引用值不一致的单位；
5. 多期 confirmation 可把小数静默转成整数；
6. data-quality 总状态在 portfolio REVIEW 时仍写 PASS；
7. V3 Reader 与 legacy report lint 各自 PASS、互不相认；
8. 历史报告只记录旧 IRR 文本，没有用旧输入独立复算；
9. Source、税务身份、thesis-break 人类标签和历史基线缺少 fail-closed 输入门。

以上均已修复并加入回归。GitHub Actions Validate 首轮：push run 30694261919 PASS；PR run 30694275857 PASS。最终文档收口提交后再运行一次 CI。
