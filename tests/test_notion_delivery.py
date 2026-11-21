from argparse import Namespace
import json
from datetime import datetime, timedelta, timezone
import zipfile
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from notion_delivery import PERSPECTIVES, finalize, read_receipt, sha_file
from scripts.evidence_pack_v3 import create
from tests.meta_v3_spec import make_spec


class NotionDeliveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        self.run = root / 'job'
        self.run.mkdir()
        self.reader = self.run / 'reader.md'
        self.reader.write_text('# Verified Reader\n')
        self.receipt = self.run / 'delivery.json'
        self.review = self.run / 'semantic-review.json'
        self.review.write_text(json.dumps({
            'status': 'PASS', 'reader_sha256': sha_file(self.reader), 'perspectives': list(PERSPECTIVES),
        }))
        (self.run / 'reader.md.verification.json').write_text(json.dumps({
            'spec_file': 'spec.json', 'report_file': 'reader.md',
        }))
        (self.run / 'spec.json').write_text(json.dumps({'sources': {}}))
        (self.run / 'evidence.json').write_text('{}')
        (self.run / 'reader.audit.md').write_text('audit')
        (self.run / 'reader.md.bundle.json').write_text('{}')
        verification = json.loads((self.run / 'reader.md.verification.json').read_text())
        verification['compiler_version'] = 'fixture'
        (self.run / 'reader.md.verification.json').write_text(json.dumps(verification))
        self.evidence = self.run / 'evidence'
        self.evidence.mkdir()
        (self.evidence / 'filing.txt').write_text('filing')
        self.other = root / 'other.txt'
        self.other.write_text('outside run')
        self.args = Namespace(
            reader=self.reader, runs_root=root, notion_url='https://app.notion.com/p/' + 'a' * 32,
            readback_reader_sha256=sha_file(self.reader), spec='spec.json', evidence_pack='evidence.json',
            semantic_review=self.review.name, remove=['evidence'], privacy_reviewed=True,
        )

    def test_finalize_verifies_writes_receipt_then_cleans_and_resumes(self):
        with patch('notion_delivery.subprocess.run') as check:
            expected = finalize(self.args)
            self.assertEqual(check.call_count, 2)
            self.assertIn('reader.md', check.call_args_list[0].args[0])
            self.assertEqual(check.call_args_list[0].kwargs['cwd'], self.run)
            self.assertEqual(finalize(self.args), expected)
            self.assertEqual(check.call_count, 2)
        self.assertEqual(read_receipt(self.receipt, self.reader), expected)
        self.assertEqual(set(self.run.iterdir()), {self.reader, self.receipt, self.run / 'audit-package.zip'})
        self.assertEqual(self.other.read_text(), 'outside run')

    def test_failed_checks_preserve_evidence(self):
        with patch('notion_delivery.subprocess.run', side_effect=subprocess.CalledProcessError(1, 'verify')):
            with self.assertRaises(subprocess.CalledProcessError):
                finalize(self.args)
        self.assertTrue(self.evidence.is_dir())
        self.assertFalse(self.receipt.exists())

    def test_sensitive_inputs_and_corrupt_archive_never_trigger_cleanup(self):
        (self.run / 'spec.json').write_text(json.dumps({'sources': {}, 'access_token': 'secret'}))
        with patch('notion_delivery.subprocess.run'):
            with self.assertRaisesRegex(ValueError, 'sensitive'):
                finalize(self.args)
            self.assertTrue(self.evidence.exists())
            self.assertFalse(self.receipt.exists())
            (self.run / 'spec.json').write_text(json.dumps({'sources': {}}))
            finalize(self.args)
            self.evidence.mkdir()
            (self.run / 'audit-package.zip').write_bytes(b'corrupt')
            with self.assertRaises(zipfile.BadZipFile):
                finalize(self.args)
            self.assertTrue(self.evidence.exists())


    def test_real_cross_directory_delivery_failure_and_retry(self):
        root = self.run.parent
        spec = make_spec()
        (self.run / 'spec.json').write_text(json.dumps(spec, ensure_ascii=False))
        now = datetime.now(timezone.utc)
        snapshot = self.run / 'raw-source.txt'
        snapshot.write_text('fixture source')
        row = {
            'path': str(snapshot), 'sha256': sha_file(snapshot),
            'observed_sha256': sha_file(snapshot),
            'retrieved_at': (now - timedelta(minutes=2)).isoformat(),
            'verified_at': (now - timedelta(minutes=1)).isoformat(),
            'expires_at': (now + timedelta(days=1)).isoformat(),
            'published_or_quoted_at': now.date().isoformat(), 'locator': 'fixture',
            'kind': 'other', 'verification_status': 'verified', 'latest_period_end': None,
        }
        pack = create(spec, {'snapshots': {key: dict(row) for key in spec['sources']},
                             'latest_period_end': spec['report']['as_of']})
        (self.run / 'evidence.json').write_text(json.dumps(pack, ensure_ascii=False))
        scripts = Path(__file__).resolve().parents[1] / 'scripts'
        subprocess.run([sys.executable, str(scripts / 'report_pipeline_v3.py'), 'build',
                        '--spec', 'spec.json', '--output', 'reader.md',
                        '--evidence-pack', 'evidence.json'], cwd=self.run, check=True, capture_output=True)
        self.review.write_text(json.dumps({'status': 'PASS', 'reader_sha256': sha_file(self.reader),
                                           'perspectives': list(PERSPECTIVES)}))
        audit = self.run / 'reader.audit.md'
        original = audit.read_text()
        audit.write_text(original + 'tampered')
        cmd = [sys.executable, str(scripts / 'notion_delivery.py'), '--reader', str(self.reader),
               '--runs-root', str(root), '--notion-url', self.args.notion_url,
               '--readback-reader-sha256', sha_file(self.reader), '--remove', 'raw-source.txt',
               '--remove', 'evidence', '--privacy-reviewed']
        failed = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        self.assertNotEqual(failed.returncode, 0)
        self.assertTrue(snapshot.exists())
        self.assertTrue((self.run / 'spec.json').exists())
        self.assertFalse(self.receipt.exists())
        audit.write_text(original)
        subprocess.run(cmd, cwd=root, check=True, capture_output=True, text=True)
        self.assertEqual(read_receipt(self.receipt, self.reader)['sha256'], sha_file(self.reader))
        self.assertEqual({p.name for p in self.run.iterdir()}, {'reader.md', 'delivery.json', 'audit-package.zip'})
        with zipfile.ZipFile(self.run / 'audit-package.zip') as archive:
            summary = json.loads(archive.read('delivery-summary.json'))
            self.assertEqual([e['result'] for e in summary['events'] if e['stage'] == 'verify'],
                             ['failed', 'passed'])
            self.assertIn(('archive', 'passed'), [(e['stage'], e['result']) for e in summary['events']])
            self.assertIn(('cleanup', 'passed'), [(e['stage'], e['result']) for e in summary['events']])
            self.assertNotIn('raw-source.txt', archive.namelist())
        self.assertEqual(self.other.read_text(), 'outside run')

    def test_hash_and_cleanup_boundary_fail_before_checks(self):
        digest = self.args.readback_reader_sha256
        self.args.readback_reader_sha256 = 'wrong'
        with self.assertRaisesRegex(ValueError, 'hash'):
            finalize(self.args)
        self.args.readback_reader_sha256 = digest
        self.args.remove.append('../other.txt')
        with self.assertRaisesRegex(ValueError, 'intermediate'):
            finalize(self.args)
        self.assertTrue(self.other.exists())
        self.assertFalse(self.receipt.exists())
