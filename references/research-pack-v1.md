# Research Pack v1

`research-pack-v1` is an optional durable recovery checkpoint for a report run. It preserves canonical source metadata, typed facts, the exact valuation basis, and ordered stage hashes so interrupted work can resume without reconstructing settled inputs.

It is not provider, model, token, timing, retry, or runtime telemetry. It does not fetch data, prove that a source is true, replace the Markdown report, or replace `report_lint.py` and `report_audit.py`.

## Create a pack

```bash
python3 scripts/research_pack.py init \
  --pack "/path/to/report.research-pack.json" \
  --ticker META \
  --market US \
  --report "/path/to/report.md" \
  --previous-report "/path/to/previous-report.md"
```

`--previous-report` is optional. At initialization, `report` and `previous_report` paths are resolved to absolute paths so checkpoint identity is stable across working-directory changes. Report, previous-report, and pack paths must not be symlinks. A new pack contains exactly these top-level keys:

```text
schema_version, identity, report, previous_report, sources, facts,
derived_records, valuation_basis, action_matrix, evidence_gates, checkpoints
```

Unknown or missing top-level or defined nested keys fail validation. JSON is strict: duplicate object keys, `NaN`, `Infinity`, and `-Infinity` are rejected. The keys `provider`, `model`, `token`, `tokens`, `finish_reason`, `timing`, `retry`, `runtime`, `latency`, `duration`, `started_at`, and `ended_at` are forbidden case-insensitively and recursively anywhere in the pack. Legitimate evidence fields such as `market_date` and `as_of` remain required. JSON writes are atomic, UTF-8, sorted, deterministic, and idempotent. Repeating an operation with the same canonical input returns `UNCHANGED` and leaves the bytes untouched. Every skill-supported pack writer holds the same persistent sibling advisory lock across its complete read/validate/mutate/replace sequence. This prevents lost updates between cooperative skill writers; it does not and cannot exclude an unrelated process that bypasses the lock and directly mutates the file.

`scripts/new_report.py` can initialize the pack after skeleton recognition:

```bash
# Derive /path/to/META.research-pack.json beside /path/to/META.md
python3 scripts/new_report.py \
  --ticker META --company Meta --market US --out "/path/to/META.md" \
  --research-pack

# Or choose the pack path and record continuity explicitly
python3 scripts/new_report.py \
  --ticker META --company Meta --market US --out "/path/to/META.md" \
  --research-pack "/path/to/state/META.json" \
  --previous-report "/path/to/previous-META.md"
```

Omitting `--research-pack` preserves the legacy generator workflow and its historical stdout: one report-path line. Recognition runs silently unless it fails. The generator rejects report/pack symlinks and report-pack path collisions, validates arguments and pack conflicts before touching an existing report, stages report and pack bytes in their destination directories, and rolls back the report if the pack commit fails. A failed `--force` run leaves existing report and pack bytes unchanged and removes temporary files.

## Register sources

`source-add` accepts a strict JSON object with exactly these fields:

```json
{
  "url": "https://www.sec.gov/Archives/example",
  "title": "Quarterly report",
  "publisher": "SEC",
  "tier": "Tier 1",
  "published_date": "2026-06-30"
}
```

`published_date` may be `null`; the other fields are required. `tier` is `Tier 1`, `Tier 2`, or `Internal`.

```bash
python3 scripts/research_pack.py source-add --pack <pack.json> --source <source.json>
```

URLs must be HTTPS. Before `urlsplit`, the original URL is rejected if any ASCII control character (`0x00`-`0x1F`) or DEL (`0x7F`) appears anywhere in its authority, path, query, or fragment; newline and tab are never silently stripped into a colliding URL. The authority also rejects other whitespace. Canonicalization lowercases the scheme and host, maps IDNA separator variants `。`, `．`, and `｡` to ASCII `.`, strips DNS trailing dots before and after IDNA, removes fragments and the default HTTPS port, preserves path case, repeated internal path slashes, and meaningful query order, and removes exactly one non-root trailing slash. These equivalent host spellings therefore share one canonical URL and source ID. Identical canonical URL plus identical metadata is `UNCHANGED`; different metadata or a source-ID collision fails closed.

## Register typed facts

`fact-add` accepts a strict JSON object with exactly these fields:

```json
{
  "fact_id": "ttm_eps",
  "field": "TTM EPS",
  "value_type": "decimal",
  "value": "27.50",
  "unit": "USD/share",
  "as_of": "2026-06-30",
  "source_ids": ["sha256:<source-id-hex>"]
}
```

```bash
python3 scripts/research_pack.py fact-add --pack <pack.json> --fact <fact.json>
```

`value_type` is `decimal`, `date`, or `string`. Decimal values must be finite JSON strings; dates must be real canonical `YYYY-MM-DD` values. `unit` may be `null`. Source IDs are sorted and deduplicated. Facts may be added before their sources, but undefined source references block `validate` and `facts_ready`.

## Register derived records

`derived-add --pack <pack.json> --record <record.json>` accepts exactly `id`, `formula_id`, `inputs`, `computed`, `reported`, `rounding`, and `binding`. Inputs are reference-only:

- `fact_ref`: exactly `name`, `kind`, and `fact_id`; it resolves value, unit, `as_of`, and source IDs from a registered decimal fact.
- `derived_ref`: exactly `name`, `kind`, and `derived_record_id`; it recursively resolves the registered record's exact result, output unit, latest resolved `as_of`, and transitive source IDs.
- `literal`: exactly `name`, `kind`, `value`, and `unit`; it is allowed only for a positive integer payback `years` value with unit `year`.

Callers must not copy `value`, `unit`, `as_of`, or `source_ids` into `fact_ref` or `derived_ref`. `ttm_sum_v1` adds required `period` in canonical `FYyyyy-Qn` form to each reference. `ttm_bridge_v1` adds required `role`, integer `fiscal_year`, and integer `duration_quarters` to each reference. Computed and reported objects contain only `value` and `unit`; rounding is exactly `ROUND_HALF_UP` plus integer `places` from 0 through 12; binding is exactly `section`, `label`, and `column`.

Registered formulas are `sum_v1`, `difference_v1`, `product_v1`, `ratio_v1`, `ttm_sum_v1`, `ttm_bridge_v1`, `payback_ttm_v1`, and `payback_forward_v1`. Input names must be unique; undefined facts/records, reference cycles, and unregistered transitive sources fail closed. TTM sum requires four consecutive unique fiscal quarters, strictly increasing resolved `as_of` dates, adjacent 70-115 day spacing, and each `FYyyyy-Qn` label within one calendar year of its date. Every four-quarter set contains exactly one Q4; that `FYyyyy-Q4` period end must have calendar year exactly `yyyy`, which rejects a coherent-looking whole-set year shift while retaining non-calendar fiscal years and 52/53-week spacing. TTM bridge requires `fy` duration 4, equal current/prior YTD durations from 1 through 3, adjacent fiscal years, and `prior_ytd < fy < current_ytd`; the annual FY period end year must exactly equal its declared fiscal year, current/prior YTD dates are 350-385 days apart, and both bridge legs fit 13-week-per-quarter windows with 35-day 52/53-week tolerance. One aggregate TTM input or detached fiscal chronology is invalid.

Units are algebra, not labels. Supported computed units are `USD`, `USD_B`, `shares`, `shares_B`, `USD/share`, `ratio`, `x`, and `year`; `%` is report-only. Additive formulas require identical units. Ratios support equal dimensions with scale conversion, `USD_B / shares_B -> USD/share`, and `USD / shares -> USD/share`. Products support `ratio * X -> X`, `USD/share * shares_B -> USD_B`, and `USD/share * shares -> USD`. Payback requires `multiple=x`, `discount_rate=ratio`, and `years=year`. Other dimensions and fake scales fail. The stored computed value must equal recursive Decimal-50 evaluation; reported must equal the declared `ratio`/`%` conversion and `ROUND_HALF_UP` rounding.

Identical records return `UNCHANGED` without rewriting bytes. Reusing an ID with different content or referencing an undefined fact, record, or transitive source fails. A new derived record removes `matrix_ready` and every downstream checkpoint.

## Checkpoints

Stages are ordered:

```text
initialized -> sources_ready -> facts_ready -> valuation_locked ->
matrix_ready -> draft_ready -> audit_passed
```

```bash
python3 scripts/research_pack.py checkpoint --pack <pack.json> --name sources_ready
python3 scripts/research_pack.py checkpoint --pack <pack.json> --name facts_ready
```

Each checkpoint stores only deterministic hashes and no wall-clock time. A stage requires every predecessor to be `CURRENT` under a freshly recomputed hash; merely having a predecessor key is insufficient. Repeating the same stage and hash returns `UNCHANGED`. Adding a source removes `sources_ready` and every later checkpoint. Adding a fact removes `facts_ready` and every later checkpoint. Adding a derived record removes `matrix_ready` and every later checkpoint. `draft_ready` includes the current report hash. Generic checkpoint API/CLI cannot create `audit_passed`; only successful v5 verdict persistence can add its upstream, report, pre-audit pack, and manifest-binding hashes.

`evidence_gates` remains the empty object `{}`. `action_matrix` is an array of JSON objects; Batch 2C added a strict per-entry schema. Each entry must have exactly `action` (Buy/Add/Hold/Reduce/Sell), `trigger_type` (price/valuation/operating/thesis-break), `condition` (nonempty string), `execution` (nonempty string), and `na` (boolean; true only for Buy or Add). Unknown keys, missing keys, invalid actions or trigger types, empty condition/execution, a non-boolean `na`, or `na: true` on Hold/Reduce/Sell fail `validate` and `status`. An empty array remains valid. The entry schema is a structural check only; it does not parse free-text conditions.
When a pack's `action_matrix` is non-empty, Audit v5 also runs a semantic correspondence check: the report's module 9 Action Matrix table must declare the same action set and trigger-type set as the pack entries, with no missing or extra actions or trigger types. A missing or malformed report table blocks extract and verdict. An empty pack `action_matrix` skips the check, so existing packs and the no-pack v4 path are unaffected.

## Audit v5

After derived records are bound to numeric report cells and checkpoints through `draft_ready` are current:

```bash
python3 scripts/report_audit.py extract --report <report.md> --pack <pack.json> --manifest-out <manifest.json>
python3 scripts/report_audit.py verdict --report <report.md> --pack <pack.json> --manifest <manifest.json>
```

V5 has no results file and never treats user-supplied fresh values as authority. Report, pack, and manifest paths must be distinct and not symlinks. Each command reads report/pack/manifest bytes once into validated immutable snapshots; public snapshot constructors reject report-text/report-bytes, parsed-pack/pack-bytes, and parsed-manifest/manifest-bytes mismatches using recursive exact Python container and scalar types, so a tuple cannot impersonate a JSON list. Extract requires one unique Markdown cell per record, constructs the prospective final pack including `audit_passed`, and atomically writes a manifest binding that final pack SHA-256 plus the canonical pre-audit input, report, records, cells, and audit-binding hash. Duplicate JSON keys fail before evaluation.

Verdict acquires the shared pack advisory lock, re-reads and compares the on-disk bytes inside that lock, then reconstructs the prospective final pack, reruns recursive formulas and payback tolerances, reapplies unit algebra/conversion/rounding, compares cells, and commits without releasing the lock. A concurrent cooperative skill writer completes first or waits, so verdict blocks on a changed snapshot instead of overwriting that update. A blocked or failed verdict writes nothing; arbitrary filesystem mutation by a process that ignores the advisory lock is outside this cooperative guarantee. The persisted pack's actual SHA-256 equals manifest `pack_sha256`, and an identical verdict rerun remains `PASS` without rewriting bytes. Using `--results` with v5 or `--pack` with v4 is an explicit usage error. Legacy v4 results authority, manifest bytes, decision logic, and numeric parser remain unchanged, including rejection of `$10/share`; v4 additionally requires distinct report/manifest/results paths, rejects symlink outputs, and writes manifest/results through one rollback-capable atomic transaction.

## Lock valuation inputs

The basis file has exactly this shape:

```json
{
  "price": {
    "value": "595.19",
    "currency": "USD",
    "kind": "regular_close",
    "market_date": "2026-07-29",
    "source_id": "sha256:<price-source-id-hex>"
  },
  "shares": {
    "value": "2538000000",
    "as_of": "2026-06-30",
    "source_id": "sha256:<shares-source-id-hex>"
  }
}
```

Price and shares are positive Decimal strings. Currency is a three-letter uppercase code. Price `kind` is one of `regular_close`, `intraday`, `pre_market`, or `after_hours`. Every source ID in the current basis and revision history must exist in the source registry.

```bash
python3 scripts/research_pack.py valuation-lock --pack <pack.json> --basis <basis.json>
```

The command requires `facts_ready`, writes the canonical basis, and creates `valuation_locked`. The locked basis cannot change through `valuation-lock`.

For a real correction or market-basis change, use a nonempty reason:

```bash
python3 scripts/research_pack.py revise-valuation \
  --pack <pack.json> --basis <revised-basis.json> \
  --reason "Use the confirmed regular-session close"
```

Revision history records the canonical old basis, new basis, and reason. It records no timestamp. Revision clears `valuation_locked` and every downstream checkpoint; rerun `valuation-lock` to confirm the revised basis.

`revise-valuation` requires `initialized`, `sources_ready`, and `facts_ready` all to be `CURRENT` under recomputed hashes. It may replace a stale `valuation_locked` checkpoint only after those upstream checkpoints have been re-established as current; stale or merely present upstream keys cannot authorize a revision.

## Validate and resume

```bash
python3 scripts/research_pack.py validate --pack <pack.json>
python3 scripts/research_pack.py status --pack <pack.json>
```

`status` emits deterministic JSON with each stage marked `CURRENT`, `MISSING`, or `STALE`, plus `next_checkpoint`. It returns nonzero when the pack is invalid. Exit codes are stable: `0` for valid success or `UNCHANGED`, `1` for a valid-state conflict such as stale/undefined upstream inputs, and `2` for malformed structure, invalid usage/input, non-strict JSON, or I/O. Malformed-but-parseable types produce a stable `ERROR:` on stderr without a traceback.

Resume from the first missing or stale checkpoint, but re-open the cited sources before making a current investment decision. A valid pack proves internal structure and continuity, not real-world freshness or provenance.
