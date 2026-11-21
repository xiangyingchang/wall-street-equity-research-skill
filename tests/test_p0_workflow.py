from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from scripts.evidence_pack_v3 import check, create, sha_file
from scripts.spec_precheck import issues
from scripts.run_reports import run
from tests.meta_v3_spec import make_spec


class P0WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.spec=make_spec()
        self.raw=self.root/'source.txt';self.raw.write_text('verified primary original')
        now=datetime.now(timezone.utc)
        self.now=now
        row={'path':str(self.raw),'sha256':sha_file(self.raw),'retrieved_at':(now-timedelta(minutes=2)).isoformat(),'verified_at':(now-timedelta(minutes=1)).isoformat(),'expires_at':(now+timedelta(hours=2)).isoformat(),'published_or_quoted_at':'2026-07-31','locator':'table, row and page','kind':'filing','verification_status':'verified','observed_sha256':sha_file(self.raw),'latest_period_end':'2026-06-30'}
        self.manifest={'latest_period_end':'2026-06-30','snapshots':{k:deepcopy(row) for k in self.spec['sources']}}

    def pack(self):return create(self.spec,self.manifest)

    def test_valid_spec_and_adapter(self):
        self.assertEqual(issues(self.spec),[])
        self.assertEqual(check(self.pack(),self.spec,now=self.now),[])

    def test_new_scaffold_has_no_company_facts_or_assumptions(self):
        target=self.root/'new.json'
        cmd=[sys.executable,str(ROOT/'scripts/new_report.py'),'--format','v3-spec','--ticker','TEST','--company','Test','--market','US','--out',str(target)]
        self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,0)
        spec=json.loads(target.read_text());old=target.read_bytes()
        self.assertTrue(all(v['value'] is None for v in spec['facts'].values()))
        self.assertTrue(all(v.get(k) is None for v in spec['assumptions'].values() for k in ('value','growth','low','high')))
        self.assertNotIn('Meta',target.read_text());self.assertNotIn('atmeta',target.read_text())
        self.assertGreater(len(issues(spec)),10)
        self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)
        self.assertEqual(target.read_bytes(),old)

    def test_aggregates_gaps(self):
        self.spec['sources'].clear();self.spec['facts'].clear();self.spec['research']['overview']['thesis']['text']='TODO'
        self.spec['research']['moat']['trajectory']='中文描述'
        self.spec['research']['moat']['dimensions'][0]['score']=8
        self.spec['research']['moat']['dimensions'][0]['name']='太短'
        self.spec['research']['risks']['items'][0]['risk']='太短'
        self.spec['research_graph']['sensitivity']['drivers'][0]['direction']='higher_is_better'
        self.spec['research_graph']['sensitivity']['drivers'][0]['variable']='太短'
        result=issues(self.spec)
        self.assertTrue(any('/sources' in e for e in result));self.assertTrue(any('/facts' in e for e in result));self.assertTrue(any('unfinished' in e for e in result))
        self.assertTrue(any('/research/moat/trajectory' in e for e in result))
        self.assertTrue(any('/research/moat/dimensions/0/score' in e for e in result))
        self.assertTrue(any('/research/moat/dimensions/0/name' in e for e in result))
        self.assertTrue(any('/research/risks/items/0/risk' in e for e in result))
        self.assertTrue(any('/research_graph/sensitivity/drivers/0/direction' in e for e in result))
        self.assertTrue(any('/research_graph/sensitivity/drivers/0/variable' in e for e in result))

    def test_unbound_action_and_missing_v32_still_fail(self):
        self.spec['research']['final_verdict']['hold_equals_buy']={'text':'当前价格不会成为新的主动买入选择。','evidence_refs':['BUNDLE:/decision/new_money_action'],'confidence':'medium'}
        self.assertTrue(any('migrate static conclusions' in x for x in issues(self.spec)))
        self.spec=make_spec();del self.spec['decision_support']
        self.assertTrue(issues(self.spec))

    def test_bad_pointer_fx_adr_and_annual_still_fail(self):
        cases=[]
        s=make_spec();s['research']['final_verdict']['hold_equals_buy']['value_refs']['bad']={'path':'/does/not/exist','format':'action'};cases.append(s)
        s=make_spec();s['report']['price_currency']='HKD';s['report']['fx_fact_id']='FACT-MISSING-FX';cases.append(s)
        s=make_spec();s['report']['cash_valuation']['shares_fact_id']='FACT-MISSING-ADR-SHARES';cases.append(s)
        from tests.test_annual_cash_basis import annual_spec
        s=annual_spec();s['cash_flow_basis']['period_end']='2027-12-31';cases.append(s)
        for spec in cases:
            with self.subTest():self.assertTrue(issues(spec))

    def test_stale_quote_and_unknown_not_current(self):
        for kind in ('current_quote','holdings','rate'):
            self.manifest['snapshots'][next(iter(self.manifest['snapshots']))].update(kind=kind,expires_at=(self.now-timedelta(seconds=1)).isoformat())
            self.assertTrue(any('STALE' in e for e in check(self.pack(),self.spec,now=self.now)))
        self.manifest['snapshots'][next(iter(self.manifest['snapshots']))]['verification_status']='saved'
        self.assertTrue(any('saved does not mean verified' in e for e in check(self.pack(),self.spec,now=self.now)))

    def test_recent_fetch_does_not_refresh_old_quote(self):
        row=self.manifest['snapshots'][next(iter(self.manifest['snapshots']))]
        row.update(kind='current_quote',published_or_quoted_at=(self.now-timedelta(days=10)).date().isoformat())
        self.assertTrue(any('STALE observation date' in e for e in check(self.pack(),self.spec,now=self.now)))
        row.update(kind='historical_quote')
        self.assertEqual(check(self.pack(),self.spec,now=self.now),[])

    def test_create_freezes_caller_data(self):
        pack=self.pack()
        self.spec['facts'][next(iter(self.spec['facts']))]['value']='changed'
        self.assertTrue(any('facts differ' in e for e in check(pack,self.spec,now=self.now)))

    def test_queue_completed_resume_rechecks_and_rejects_tampered_reader(self):
        from scripts.report_pipeline_v3 import build
        spec=self.root/'spec.json';spec.write_text(json.dumps(self.spec))
        out=self.root/'out.md';build(spec,out)
        (self.root/'pack.json').write_text(json.dumps(self.pack()))
        (self.root/'completion.json').write_text(json.dumps({'status':'done','report_path':str(out)}))
        (self.root/'semantic.json').write_text(json.dumps({'status':'PASS','reader_sha256':sha_file(out),'perspectives':['business','financial','challenge','risk']}))
        job={'id':'one','notion_delivery':False,'workdir':str(self.root),'research_command':[sys.executable,'-c','raise SystemExit(99)'],'spec':str(spec),'output':str(out),'evidence_pack':str(self.root/'pack.json'),'completion':str(self.root/'completion.json'),'semantic_review':str(self.root/'semantic.json')}
        queue=self.root/'queue.json';queue.write_text(json.dumps({'jobs':[job]}))
        (self.root/'queue-state.json').write_text(json.dumps({'jobs':{'one':{'status':'running','stage':'research','stages':{'research':{'spec_sha256':sha_file(spec)}}}}}))
        self.assertEqual(run(queue)['jobs']['one']['status'],'done')
        self.assertEqual(run(queue)['jobs']['one']['status'],'done')
        rows=[json.loads(x) for x in (self.root/'run-metrics.jsonl').read_text().splitlines()]
        self.assertEqual(sum(x['stage']=='build' for x in rows),1)
        self.assertEqual(sum(x['stage']=='verify' for x in rows),2)
        self.assertEqual(sum(x['stage']=='lint' for x in rows),2)
        self.assertFalse(any(x['stage']=='research' for x in rows))
        out.write_text(out.read_text()+'tampered')
        with self.assertRaisesRegex(ValueError,'semantic review missing/stale'):run(queue)
        state=json.loads((self.root/'queue-state.json').read_text())
        self.assertEqual(state['jobs']['one']['status'],'failed')

    def test_remote_hash_local_hash_quarter_and_missing_fields(self):
        pack=self.pack();self.raw.write_text('same URL different original')
        self.assertTrue(check(pack,self.spec,now=self.now))
        self.raw.write_text('verified primary original')
        key=next(iter(self.manifest['snapshots']))
        self.manifest['snapshots'][key]['observed_sha256']='0'*64
        self.assertTrue(check(self.pack(),self.spec,now=self.now))
        self.manifest['snapshots'][key]['observed_sha256']=sha_file(self.raw)
        self.manifest['snapshots'][key]['latest_period_end']='2026-09-30'
        self.assertTrue(any('new quarter' in e for e in check(self.pack(),self.spec,now=self.now)))
        pack=self.pack();s=deepcopy(self.spec);s['quarterly_series']['fcf'].reverse()
        self.assertTrue(any('quarter window' in e for e in check(pack,s,now=self.now)))
        del self.manifest['snapshots'][key]['locator']
        self.assertTrue(check(self.pack(),self.spec,now=self.now))

    def test_telemetry_separate_and_mutation_blocked(self):
        pack=self.pack();pack['tokens']=123
        self.assertTrue(any('telemetry' in e for e in check(pack,self.spec,now=self.now)))
        pack=self.pack();self.spec['facts'][next(iter(self.spec['facts']))]['value']='123'
        # deepcopy required: in-memory create doesn't freeze a caller's mutable dict.
        # Persisted adapter reads independent JSON objects in production.
        pack=json.loads(json.dumps(self.pack()));self.spec['facts'][next(iter(self.spec['facts']))]['value']='124'
        self.assertTrue(any('facts differ' in e for e in check(pack,self.spec,now=self.now)))

    def test_queue_failure_saves_checkpoint_and_resume(self):
        for name,data in [('spec.json',self.spec),('pack.json',self.pack()),('completion.json',{'status':'done','report_path':str(self.root/'out.md')})]: (self.root/name).write_text(json.dumps(data))
        job={'id':'one','notion_delivery':False,'workdir':str(self.root),'research_command':[sys.executable,'-c','raise SystemExit(1)'],'spec':str(self.root/'spec.json'),'output':str(self.root/'out.md'),'evidence_pack':str(self.root/'pack.json'),'completion':str(self.root/'completion.json'),'semantic_review':str(self.root/'semantic.json')}
        queue=self.root/'queue.json';queue.write_text(json.dumps({'jobs':[job]}))
        with self.assertRaisesRegex(ValueError,'research failed'):run(queue)
        state=json.loads((self.root/'queue-state.json').read_text());self.assertEqual(state['jobs']['one']['status'],'failed');self.assertNotIn('research',state['jobs']['one']['stages'])
        self.assertTrue((self.root/'run-metrics.jsonl').exists())
        # Same failed job is run again; logs append, never falsely marked done.
        with self.assertRaises(ValueError):run(queue)
        self.assertEqual(len((self.root/'run-metrics.jsonl').read_text().splitlines()),2)
        state=json.loads((self.root/'queue-state.json').read_text());self.assertEqual(state['jobs']['one']['status'],'failed')

    def test_queue_stop_and_disjoint_paths(self):
        queue=self.root/'queue.json';queue.write_text(json.dumps({'jobs':[]}))
        stop=self.root/'STOP';stop.touch();self.assertEqual(run(queue,stop_file=stop)['jobs'],{})

    def test_queue_default_limit_preserves_second_job(self):
        jobs=[]
        for i in range(2):
            folder=self.root/str(i);folder.mkdir()
            spec=folder/'spec.json';spec.write_text(json.dumps(self.spec))
            (folder/'pack.json').write_text(json.dumps(self.pack()))
            job={'id':str(i),'notion_delivery':False,'workdir':str(folder),'research_command':['fake-research',str(i)],'spec':str(spec),'output':str(folder/'out.md'),'evidence_pack':str(folder/'pack.json'),'completion':str(folder/'completion.json'),'semantic_review':str(folder/'semantic.json')}
            jobs.append(job)
        queue=self.root/'queue.json';queue.write_text(json.dumps({'jobs':jobs}))
        real_run=subprocess.run
        def launch(argv,**kwargs):
            if argv[0]!='fake-research':return real_run(argv,**kwargs)
            job=jobs[int(argv[1])]
            from scripts.report_pipeline_v3 import build
            build(Path(job['spec']),Path(job['output']))
            Path(job['completion']).write_text(json.dumps({'status':'done','report_path':job['output']}))
            Path(job['semantic_review']).write_text(json.dumps({'status':'PASS','reader_sha256':sha_file(job['output']),'perspectives':['business','financial','challenge','risk']}))
            return subprocess.CompletedProcess(argv,0)
        with patch('scripts.run_reports.subprocess.run',side_effect=launch):
            state=run(queue)
            self.assertEqual(list(state['jobs']),['0'])
            self.assertFalse(Path(jobs[1]['output']).exists())
            state=run(queue,max_jobs=2)
            self.assertEqual([x['status'] for x in state['jobs'].values()],['done','done'])
        events=[json.loads(x) for x in (self.root/'run-metrics.jsonl').read_text().splitlines()]
        self.assertEqual([e['job'] for e in events if e['stage']=='research'],['0','1'])
        # New jobs may not claim existing delivered output, even with valid evidence.
        jobs[0]['id']='new-id';queue.write_text(json.dumps({'jobs':[jobs[0]]}))
        before=Path(jobs[0]['output']).read_bytes()
        with self.assertRaisesRegex(ValueError,'pre-existing output'):run(queue)
        self.assertEqual(Path(jobs[0]['output']).read_bytes(),before)

    def test_new_queue_waits_for_notion_after_verify_and_resumes(self):
        runs=self.root/'runs';runs.mkdir();work=runs/'META';work.mkdir()
        (work/'spec.json').write_text(json.dumps(self.spec))
        (work/'evidence.json').write_text(json.dumps(self.pack()))
        out=work/'reader.md'
        job={'id':'META','research_command':['fake-research']}
        queue=runs/'queue.json';queue.write_text(json.dumps({'jobs':[job]}))
        real_run=subprocess.run
        def launch(argv,**kwargs):
            if argv[0]!='fake-research':return real_run(argv,**kwargs)
            from scripts.report_pipeline_v3 import build
            build(work/'spec.json',out)
            (work/'completion.json').write_text(json.dumps({'status':'done','report_path':str(out)}))
            (work/'semantic-review.json').write_text(json.dumps({'status':'PASS','reader_sha256':sha_file(out),'perspectives':['business','financial','challenge','risk']}))
            return subprocess.CompletedProcess(argv,0)
        with patch('scripts.run_reports.subprocess.run',side_effect=launch):
            state=run(queue);self.assertEqual(state['jobs']['META']['status'],'awaiting_notion')
            self.assertEqual(run(queue)['jobs']['META']['status'],'awaiting_notion')
        self.assertFalse((work/'delivery.json').exists())
        self.assertTrue(all(p.exists() for p in [work/'spec.json',out.with_suffix('.audit.md'),Path(str(out)+'.bundle.json'),Path(str(out)+'.verification.json')]))

    def test_duplicate_output_paths_rejected_before_launch(self):
        job={'id':'one','notion_delivery':False,'workdir':str(self.root),'research_command':['not-run'],**{k:str(self.root/(k+'.json')) for k in ('spec','output','evidence_pack','completion','semantic_review')}}
        second={**job,'id':'two'}
        queue=self.root/'queue.json';queue.write_text(json.dumps({'jobs':[job,second]}))
        with self.assertRaisesRegex(ValueError,'disjoint artifact'):run(queue)
