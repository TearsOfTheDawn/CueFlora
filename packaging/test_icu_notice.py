import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from icu_notice import ROOT, blob_sha, validate, local_evidence, verify_data, collect, notice_origin
from licence_attribution import augment
from cargo_notice_evidence import REGISTRY


class IcuNoticeTests(unittest.TestCase):
    def setUp(self):
        self.pin = json.loads((ROOT/'packaging/v8-notice-inputs.lock.json').read_text())['icu']

    def deps(self, commit=None):
        return ("'third_party/icu': Var('chromium_url') + '/chromium/deps/icu.git' + '@' + '" + (commit or self.pin['commit']) + "',").encode()

    def test_actual_original_notice_and_git_tree_match_locked_bytes(self):
        notice = local_evidence(self.pin)
        self.assertEqual(len(notice), 26487)
        self.assertEqual(blob_sha(notice), self.pin['noticeGitBlobSha1'])

    def test_icu_notice_origin_is_accepted_by_the_production_runtime_ledger(self):
        name = 'licenses/deno-v8-source-notices/' + self.pin['noticeFile']
        metadata = {'files':{name:self.pin['noticeSha256']},'hostVersion':'synthetic',
                    'v8NoticeEvidence':{'notices':{self.pin['noticeFile']:notice_origin(self.pin)}}}
        report = {'rows':[]}
        with tempfile.TemporaryDirectory() as temp:
            augment(metadata, report, Path(temp))
        row = next(item for item in report['rows'] if item['id'] == 'v8-notice:LICENSE')
        self.assertEqual(row['shippedFiles'], [{'path':name,'sha256':self.pin['noticeSha256']}])
        self.assertTrue(row['originVerified'])

    def test_unpinned_paths_hashes_and_nonprimary_origin_are_rejected(self):
        for change in ({'noticeFile':'../LICENSE'}, {'treeFile':'x/y'}, {'dataSha256':'bad'},
                       {'sourceUrl':'https://example.invalid/LICENSE'}, {'commit':'latest'}, {'extra':'unlisted'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate({**self.pin, **change})
        with self.assertRaises(ValueError):
            validate(None)

    def test_data_identity_and_exact_v8_dependency_are_both_required(self):
        data = b'synthetic ICU data'
        pin = {**self.pin, 'dataSha256':hashlib.sha256(data).hexdigest(), 'dataGitBlobSha1':blob_sha(data)}
        verify_data(pin, data, self.deps())
        for candidate, deps in ((b'other', self.deps()), (data, self.deps('b'*40)), (data, b'no dependency')):
            with self.assertRaisesRegex(ValueError, 'lineage'):
                verify_data(pin, candidate, deps)

    def test_changed_or_missing_local_evidence_is_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); folder = root/'packaging/source-metadata'; folder.mkdir(parents=True)
            for field in ('noticeFile','treeFile'):
                (folder/self.pin[field]).write_bytes((ROOT/'packaging/source-metadata'/self.pin[field]).read_bytes())
            local_evidence(self.pin, root)
            (folder/self.pin['noticeFile']).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'original ICU'): local_evidence(self.pin, root)

    def test_missing_offline_crate_never_downloads_or_infers(self):
        cargo = {'package':[{'name':'deno_core_icudata', 'version':self.pin['crateVersion'],
                            'source':REGISTRY, 'checksum':self.pin['crateSha256']}]}
        with tempfile.TemporaryDirectory() as temp, patch('cargo_notice_evidence.urlopen') as network:
            with self.assertRaisesRegex(ValueError, 'Missing exact Cargo'):
                collect(self.pin, cargo, Path(temp), self.deps())
            network.assert_not_called()

    def test_actual_collection_checks_the_crate_checksum_and_data_member(self):
        data = b'synthetic ICU data'
        content = io.BytesIO()
        name = 'deno_core_icudata-0.77.0/src/icudtl.dat'
        with tarfile.open(fileobj=content, mode='w:gz') as archive:
            entry = tarfile.TarInfo(name); entry.size = len(data); archive.addfile(entry, io.BytesIO(data))
        raw = content.getvalue()
        pin = {**self.pin, 'crateSha256':hashlib.sha256(raw).hexdigest(),
               'dataSha256':hashlib.sha256(data).hexdigest(), 'dataGitBlobSha1':blob_sha(data)}
        cargo = {'package':[{'name':'deno_core_icudata','version':'0.77.0','source':REGISTRY,'checksum':pin['crateSha256']}]}
        with tempfile.TemporaryDirectory() as temp, patch('icu_notice.local_evidence', return_value=b'original fixture notice'):
            cache=Path(temp); (cache/'cargo-registry-cache').mkdir()
            path=cache/'cargo-registry-cache/deno_core_icudata-0.77.0.crate'; path.write_bytes(raw)
            notice, actual, evidence = collect(pin, cargo, cache, self.deps())
            self.assertEqual(actual, path); self.assertEqual(notice, b'original fixture notice')
            self.assertTrue(evidence['dataLineageVerified'])
            path.write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'Changed Cargo'): collect(pin, cargo, cache, self.deps())
