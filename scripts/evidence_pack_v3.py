#!/usr/bin/env python3
"""V3 evidence adapter using v1 canonical hashing, atomic writes and locks.
No model telemetry belongs here. Snapshots are immutable; publish a new path on revision.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, timezone
from copy import deepcopy
import json
from pathlib import Path
try:
    from .research_pack import canonical_hash, canonical_json_bytes, pack_write_lock, write_pack_atomic, _forbidden_key_issues
except ImportError:
    from research_pack import canonical_hash, canonical_json_bytes, pack_write_lock, write_pack_atomic, _forbidden_key_issues

SCHEMA='evidence-pack-v3'


def read(path):
    return json.loads(Path(path).read_text())


def sha_file(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def instant(text):
    value=datetime.fromisoformat(text.replace('Z','+00:00'))
    if value.tzinfo is None: raise ValueError('evidence timestamps need timezone')
    return value


def check(pack, spec, *, now=None):
    now=now or datetime.now(timezone.utc)
    errors=[]
    # The legacy schema remains strict and untouched; the envelope is versioned separately.
    errors.extend(_forbidden_key_issues(pack, 'evidence'))
    if set(pack)!={'schema_version','identity','sources','facts','snapshots','quarter_window','latest_period_end','content_hash'}:
        return errors+['evidence envelope has missing/unknown keys']
    core={k:v for k,v in pack.items() if k!='content_hash'}
    if pack['schema_version']!=SCHEMA or canonical_hash(core)!=pack['content_hash']:
        errors.append('evidence schema/hash mismatch')
    if pack['identity']!={'ticker':spec['report']['ticker'],'as_of':spec['report']['as_of']}:
        errors.append('evidence identity mismatch')
    for key in ('sources','facts'):
        if pack[key]!=spec[key]: errors.append(key+' differ from evidence snapshot; publish a revised pack')
    if pack['quarter_window']!=spec['quarterly_series']: errors.append('quarter window changed')
    if not pack['latest_period_end'] or pack['latest_period_end']>spec['report']['as_of']:
        errors.append('latest period invalid')
    if set(pack['snapshots'])!=set(pack['sources']): errors.append('every source requires a snapshot')
    for source_id, row in pack['snapshots'].items():
        try:
            required={'path','sha256','retrieved_at','verified_at','expires_at','published_or_quoted_at','locator','kind','verification_status','observed_sha256','latest_period_end'}
            if set(row)!=required: raise ValueError('snapshot fields missing/unknown')
            if row['kind'] not in {'filing','historical_quote','current_quote','rate','holdings','other'}: raise ValueError('bad snapshot kind')
            if row['verification_status']!='verified': raise ValueError('saved does not mean verified')
            if row['sha256']!=sha_file(row['path']) or row['observed_sha256']!=row['sha256']: raise ValueError('local or reopened URL content changed')
            retrieved=instant(row['retrieved_at']); verified=instant(row['verified_at']); expires=instant(row['expires_at'])
            if retrieved>now or verified>now or verified<retrieved or expires<=now or expires<=verified: raise ValueError('STALE/future timestamp or verification precedes retrieval')
            # Current market and private snapshots must not silently become evergreen.
            max_days={'current_quote':4,'rate':8,'holdings':1,'filing':93,'historical_quote':93,'other':31}[row['kind']]
            if (expires-verified).total_seconds()>max_days*86400: raise ValueError('revalidation interval too long')
            if not row['locator'] or not row['published_or_quoted_at']: raise ValueError('missing locator/date')
            quoted = date.fromisoformat(row['published_or_quoted_at'][:10])
            if quoted > now.date(): raise ValueError('future evidence date')
            if row['kind'] in {'current_quote','rate','holdings'} and (now.date()-quoted).days > max_days:
                raise ValueError('STALE observation date; re-fetching an old quote does not make it current')
            if row['kind']=='filing' and row['latest_period_end']!=pack['latest_period_end']: raise ValueError('new quarter requires REVIEW')
        except (KeyError,ValueError,TypeError,OSError) as exc: errors.append(f'{source_id}: {exc}')
    for fact_id,fact in pack['facts'].items():
        if not fact.get('source_ids') or not fact.get('unit') or not (fact.get('as_of') or fact.get('period_end') or fact.get('period')) or fact.get('value') is None:
            errors.append(f'{fact_id}: incomplete value/unit/period/source')
    return errors


def create(spec, manifest):
    core={'schema_version':SCHEMA,'identity':{'ticker':spec['report']['ticker'],'as_of':spec['report']['as_of']},'sources':spec['sources'],'facts':spec['facts'],'snapshots':manifest['snapshots'],'quarter_window':spec['quarterly_series'],'latest_period_end':manifest['latest_period_end']}
    return deepcopy({**core,'content_hash':canonical_hash(core)})


def require_pack(path, spec):
    pack=read(path); errors=check(pack,spec)
    if errors: raise ValueError('evidence REVIEW: '+'; '.join(errors))
    return pack


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('create','check','apply'));p.add_argument('--spec',required=True,type=Path);p.add_argument('--pack',required=True,type=Path);p.add_argument('--manifest',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
    try:
        spec=read(a.spec)
        if a.command=='create':
            if not a.manifest: raise ValueError('create requires --manifest')
            pack=create(spec,read(a.manifest)); errors=check(pack,spec)
            if errors: raise ValueError('; '.join(errors))
            with pack_write_lock(a.pack):
                if a.pack.exists() and read(a.pack)!=pack: raise ValueError('immutable snapshot exists; use new pack filename')
                write_pack_atomic(a.pack,pack,lock_held=True)
        elif a.command=='apply':
            if not a.out or a.out.exists(): raise ValueError('apply requires a new --out')
            pack=read(a.pack)
            for key in ('sources','facts'):spec[key]=pack[key]
            errors=check(pack,spec)
            if errors: raise ValueError('; '.join(errors))
            with a.out.open('xb') as handle:handle.write(canonical_json_bytes(spec,pretty=True))
        else: require_pack(a.pack,spec)
        print('PASS: '+str(a.pack));return 0
    except (ValueError,KeyError,TypeError,OSError) as exc: print('FAIL: '+str(exc));return 1

if __name__=='__main__':raise SystemExit(main())
