import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from build_isolation import environment, native_inputs


class IsolationTests(unittest.TestCase):
    def test_embedded_shared_runtime_requires_exact_root_and_inventory_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); payload = root/'payload'; payload.mkdir()
            library = payload/'audio.dll'; library.write_bytes(b'approved')
            checksum = hashlib.sha256(b'approved').hexdigest()
            analysis = root/'Analysis.toc'
            analysis.write_text(repr([('audio.dll',str(library),'BINARY')]))
            lock = {'interpreterFiles':[]}
            self.assertEqual(native_inputs(analysis,lock,payload=(payload,{'audio.dll':checksum}))[0]['lockedRuntimeFile'],'audio.dll')
            library.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Unpinned'): native_inputs(analysis,lock,payload=(payload,{'audio.dll':checksum}))
            outside = root/'external.dll'; outside.write_bytes(b'approved')
            analysis.write_text(repr([('audio.dll',str(outside),'BINARY')]))
            with self.assertRaisesRegex(ValueError,'Unpinned'): native_inputs(analysis,lock,payload=(payload,{'audio.dll':checksum}))

    def test_path_and_python_injection_are_removed(self):
        original = {'SystemRoot':str(Path(tempfile.gettempdir())/'Windows'), 'PATH':'unrelated-tools',
            'PYTHONPATH':'external','PYTHONHOME':'external','LD_LIBRARY_PATH':'external','DYLD_LIBRARY_PATH':'external', 'FFMPEG_PATH':'explicit-tool'}
        result=environment(original,Path(tempfile.gettempdir())/'interpreter')
        self.assertNotIn('unrelated-tools',result['PATH'])
        self.assertEqual(len(result['PATH'].split(os.pathsep)),3)
        for name in ('PYTHONPATH','PYTHONHOME','LD_LIBRARY_PATH','DYLD_LIBRARY_PATH'): self.assertNotIn(name,result)
        self.assertEqual(result['FFMPEG_PATH'],'explicit-tool'); self.assertEqual(original['PATH'],'unrelated-tools')

    def test_only_exact_locked_native_inputs_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'native.dll'; source.write_bytes(b'locked')
            analysis=root/'Analysis.toc'; analysis.write_text(repr([('native.dll',str(source),'BINARY')]))
            lock={'interpreterFiles':[{'file':'native.dll','sha256':hashlib.sha256(b'locked').hexdigest()}]}
            self.assertEqual(native_inputs(analysis,lock)[0]['lockedInterpreterFile'],'native.dll')
            source.write_bytes(b'unpinned')
            with self.assertRaisesRegex(ValueError,'Unpinned'): native_inputs(analysis,lock)

    def test_windows_environment_names_are_case_insensitive(self):
        root=str(Path(tempfile.gettempdir())/'Windows')
        result=environment({'SYSTEMROOT':root,'Path':'unrelated','pythonpath':'external'},Path(tempfile.gettempdir()))
        self.assertNotIn('unrelated',result['PATH']); self.assertNotIn('PYTHONPATH',result)
        self.assertNotIn('Path',result)

    def test_empty_analysis_cannot_claim_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            analysis=Path(directory)/'Analysis.toc'; analysis.write_text('[]')
            with self.assertRaisesRegex(ValueError,'missing'): native_inputs(analysis,{'interpreterFiles':[]})
