import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from dependency_ledger import ledger, supplemental, setup_inventory, file_evidence, require_file_attribution
from release_inputs import explain_frozen_differences, explain_library_order
import zipfile


class LedgerTests(unittest.TestCase):
    def test_engineering_attribution_gate_requires_actual_complete_rows_and_hashes(self):
        files={'notice':'a'*64}
        rows=[{'id':'notice-only','shippedFiles':[{'path':'notice','sha256':'a'*64}]}]
        report={'completeRuntimeFileInventory':files,'rows':rows,'fileCoverage':file_evidence(files,rows),
            'unassignedRuntimeFiles':[],'fileAttributionComplete':True,'redistributionApproved':False}
        self.assertTrue(require_file_attribution(report))
        self.assertFalse(report['redistributionApproved'])
        for changed in ({'rows':[]},{'fileCoverage':{}},{'unassignedRuntimeFiles':['notice']},
                {'fileAttributionComplete':False},{'completeRuntimeFileInventory':{}},
                {'rows':[{'id':'changed','shippedFiles':[{'path':'notice','sha256':'b'*64}]}]}):
            with self.subTest(changed=changed), self.assertRaises(ValueError): require_file_attribution({**report,**changed})

    def test_green_declaration_does_not_clear_an_unattributed_file(self):
        files={'unknown.dll':'a'*64}
        report={'completeRuntimeFileInventory':files,'rows':[],'fileCoverage':file_evidence(files,[]),
            'unassignedRuntimeFiles':[],'fileAttributionComplete':True}
        with self.assertRaisesRegex(ValueError,'incomplete'): require_file_attribution(report)

    def test_every_file_has_hash_and_unmatched_attribution_stays_unresolved(self):
        rows = [{'id':'example','version':'1','licence':'MIT','shippedFiles':[{'path':'known','sha256':'a'*64}]}]
        result = file_evidence({'known':'a'*64,'unknown':'b'*64},rows)
        self.assertEqual(set(result),{'known','unknown'})
        self.assertEqual(result['known']['components'][0]['licence'],'MIT')
        self.assertEqual(result['unknown']['components'],[])
        self.assertIn('review required',result['unknown']['attribution'])

    def test_shared_notice_lists_are_referenced_once_without_quadratic_growth(self):
        files = {'notice-'+str(index):'a'*64 for index in range(1000)}
        notices = [{'path':name,'sha256':checksum} for name,checksum in files.items()]
        rows = [{'id':'tool:deno','version':'synthetic','licence':'original terms','notices':notices,
            'sourceEvidence':[{'file':'source.zip','sha256':'b'*64}]}]
        result = file_evidence(files,rows)
        self.assertEqual(len(result),1000)
        self.assertTrue(all(item['components'][0]['ledgerRow']==0 for item in result.values()))
        self.assertTrue(all('notices' not in item['components'][0] and 'sourceEvidence' not in item['components'][0]
            for item in result.values()))
        self.assertLess(len(json.dumps(result)),600000)
        self.assertEqual(len(rows[0]['notices']),1000)

    def test_repeated_component_ids_remain_distinct_row_references(self):
        files = {'notice':'a'*64}
        rows = [{'id':'shared-id','version':str(index),'licence':'MIT',
            'shippedFiles':[{'path':'notice','sha256':'a'*64}],
            'notices':[{'path':'notice','sha256':'a'*64}]} for index in range(2)]
        result = file_evidence(files,rows)['notice']['components']
        self.assertEqual([item['ledgerRow'] for item in result],[0,1])
        self.assertEqual([rows[item['ledgerRow']]['version'] for item in result],['0','1'])

    def test_changed_attribution_hashes_are_not_accepted_as_provenance(self):
        for field in ('shippedFiles','notices','sourceEvidence'):
            with self.subTest(field=field):
                rows = [{'id':'synthetic',field:[{'path':'known','sha256':'b'*64}]}]
                with self.assertRaisesRegex(ValueError,'hashes disagree'):
                    file_evidence({'known':'a'*64},rows)

    def fixture(self):
        tools=[{'name':name,'versionOutput':'synthetic','sha256':'a'*64} for name in ('yt-dlp','ffmpeg','ffprobe','deno')]
        metadata={'tools':tools,'files':{'tools/'+tool['name']+'.exe':'a'*64 for tool in tools},'dependencies':[], 'buildEnvironmentDependencies':[{'name':'build-only','version':'1'}]}
        source={'sources':[],'denoSourceDependencies':[{'name':'source-only','version':'1'}],'ytDlpEmbeddedMetadata':{}}
        extra={'inputs':[],'sourceNoticeInventory':{},'candidateFfmpegHashes':{'ffmpeg.exe':'b'*64,'ffprobe.exe':'b'*64}}
        return metadata,source,extra

    def test_incomplete_and_source_only_evidence_never_grant_approval(self):
        metadata,source,extra=self.fixture(); result=ledger(metadata,[{'packages':[{'name':'shipped-js','version':'1','license':'MIT'}]}],source,extra)
        self.assertFalse(result['redistributionApproved']); self.assertFalse(result['correspondingSourceComplete'])
        self.assertTrue(any(row.get('originVerified') is False for row in result['rows']))
        self.assertEqual(result['buildOnlyPython'],metadata['buildEnvironmentDependencies'])
        self.assertIn('not proof',result['denoInventoryScope'])
        metadata['tools'][0]['sha256']='b'*64
        with self.assertRaises(ValueError): ledger(metadata,[],source,extra)

    def test_malformed_or_missing_offline_evidence_fails_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); target=root/'out'
            item={'file':'absent.zip','url':'https://github.com/official/source','sha256':'a'*64,'role':'source'}
            for lock in [None, {'schema':1,'redistributionApproved':True,'files':[item]},
                    {'schema':1,'redistributionApproved':False,'files':[{**item,'file':'../secret'}]},
                    {'schema':1,'redistributionApproved':False,'files':[item]}]:
                with self.assertRaises(ValueError): supplemental(root,target,lock)
            self.assertFalse(target.exists())

    def test_setup_inventory_includes_actual_tcl_and_tk_bytes_separately(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            executable=Path(directory)/'setup.exe'; executable.write_bytes(b'synthetic')
            entries={'tcl86t.dll':b'tcl','tk86t.dll':b'tk','bundle/runtime/tool.dll':b'runtime'}
            reader=SimpleNamespace(toc=entries,extract=lambda name:entries[name])
            with patch('PyInstaller.archive.readers.CArchiveReader',return_value=reader), patch('release_inputs.shipped_python',return_value=[]):
                result=setup_inventory(executable,Path(directory)/'Analysis', {hashlib.sha256(b'tcl').hexdigest():'tcl86t.dll'})
            self.assertEqual(len(result['archiveEntryHashes']),3)
            self.assertEqual([row['noticeFamily'] for row in result['nativeLibraries']],['Tcl','Tk'])
            self.assertTrue(result['nativeLibraries'][0]['originMatched'])
            self.assertFalse(result['nativeLibraries'][1]['originMatched'])

    def test_pe_debug_timestamp_is_normalized_but_payload_changes_are_not(self):
        def image(path,fast_load=True):
            return SimpleNamespace(FILE_HEADER=SimpleNamespace(TimeDateStamp=1,get_field_absolute_offset=lambda _:4),
                OPTIONAL_HEADER=SimpleNamespace(get_field_absolute_offset=lambda _:12),
                DIRECTORY_ENTRY_DEBUG=[SimpleNamespace(struct=SimpleNamespace(get_field_absolute_offset=lambda _:20))],parse_data_directories=lambda **_:None)
        def archive(path):
            return SimpleNamespace(toc={'payload':None},extract=lambda _:Path(path).read_bytes()[28:])
        with tempfile.TemporaryDirectory() as directory, patch('pefile.PE',side_effect=image), patch('PyInstaller.archive.readers.CArchiveReader',side_effect=archive):
            first,second=Path(directory)/'a.exe',Path(directory)/'b.exe'
            left=bytearray(32); right=bytearray(left)
            for off in (4,12,20): right[off]=1
            first.write_bytes(left); second.write_bytes(right)
            result=explain_frozen_differences(first,second)
            self.assertTrue(result['equalAfterNormalizingPeTimestampAndChecksum']); self.assertEqual(result['archiveEntryDifferences'],[])
            right[-1]=2; second.write_bytes(right)
            result=explain_frozen_differences(first,second)
            self.assertFalse(result['equalAfterNormalizingPeTimestampAndChecksum']); self.assertEqual(result['archiveEntryDifferences'],['payload'])

    def test_library_order_does_not_hide_changed_content(self):
        with tempfile.TemporaryDirectory() as directory:
            first,second=Path(directory)/'a.zip',Path(directory)/'b.zip'
            with zipfile.ZipFile(first,'w') as archive: archive.writestr('a',b'a'); archive.writestr('b',b'b')
            with zipfile.ZipFile(second,'w') as archive: archive.writestr('b',b'b'); archive.writestr('a',b'a')
            self.assertFalse(explain_library_order(first,second)['sameEntryOrder']); self.assertEqual(explain_library_order(first,second)['differentEntryContents'],[])
            with zipfile.ZipFile(second,'w') as archive: archive.writestr('b',b'changed'); archive.writestr('a',b'a')
            self.assertEqual(explain_library_order(first,second)['differentEntryContents'],['b'])
