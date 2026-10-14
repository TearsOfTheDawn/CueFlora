import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from release_assets import assemble
from release_inputs import digest
from promote_release import promotion,execute


class PromotionTests(unittest.TestCase):
    def test_release_assets_include_exact_pending_review_template_and_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            paths=['delivery/CueFlora Setup/CueFlora Setup.exe','delivery/CueFlora Setup/CueFlora-Chrome-store-upload.zip',
                'source-export/CueFlora-source.zip','source-bundle/CueFlora-third-party-sources.zip']
            for name in paths:
                path=root/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(name.encode())
            bindings={'sourceInventorySha256':'a'*64,'runtimeInventorySha256':'b'*64,
                'setupSha256':digest(root/paths[0]),'extensionSha256':digest(root/paths[1])}
            report={'engineeringPassed':True,'artifactBindings':bindings,'effectiveConfiguration':{'version':'0.1.4'},
                'sourceArchive':{'archiveSha256':digest(root/paths[2])}}
            (root/'readiness.json').write_text(json.dumps(report))
            (root/'source-bundle/source-bundle-report.json').write_text(json.dumps({'archiveSha256':digest(root/paths[3])}))
            for name in ('release-gates.json','external-approvals.json','build-comparison.json'):
                (root/name).write_text('{}')
            (root/'release-ledger').mkdir(); (root/'release-ledger/original-notice.txt').write_text('synthetic notice')
            template=root/'licence-assessment.template.json'
            template.write_text(json.dumps({'status':'pending','artifacts':bindings}))
            result=assemble(root,root/'assets')
            self.assertEqual((root/'assets'/template.name).read_bytes(),template.read_bytes())
            self.assertEqual(result['files'][template.name],digest(template))
            self.assertFalse(result['publicReleaseReady']); self.assertFalse(result['published'])

    def test_artifact_assembly_and_promotion_reject_unverified_engineering(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'readiness.json').write_text(json.dumps({'engineeringPassed':False}))
            with self.assertRaises(ValueError): assemble(root,root/'assets')
            self.assertFalse((root/'assets').exists())
            (root/'source-export').mkdir(); (root/'release-ledger').mkdir()
            (root/'source-export/source-audit.json').write_text(json.dumps({'passed':False,'issues':['synthetic']}))
            (root/'release-ledger/dependency-ledger.json').write_text(json.dumps({'correspondingSourceComplete':False,'remainingObligations':['synthetic']}))
            with patch('subprocess.run') as command:
                with self.assertRaises(ValueError): promotion(root,{},None,root)
                command.assert_not_called()

    def test_execution_requires_exact_confirmation_and_never_creates_or_replaces_releases(self):
        plan={'version':'0.1.4','repository':'fixture/repo','artifacts':{'setupSha256':'a'*64,'extensionSha256':'b'*64},
            'command':['gh','release','edit','v0.1.4','--repo','fixture/repo','--prerelease=false','--draft=false']}
        with patch('subprocess.run') as command:
            with self.assertRaises(ValueError): execute(plan)
            with self.assertRaises(ValueError): execute(plan,'0.1.3')
            command.assert_not_called()
        with patch('shutil.which',return_value=None),patch('subprocess.run') as command:
            with self.assertRaises(ValueError): execute(plan,'0.1.4')
            command.assert_not_called()
