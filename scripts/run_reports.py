#!/usr/bin/env python3
"""Sequential report launcher with durable stage hashes and append-only telemetry.
Queue JSON: {jobs:[{id, workdir, research_command:[...], spec, output,
evidence_pack, completion, semantic_review}]}. Never pass shell code or full history.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import fcntl
import json
import re
from pathlib import Path
import subprocess
import sys
import time
from research_pack import canonical_hash, write_pack_atomic
from evidence_pack_v3 import require_pack, read, sha_file
from notion_delivery import read_receipt

SCRIPTS=Path(__file__).resolve().parent
ARTIFACTS = {'spec': 'spec.json', 'output': 'reader.md', 'evidence_pack': 'evidence.json',
             'completion': 'completion.json', 'semantic_review': 'semantic-review.json'}


def prepare_job(job, root):
    # Use native Notion delivery for new jobs unless explicitly local-only.
    if 'vault_output' in job:
        raise ValueError('retired delivery setting vault_output; use a new Notion job ID')
    if not job.get('notion_delivery', True):
        return job
    job = dict(job, notion_delivery=True)
    identifier = job['id']
    if not re.fullmatch(r'[A-Za-z0-9_-]+', identifier):
        raise ValueError('job ID must contain only letters, digits, underscore or hyphen')
    workdir = Path(job.get('workdir', root / identifier))
    if not workdir.is_absolute() or workdir.resolve() != root / identifier:
        raise ValueError('Notion jobs require a dedicated queue-dir/job-id directory')
    job['workdir'] = str(workdir)
    for key, name in ARTIFACTS.items():
        path = Path(job.get(key, workdir / name))
        if not path.is_absolute() or path.parent.resolve() != workdir.resolve():
            raise ValueError(key + ' must be directly inside the run directory')
        job[key] = str(path)
    return job


def engine_hash():
    return canonical_hash({str(p.relative_to(SCRIPTS.parent)):sha_file(p) for folder in ('scripts','templates') for p in sorted((SCRIPTS.parent/folder).rglob('*')) if p.suffix in {'.py','.json','.md'} and p.is_file()})


def run(queue_path, max_jobs=1, stop_file=None):
    queue_path=queue_path.resolve(); queue=read(queue_path); root=queue_path.parent
    state_path=root/'queue-state.json';metrics=root/'run-metrics.jsonl'
    state=read(state_path) if state_path.exists() else {'jobs':{}}
    # Do not reopen completed jobs from the retired delivery workflow.
    jobs = [job for job in queue['jobs'] if not (
        'vault_output' in job and state['jobs'].get(job['id'], {}).get('status') == 'done'
    )]
    queue['jobs'] = [
        job if 'notion_delivery' not in job and all(key in job for key in ARTIFACTS)
        and state['jobs'].get(job['id'], {}).get('config_hash') == canonical_hash(job)
        else prepare_job(job, root) for job in jobs
    ]
    seen=set(); outputs=set(); new_workdirs=set()
    for job in queue['jobs']:
        if job['id'] in seen: raise ValueError('duplicate job ID')
        seen.add(job['id'])
        if job.get('notion_delivery'):
            workdir=Path(job['workdir']).resolve()
            if workdir in new_workdirs: raise ValueError('new jobs must have disjoint workdirs')
            new_workdirs.add(workdir)
        for key in ('spec','output','evidence_pack','completion','semantic_review'):
            p=Path(job[key])
            if not p.is_absolute(): raise ValueError(key+' must be absolute')
            if str(p.resolve()) in outputs: raise ValueError('jobs must have disjoint artifact paths')
            outputs.add(str(p.resolve()))
    processed=0
    for job in queue['jobs']:
        if processed>=max_jobs or (stop_file and stop_file.exists()):break
        processed+=1
        Path(job['workdir']).mkdir(parents=True,exist_ok=True)
        identifier=job['id']; record=state['jobs'].setdefault(identifier,{'status':'pending','stages':{}})
        # Pin each ID to its command and output paths; changing jobs cannot inherit completion.
        config_hash=canonical_hash(job)
        if record.get('config_hash',config_hash)!=config_hash:raise ValueError('job config changed; use new ID')
        record['config_hash']=config_hash
        def save():write_pack_atomic(state_path,state)
        def command(stage,args):
            record['status']='running';record['stage']=stage;save()
            started=time.monotonic();log=(Path(job['workdir']) if job.get('notion_delivery') else root)/(identifier+'-'+stage+'.log')
            with log.open('ab') as stream:
                result=subprocess.run(args,cwd=job['workdir'],stdout=stream,stderr=subprocess.STDOUT)
            with metrics.open('a') as stream:stream.write(json.dumps({'job':identifier,'stage':stage,'elapsed_seconds':time.monotonic()-started,'exit_code':result.returncode,'timestamp':datetime.now(timezone.utc).isoformat(),'log':str(log)})+'\n')
            if result.returncode:raise ValueError(stage+' failed; resume artifacts in '+job['workdir'])
        try:
            spec=Path(job['spec']);out=Path(job['output']);pack=Path(job['evidence_pack'])
            paths=[out,out.with_suffix('.audit.md'),Path(str(out)+'.bundle.json'),Path(str(out)+'.verification.json')]
            delivery = Path(job['workdir']) / 'delivery.json'
            if job.get('notion_delivery') and delivery.exists():
                record['stages']['delivery'] = read_receipt(delivery, out)
                record['status'] = 'done'
                record['stage'] = 'complete'
                record.pop('error', None)
                save()
                continue
            # Research is resumable via saved evidence/spec, never via inherited chat history.
            if not record['stages'].get('research'):
                if any(p.exists() for p in paths) and record.get('stage') is None:
                    raise ValueError('refuse pre-existing output; choose isolated job path')
                command('research',job['research_command'])
                receipt=read(job['completion'])
                if receipt.get('status')!='done' or Path(receipt.get('report_path','')).resolve()!=out.resolve():raise ValueError('research completion missing or failed')
                record['stages']['research']={'spec_sha256':sha_file(spec)};save()
            require_pack(pack,read(spec))
            fingerprint=canonical_hash({'spec':sha_file(spec),'evidence':sha_file(pack),'engine':engine_hash()})
            old=record.get('fingerprint')
            if old!=fingerprint:record['stages']={k:v for k,v in record['stages'].items() if k=='research'}
            record['fingerprint']=fingerprint;save()
            command('precheck',[sys.executable,str(SCRIPTS/'spec_precheck.py'),'--spec',str(spec)])
            if not record['stages'].get('build') or not all(p.exists() for p in paths):
                command('build',[sys.executable,str(SCRIPTS/'report_pipeline_v3.py'),'build','--spec',str(spec),'--output',str(out),'--evidence-pack',str(pack)])
                record['stages']['build']={'hashes':{str(p):sha_file(p) for p in paths}};save()
            # Human/model semantic receipt is not produced by deterministic checks.
            review=read(job['semantic_review'])
            if review.get('reader_sha256')!=sha_file(out) or review.get('status')!='PASS' or set(review.get('perspectives',[]))!={'business','financial','challenge','risk'}:
                raise ValueError('full Reader semantic review missing/stale; re-open relevant evidence and save review')
            # Always rerun full verify and the separate lint, including resumed/done jobs.
            command('verify',[sys.executable,str(SCRIPTS/'report_pipeline_v3.py'),'verify','--spec',str(spec),'--output',str(out),'--evidence-pack',str(pack)])
            record['stages']['verify']={'fingerprint':fingerprint};save()
            command('lint',[sys.executable,str(SCRIPTS/'report_lint.py'),str(out)])
            record['stages']['lint']={'fingerprint':fingerprint};save()
            record['status'] = 'awaiting_notion' if job.get('notion_delivery') else 'done'
            record['stage'] = 'complete'
            record.pop('error', None)
            save()
        except (ValueError,OSError,KeyError,TypeError) as exc:
            record['status']='failed';record['error']=str(exc);save();raise
    return state


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--queue',type=Path,default=Path.home()/'research-runs'/'queue.json');p.add_argument('--max-jobs',type=int,default=1);p.add_argument('--stop-file',type=Path);a=p.parse_args()
    try:
        if a.max_jobs<1:raise ValueError('max-jobs must be positive')
        lock=a.queue.resolve().parent/'.queue.lock';lock.parent.mkdir(parents=True,exist_ok=True)
        with lock.open('a') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            result=run(a.queue,a.max_jobs,a.stop_file)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:print('FAIL: '+str(exc));return 1

if __name__=='__main__':raise SystemExit(main())
