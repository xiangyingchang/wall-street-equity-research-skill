# PRD: 估值口径一致性与语义审计

## 状态

实施中 - 2026-07-31

## 背景

Meta 2026-07-30 报告通过了现有 lint 与 audit，但仍出现会直接改变投资结论的错误：

1. `$520` 对应的 FCF yield 与正文声明不一致；
2. `FCF/share $14.76` 在估值表中被写成 `$147.6`；
3. `$608.01亿 < $610亿` 却被描述为 beat 指引上限；
4. `+67%` 被描述为“翻倍”；
5. 首页 `<$520` 被称为安全买入区，模块 8 又把 `$400-$520` 定义为观察区；
6. normalized EPS `$22` 缺少从收入、利润率、税率、股数到 EPS 的完整桥接；
7. 目标价采用“悲观 EPS × 悲观倍数 × 再打安全折扣”，形成重复保守；
8. 10 年回本压力测试被事实上一票否决，超过了其“压力测试而非完整 DCF”的定位。

根因不是缺章节，而是现有系统主要校验结构存在、来源声明和部分数值单元格，没有约束估值口径的身份、调整项来源、情景引用关系与跨章节语义一致性。

## 目标

1. 每个进入估值的 EPS / FCF 基数都有唯一 `Basis ID`，可追溯到报告口径与调整项；
2. normalized / adjusted 指标必须有 One-off Adjustment Ledger，不允许无桥接“拍一个中枢”；
3. 公允价值、买入价、压力价格分开，禁止重复打折后仍称“公允价值”；
4. 情景估值可以复算：`metric × multiple = fair value`，`fair value × (1-safety margin) = buy price`；
5. 10 年回本保留为压力测试，但不得单独否决 Buy；主判断必须同时考虑情景 IRR / reverse expectations / 业务质量；
6. 高 Capex 公司必须区分 reported FCF、maintenance/owner earnings、growth/strategic capex，禁止直接把单季 FCF 年化成长期能力；
7. 新增独立语义审计脚本，在现有 lint 与 audit 之前运行，优先拦截数学和口径错误。

## 改动范围

### A. Valuation Basis Registry

模块 4 新增强制表：

| Basis ID | Metric | Value | Period | Adjustments | Use |
|---|---|---:|---|---|---|

规则：

- `Basis ID` 唯一；
- `Value` 必须是每股指标或明确单位；
- `Adjustments` 只能填 `None` 或 Adjustment ID 列表；
- 每个情景估值必须引用一个已注册 Basis ID；
- Bear / Base / Bull 必须使用清晰命名，不得把 Bear Case 偷换成“中枢”。

### B. One-off Adjustment Ledger

报告出现 normalized / adjusted / 核心 EPS / 核心 FCF 时，模块 2 必须包含：

| Adjustment ID | Period | Item | Pre-tax/after-tax | Cash/non-cash | Repeatability | Per-share impact | Treatment | Source |
|---|---|---|---|---|---|---:|---|---|

税务费用与税务收益必须对称处理；法务、重组等项目必须说明现金属性与重复概率。

### C. Scenario Valuation

模块 4 新增可复算表：

| Scenario | Basis ID | Metric value | Multiple | Fair value | Safety margin | Buy price | Key assumptions |
|---|---|---:|---:|---:|---:|---:|---|

语义：

- `Fair value` 是该情景的正常价值；
- `Buy price` 是在 fair value 上施加安全边际后的价格；
- `Stress price` 来自 Bear / Stress 情景，不得与 Base buy price 混称；
- 价格区间必须由该表派生，不得另起一套边界。

### D. Capex / Owner Earnings Bridge

高 Capex 公司必须列示：

- reported OCF；
- reported capex；
- reported FCF；
- maintenance capex；
- growth capex；
- strategic / AI capex；
- owner earnings / normalized FCF；
- 每个拆分的证据和置信度。

缺少公司披露时允许给区间或标记 Unclear，但不得把估计写成事实。

### E. 语义一致性脚本

新增 `scripts/valuation_consistency.py`，至少检查：

1. 必需表格与列名；
2. Basis ID 唯一、Adjustment ID 引用有效；
3. Scenario 引用有效；
4. fair value 与 buy price 可复算；
5. Bear ≤ Base ≤ Bull；
6. buy price ≤ fair value；
7. Evidence Ledger 中 PE、FCF yield 与 price/EPS/FCF-share 的基本重算；
8. normalized/adjusted 口径出现时必须有调整表；
9. 单季 FCF 年化用作长期估值时给出错误或警告；
10. “翻倍”与百分比、“beat 上限”与数字比较等明显语义冲突。

### F. 决策框架

- 10 年回本：压力测试，权重建议 20%，不得单独一票否决；
- 5 年情景 IRR：主估值框架，权重建议 50%；
- Reverse expectations / reverse DCF：检验当前价格隐含预期，权重建议 30%；
- 机会成本比较改为预期总回报 / IRR 对比，不要求当期 FCF yield 机械超过国债 ×2。

## 不在范围内

- 本批次不实现完整 DCF 引擎；
- 不自动判断 maintenance capex 的真实数值；
- 不自动抓取外部数据或替代人工来源验证；
- 不改变 9 模块顶层结构；
- 不自动修改历史报告；Meta 报告作为回归 fixture 在后续批次加入。

## 验证标准

1. 新模板包含 Basis Registry、Adjustment Ledger、Scenario Valuation、Capex Bridge；
2. `valuation_consistency.py` 对合格示例 PASS；
3. 对以下错误 FAIL：14.76/147.6 口径漂移、scenario 引用不存在、fair value 算错、buy price 高于 fair value、Bear/Base/Bull 逆序、normalized 无调整表；
4. `python3 -m py_compile scripts/*.py` PASS；
5. `python3 -m unittest discover -s tests` PASS；
6. `report_lint.py --self-test` 和 fixtures PASS；
7. `git diff --check` PASS；
8. PR 中清楚披露本批次未覆盖的自动化边界。
