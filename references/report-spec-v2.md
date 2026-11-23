# Report Spec v2 Contract

## One editable source

A new report starts from one JSON file with `schema_version=report-spec-v2`. The JSON is the only editable analytical source. Markdown, calculated tables, decisions, price zones, Bundle, and Verification are compiler outputs.

## Required top-level objects

```text
report
facts
quarterly_series
assumptions
scenarios
decision_policy
narrative
sources
```

## Facts

Each fact requires:

- value
- unit
- period or as_of
- source
- tier
- confidence
- uncertainty when material

Facts are external observations. They are never model outputs.

## Quarterly series

`eps`, `revenue`, `operating_income`, and `fcf` each contain exactly four Fact IDs. The compiler derives TTM sums and ratios.

## Assumptions

Each assumption requires:

- scope: `global`, `bear`, `base`, or `bull`
- role
- rationale
- confidence
- scalar value or mode-specific fields

A scenario may reference only assumptions with its own scope or `global` scope.

## Revenue modes

- `guide_midpoint`: low, high, source
- `guide_high`: low, high, source
- `yoy`: growth and a prior-year same-quarter base reference
- `qoq`: growth and an immediately prior-quarter base reference
- `explicit`: value, source, rationale
- `consensus`: value, source, as_of

Do not put a growth percentage in a `guide_midpoint` assumption's value field. Guide modes are defined by low/high.

## Scenario requirements

Bear, Base, and Bull each require four forward revenue periods and assumption references for:

- operating_margin
- tax_rate
- other_income
- diluted_shares
- eps_cagr
- exit_pe
- dividend_yield
- reference_multiple
- safety_margin

## Outputs

The compiler emits:

- report Markdown
- `report-bundle-v2` JSON
- `report-verification-v2` JSON

These outputs are reproducible from the Spec. Manual edits invalidate verification.

## v3.1 overlay

`report-spec-v3.1` keeps the v2 numerical core and adds `research`, `research_graph`, explicit `portfolio_context`, and explicit `prior_report_context`. It also requires:

- every Source to include a valid HTTPS `url`, ISO date no later than report `as_of`, publisher, document type, precise locator, and scope;
- no generic index/peer/source placeholders;
- `decision_policy.require_portfolio_context=true`;
- company-specific `decision_policy.operating.metrics[]`;
- homogeneous currency and scale for revenue, operating income, and FCF TTM series;
- the same per-share currency unit for EPS and current price.

Facts, calculations, assumptions, and portfolio observations remain distinct. Missing portfolio data is represented as `position_status=unknown`; it is never filled by inference. `current_weight` means the stock's market value divided by verified total net assets. A separately verified `stock_pool_weight` means its share of all active listed-stock market value; it excludes cash and other assets and cannot authorize a portfolio trade. When total net assets or the user's target weight is missing, preserve REVIEW even if the stock-pool ratio is available.

Each operating metric's declared unit must equal the unit on its referenced Fact or derived object. Multi-period confirmation must resolve to an explicit non-negative integer Fact/Bundle value; fractional or silently assumed confirmation fails build.

`prior_report_context` is `available` or `not_available`. Available baselines record prior actions, reported Base IRR, rating/metric/thesis/method deltas, and calculation status. `recalculated` status requires the old price, starting EPS, EPS CAGR, exit PE, years, and dividend yield; the Compiler recomputes the old IRR and rejects a mismatching declared value. This preserves historical wording without preserving historical arithmetic errors.


### v3 可读研报（Skill 3.4.3 起）

`report_pipeline_v3.py build` 先生成并检查原编译内容，再从同一个 Bundle 输出一份报告。标题下写阅读顺序，正文依次为「现在怎么做」「经营证据」「估值」「什么会改变仓位判断」，第五节为「附录｜财务底稿、估值明细与执行规则」。

- 首节体现新资金、已有仓位可执行动作及有差异的研究候选，并前置参考价与日期、目标回报价、安全边际价及对应距离。
- 正文的事实、数值、单位、限定、回报口径和执行条件沿用编译内容，只压缩重复和改写表达。要调整公司专属措辞，修改 Spec 的相关文字，保留数值绑定和来源。
- 附录保留完整编译底稿。Action Matrix、敏感性、财务表、经营闸门、比较和执行规则仍按原契约检查。Audit、Bundle、Verification 作为内部审计产物留存。
- `verify` 重新生成整份可读报告并逐字比对。Verification 和语义审阅凭据绑定最终报告的哈希，独立 lint 核验正文结构及附录的原契约。旧报告独立 lint 仍受支持，采用新结构的报告须重新 build、语义审阅及 verify。


### 历史年度现金流例外（v3.2）
只披露年度现金流的公司可设 `cash_flow_basis={frequency:"annual",fact_id,period_end,reason}`，`quarterly_series.fcf=[]`。年度 Fact 必须有 `period:"FYyyyy"` 和同一 `period_end`；禁止未来数据与季度覆盖。兼容 `/derived/ttm/fcf/value` 仅为历史数值位置，必须同时读取 frequency/label/period_end，不代表最新 TTM。年度基准强制 `decision_support.cash_flow_escalation={status:"unknown",pending:"具体待披露项目"}`；不得提供 counter_ref、把未知计数填零。编译器限制新资金上限零且已有仓位 REVIEW，独立 thesis-break SELL 不受影响。旧报告未给 Base IRR 时允许 null，但 calculation_status 必须 unverified。
