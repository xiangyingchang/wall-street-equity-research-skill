#!/usr/bin/env python3
"""Aggregate independent static failures; never repair or default research data."""
from __future__ import annotations
import argparse
import sys
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.report_compiler_v3 import compile_report_v3
from scripts.report_spec_v2 import SpecError


def _nonneg_dec(val) -> bool:
    try:
        d = Decimal(str(val))
        return d.is_finite() and d >= 0
    except (InvalidOperation, ValueError, TypeError):
        return False


def issues(spec):
    errors = []
    def walk(x, path=''):
        if isinstance(x, dict):
            for key, value in x.items():
                walk(value, path+'/'+str(key))
        elif isinstance(x, list):
            for i, value in enumerate(x): walk(value, path+'/'+str(i))
        elif isinstance(x, str) and ('TODO' in x or '{{' in x):
            errors.append(path+': unfinished scaffold')
    walk(spec)
    for key in ('report','sources','facts','assumptions','quarterly_series','scenarios','decision_policy','research','research_graph','decision_support','portfolio_context','prior_report_context'):
        if not isinstance(spec.get(key), dict) or not spec[key]: errors.append('/'+key+': required object missing')
    for registry in ('sources','facts','assumptions'):
        for key, value in spec.get(registry,{}).items():
            if not isinstance(value, dict): continue
            fields = {'sources':('url','date','locator','scope','publisher'), 'facts':('value','unit','source_ids'), 'assumptions':('rationale','confidence')}[registry]
            if registry == 'assumptions':
                mode = value.get('mode')
                fields += ('growth',) if mode in {'yoy', 'qoq'} else ('low', 'high') if mode in {'guide_midpoint', 'guide_high', 'guide_low'} else ('value',)
            for field in fields:
                if value.get(field) in (None,'',[]): errors.append(f'/{registry}/{key}/{field}: required evidence or judgment missing')
            if registry == 'facts' and 'uncertainty' in value and not _nonneg_dec(value.get('uncertainty')):
                errors.append(f'/facts/{key}/uncertainty: must be non-negative decimal (put text notes in note)')
    moat = (spec.get('research') or {}).get('moat') or {}
    if isinstance(moat, dict):
        if str(moat.get('trajectory', '')).lower() not in {'strengthening', 'stable', 'weakening'}:
            errors.append('/research/moat/trajectory: must be strengthening, stable, or weakening')
        for i, dim in enumerate(moat.get('dimensions') or []):
            if not isinstance(dim, dict): continue
            if not isinstance(dim.get('score'), int) or not (1 <= dim['score'] <= 5):
                errors.append(f'/research/moat/dimensions/{i}/score: must be integer 1..5')
            if len(str(dim.get('name') or '').strip()) < 12:
                errors.append(f'/research/moat/dimensions/{i}/name: must be >= 12 chars')
    levels = {'low', 'low_medium', 'medium', 'medium_high', 'high', 'very_high'}
    for i, item in enumerate(((spec.get('research') or {}).get('risks') or {}).get('items') or []):
        if not isinstance(item, dict): continue
        for tf in ('risk', 'mechanism', 'trigger', 'mitigant', 'action'):
            if len(str(item.get(tf) or '').strip()) < 12:
                errors.append(f'/research/risks/items/{i}/{tf}: must be >= 12 chars')
        for lf in ('probability', 'impact'):
            if str(item.get(lf, '')).lower() not in levels:
                errors.append(f'/research/risks/items/{i}/{lf}: must be in {sorted(levels)}')
    for i, drv in enumerate(((spec.get('research_graph') or {}).get('sensitivity') or {}).get('drivers') or []):
        if not isinstance(drv, dict): continue
        if str(drv.get('direction', '')).lower() not in {'positive', 'negative', 'mixed'}:
            errors.append(f'/research_graph/sensitivity/drivers/{i}/direction: must be positive, negative, or mixed')
        if str(drv.get('importance', '')).lower() not in {'high', 'medium', 'low'}:
            errors.append(f'/research_graph/sensitivity/drivers/{i}/importance: must be high, medium, or low')
        if len(str(drv.get('variable') or '').strip()) < 8:
            errors.append(f'/research_graph/sensitivity/drivers/{i}/variable: must be >= 8 chars')
    try: compile_report_v3(spec)
    except (SpecError, ValueError, KeyError, TypeError, ArithmeticError) as exc: errors.append('compiler: '+str(exc))
    return list(dict.fromkeys(errors))


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--spec',type=Path,required=True); a=p.parse_args()
    try: result=issues(json.loads(a.spec.read_text()))
    except (OSError,ValueError,TypeError) as exc: result=[str(exc)]
    print(json.dumps({'status':'FAIL' if result else 'PASS','errors':result},ensure_ascii=False,indent=2))
    return int(bool(result))

if __name__=='__main__': raise SystemExit(main())
