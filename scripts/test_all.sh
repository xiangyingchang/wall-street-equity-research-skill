#!/bin/sh
# Fail immediately if any verification step fails.
set -eu
cd "$(dirname "$0")/.."
python3 -m compileall -q scripts tests
python3 scripts/financial_rigor.py --self-test
python3 scripts/report_audit.py --self-test
python3 scripts/report_lint.py --self-test
python3 scripts/report_lint.py --fixtures tests/fixtures
python3 -m unittest discover -s tests -t .
