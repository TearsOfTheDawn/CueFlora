import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
sys.path.insert(0, str(Path(__file__).parent))
from release_inputs import validate_lock, obtain_inputs, inspect_ejs, compare_outputs, source_inventory, ROOT


def fixture():
    files = [{'file': name, 'sha256': hashlib.sha256(b'fixture').hexdigest()} for name in ['yt-dlp.exe', 'ffmpeg.exe', 'ffprobe.exe', 'deno.exe', 'fixture.whl']]
    return {'schema': 1, 'platform': 'Windows-x64', 'files': files,
            'tools': {name:name+'.exe' for name in ['yt-dlp','ffmpeg','ffprobe','deno']}, 'pythonWheels':[{'file':'fixture.whl'}],
            'pythonVersion':'3.13.15','interpreterFiles':[{'file':'python.exe','sha256':'a'*64}],
            'publicReleaseAuthorized':False,'redistributionApproved':False}


class ReleaseInputTests(unittest.TestCase):
    def test_malformed_locks_and_unsafe_inputs_fail(self):
        lock = fixture()
        validate_lock(lock)
        for value in [None, [], {}, {**lock, 'schema':2}, {**lock,'tools':{}}, {**lock,'pythonWheels':[]},
            {**lock,'interpreterFiles':[{'file':'../python.exe','sha256':'a'*64}]}, {**lock,'publicReleaseAuthorized':True}]:
            with self.assertRaises(ValueError): validate_lock(value)
        for change in [{'file':'../secret'}, {'sha256':'bad'}, {'url':'http://insecure.invalid'}, {'url':'https://files.pythonhosted.org.evil.invalid/file'}]:
            invalid = copy.deepcopy(lock); invalid['files'][0].update(change)
            with self.assertRaises(ValueError): validate_lock(invalid)
        invalid = copy.deepcopy(lock); invalid['files'].append(dict(invalid['files'][0]))
        with self.assertRaises(ValueError): validate_lock(invalid)

    def test_offline_cache_requires_every_exact_input_no_download(self):
        with tempfile.TemporaryDirectory() as directory, patch('urllib.request.urlopen') as network:
            cache = Path(directory); lock = fixture()
            with self.assertRaisesRegex(ValueError, 'Missing'): obtain_inputs(lock, cache)
            for item in lock['files']: (cache / item['file']).write_bytes(b'fixture')
            self.assertEqual(obtain_inputs(lock, cache), cache.resolve())
            (cache / 'ffmpeg.exe').write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError, 'Mismatched'): obtain_inputs(lock, cache, offline=False)
            network.assert_not_called()

    def test_missing_ejs_is_a_build_failure(self):
        with patch('PyInstaller.archive.readers.CArchiveReader', return_value=Mock(toc={})):
            with self.assertRaisesRegex(ValueError, 'missing local EJS'): inspect_ejs('fixture.exe')

    def test_source_built_preparation_needs_no_private_audio_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            cache=Path(directory); lock=fixture()
            for item in lock['files']:
                if item['file'] not in ('ffmpeg.exe','ffprobe.exe'): (cache/item['file']).write_bytes(b'fixture')
            self.assertEqual(obtain_inputs(lock,cache,source_audio=True),cache.resolve())
            with self.assertRaisesRegex(ValueError,'Missing'): obtain_inputs(lock,cache)

    def test_comparison_reports_differences_not_reproducibility_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory)/'one', Path(directory)/'two'
            first.mkdir(); second.mkdir()
            (first/'host.exe').write_bytes(b'first'); (second/'host.exe').write_bytes(b'second')
            result = compare_outputs(first, second)
            self.assertTrue(result['sameNames']); self.assertFalse(result['identical'])
            self.assertEqual(result['differentFiles'], ['host.exe'])

    def test_source_hashes_work_without_git_and_exclude_private_artifacts(self):
        result = source_inventory()
        self.assertIn('entrypoints/background.ts', result)
        self.assertIn('preview-identity.json', result)
        self.assertFalse(any(name.startswith(('artifacts/', '.git/','.packaging-venv/','node_modules/')) for name in result))

    def test_submission_workflow_has_no_publish_or_credentials(self):
        workflow = (ROOT/'.github/workflows/release.yml').read_text()
        for marker in ['secrets.', 'contents: write', 'action-gh-release', 'wxt submit', 'FIREFOX_EXTENSION_ID']:
            self.assertNotIn(marker, workflow)
        script = (ROOT/'scripts/release.sh').read_text()
        self.assertNotIn('.env.submit', script)
