import copy
import json
from pathlib import Path
import tempfile
import unittest
import tarfile
import io
from unittest.mock import patch
from audio_build import validate_inputs, obtain, extract_source, CONFIGURE, verify_signature
from build_runtime import validated_audio_build, sha256, ROOT


class AudioBuildTests(unittest.TestCase):
    def test_signature_verification_uses_public_key_only_and_requires_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); first=root/'first'; first.mkdir(); calls=[]
            fingerprint='A'*40
            def shell(toolchain,command,log):
                calls.append(command); log.write_text('[GNUPG:] VALIDSIG '+fingerprint+' 0\n' if 'gpgv ' in command else '')
            # Test signature commands and fingerprint rejection independently
            # of the Windows-only MSYS2 path adapter and external GPG process.
            with patch('audio_build.shell',side_effect=shell), \
                    patch('audio_build.posix',side_effect=lambda path: Path(path).as_posix()):
                verify_signature(root,root,first,fingerprint)
                self.assertTrue(any('gpgv ' in command for command in calls))
                self.assertTrue(any('--dearmor' in command for command in calls))
                self.assertFalse(any('--import' in command for command in calls))
                second=root/'second'; second.mkdir()
                with self.assertRaises(ValueError): verify_signature(root,root,second,'B'*40)

    def test_runtime_requires_matching_compiler_audit_inputs_and_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'install/bin').mkdir(parents=True); (root/'corresponding-source').mkdir()
            tools = {}
            for name in ('ffmpeg','ffprobe'):
                tools[name] = root/'install/bin'/(name+'.exe'); tools[name].write_bytes(name.encode())
            files = {path.name:sha256(path) for path in tools.values()}
            audit_file = root/'corresponding-source/toolchain-audit.json'
            audit_file.write_text(json.dumps({'passed':True,'files':{'compiler.exe':'a'*64}}))
            audio = {'version':'9.0.2','sourceSignatureVerified':True,'files':files,'toolchainAuditSha256':sha256(audit_file),
                'inputLockSha256':sha256(ROOT/'packaging/audio-inputs.lock.json'),
                'toolchainLockSha256':sha256(ROOT/'packaging/audio-toolchain.lock.json')}
            (root/'audio-build.json').write_text(json.dumps(audio))
            compatibility = {'passed':True,'audioBuildSha256':sha256(root/'audio-build.json'),'candidateFileHashes':files}
            (root/'audio-compatibility.json').write_text(json.dumps(compatibility))
            validated_audio_build(root,tools)
            audit_file.write_text(json.dumps({'passed':False,'files':{'compiler.exe':'a'*64}}))
            with self.assertRaisesRegex(ValueError,'audit'): validated_audio_build(root,tools)
            audit_file.write_text(json.dumps({'passed':True,'files':{'compiler.exe':'a'*64}}))
            tools['ffmpeg'].write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'payload'): validated_audio_build(root,tools)

    def test_configuration_preserves_encoder_and_excludes_gpl_network(self):
        self.assertIn('--enable-libopus',CONFIGURE)
        self.assertIn('--enable-shared',CONFIGURE)
        self.assertIn('--disable-gpl',CONFIGURE)
        self.assertIn('--disable-network',CONFIGURE)
        self.assertNotIn('--enable-nonfree',CONFIGURE)

    def test_strict_locks_offline_and_mismatched_inputs(self):
        lock = {'schema':1,'files':[{'file':'source.tar.gz','sha256':'a'*64,'url':'https://ffmpeg.org/releases/source.tar.gz'}]}
        validate_inputs(lock)
        for replacement in [{'file':'../escape'}, {'sha256':'latest'}, {'url':'http://ffmpeg.org/source'}, {'url':'https://ffmpeg.org@evil.invalid/source'}]:
            broken = copy.deepcopy(lock); broken['files'][0].update(replacement)
            with self.assertRaises(ValueError): validate_inputs(broken)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError): obtain(lock,root)
            (root/'source.tar.gz').write_bytes(b'mismatch')
            with self.assertRaises(ValueError): obtain(lock,root)

    def test_source_archive_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); archive = root/'source.tar'
            with tarfile.open(archive,'w') as package:
                entry = tarfile.TarInfo('../escape'); entry.size = 3
                package.addfile(entry,io.BytesIO(b'bad'))
            with self.assertRaises(ValueError): extract_source(archive,root/'extract')
            self.assertFalse((root/'escape').exists())
