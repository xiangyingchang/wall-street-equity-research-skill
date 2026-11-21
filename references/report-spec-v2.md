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


### 历史年度现金流例外（v3.2）
只披露年度现金流的公司可设 `cash_flow_basis={frequency:"annual",fact_id,period_end,reason}`，`quarterly_series.fcf=[]`。年度 Fact 必须有 `period:"FYyyyy"` 和同一 `period_end`；禁止未来数据与季度覆盖。兼容 `/derived/ttm/fcf/value` 仅为历史数值位置，必须同时读取 frequency/label/period_end，不代表最新 TTM。年度基准强制 `decision_support.cash_flow_escalation={status:"unknown",pending:"具体待披露项目"}`；不得提供 counter_ref、把未知计数填零。编译器限制新资金上限零且已有仓位 REVIEW，独立 thesis-break SELL 不受影响。旧报告未给 Base IRR 时允许 null，但 calculation_status 必须 unverified。
