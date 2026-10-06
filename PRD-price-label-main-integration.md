# Price label integration into main — 2026-10-06

## Scope

Merge `feat/a99-quality-hardening` while retaining main's newer v3.1 Spec,
Compiler, Reader, verification, portfolio gates and single Action Matrix.
Then install the verified main snapshot locally, preserving the previous install.

## Requirements

- Preserve main's existing validation and report architecture during conflict resolution.
- Retain the standalone valuation math and read-only Ledger preflight utilities and tests.
- Include the five-line Chinese price table in the legacy template and reference contract.
- Validate complete Chinese first-column labels whenever this table is present,
  including in v3.1 Readers; reject labels placed in later columns or prefix-only matches.
- Do not impose the retired branch's report layout on v3.1 or invent new Bundle gates.
- Keep historical branch-specific validation results clearly dated.

## Acceptance

- Repository syntax, self-tests, fixtures and complete unit suite pass.
- Both v2.1.2 and v3.1 sample build/verify paths pass the CI artifact checks.
- Main contains the reviewed branch by ancestry, and remote HEAD matches.
- The local installed skill matches tracked main files byte for byte; the old install is backed up.

## Limits

No fresh financial research, live Ledger fetch or trading action is performed.
The older branch's general lint tests are superseded by main's existing contract
tests; the new Chinese-label regressions remain. The legacy five-price formula
table does not replace the active v3.1 compiler or its executable price policy.
