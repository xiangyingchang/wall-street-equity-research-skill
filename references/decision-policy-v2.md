# Decision Policy v2

## Separate two decisions

Every report must output:

1. `new_money_action`: BUY / WATCH / DO_NOT_BUY
2. `existing_position_action`: HOLD / REVIEW / REDUCE / SELL

v3.1 additionally outputs `existing_position_candidate_action`. The candidate is the company-research result; the executable action is the candidate after the portfolio-context gate. `NOT_APPLICABLE` is valid when the portfolio confirms no position.

This prevents “not attractive for new money” from being silently converted into either HOLD or SELL.

## Mandatory dimensions

### Valuation

Required fields:

- reduce_gap: minimum IRR shortfall versus hurdle that supports REDUCE
- review_band: explicit neutral band around the valuation decision
- buy_below: must reference Base buy price
- add_below: must reference Base buy price

The Hold=Buy principle is executable only when valuation participates in the existing-position decision.

### Operating

v3.1 requires a non-empty company-specific `metrics[]`. Every metric has:

- metric_id and human label
- `value_ref`: a Fact ID or `BUNDLE:/...` JSON Pointer
- direction: `higher_is_better` or `lower_is_better`
- hold_threshold and reduce_threshold
- tolerance and uncertainty
- confirmation_periods; when greater than one, a confirmation_ref

Any confirmed reduce metric dominates; otherwise any neutral metric produces review; only all-hold metrics produce hold. The v2 legacy single `ttm_fcf` object remains supported only on old compiler paths.

Tolerance and uncertainty are separate, explicit inputs. Narrative text cannot add another buffer.

### Thesis break

Contains typed conditions with Fact ID, operator, and value. SELL is reserved for thesis-break conditions.

## Resolution order

1. Thesis break → candidate SELL
2. Base IRR materially below hurdle → candidate REDUCE
3. Valuation in explicit neutral band → candidate REVIEW
4. Operating reduce → candidate REDUCE
5. Operating neutral band → candidate REVIEW
6. Otherwise → candidate HOLD

If robustness shocks change the action, downgrade to REVIEW unless SELL is independently triggered.

Then apply `portfolio_context`:

- `not_held` → `NOT_APPLICABLE` for an existing position;
- `unknown` → `REVIEW`;
- candidate `REDUCE` requires `held`, current_weight, and a lower target_weight; otherwise → `REVIEW`;
- complete context preserves the candidate.

This gate prevents a company report from inventing portfolio execution. Tax friction and constraints must still be disclosed even when they do not change the action.

The v3.1 Reader renders one compact current-decision table and one authoritative six-row Action Matrix: Buy, Add, Hold, Review, Reduce, Sell. The matrix conditions are generated from the actual buy price, valuation bands, operating status, thesis-break labels, and portfolio gate; they are not free-text rules authored after compilation.

## Price-zone semantics

- at or below buy price: 安全边际买入区
- buy price to target-return price: 目标回报达标区
- target-return price to forward reference: 回报不足观察区
- above forward reference: 估值偏高区

Only the first zone is named “买入区” when the Action Policy also permits BUY.
