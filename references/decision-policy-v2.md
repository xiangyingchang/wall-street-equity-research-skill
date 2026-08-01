# Decision Policy v2

## Separate two decisions

Every report must output:

1. `new_money_action`: BUY / WATCH / DO_NOT_BUY
2. `existing_position_action`: HOLD / REVIEW / REDUCE / SELL

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

Required fields:

- metric
- hold_threshold
- reduce_threshold
- tolerance
- uncertainty
- confirmation

Tolerance and uncertainty are separate, explicit inputs. Narrative text cannot add another buffer.

### Thesis break

Contains typed conditions with Fact ID, operator, and value. SELL is reserved for thesis-break conditions.

## Resolution order

1. Thesis break → SELL
2. Base IRR materially below hurdle → REDUCE
3. Valuation in explicit neutral band → REVIEW
4. Operating reduce → REDUCE
5. Operating neutral band → REVIEW
6. Otherwise → HOLD

If robustness shocks change the action, downgrade to REVIEW unless SELL is independently triggered.

## Price-zone semantics

- at or below buy price: 安全边际买入区
- buy price to target-return price: 目标回报达标区
- target-return price to forward reference: 回报不足观察区
- above forward reference: 估值偏高区

Only the first zone is named “买入区” when the Action Policy also permits BUY.
