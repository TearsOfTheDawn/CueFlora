import copy
import hashlib
import json
from pathlib import Path
import platform
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from approval_evidence import GITHUB_GATES, pending, verified_decisions
from assemble_preview import extension_identity, keyed_archive
from installation_guide import render
from public_materials import build
from release_assets import assemble
from release_inputs import ROOT, digest
from release_readiness import assess

sys.path.insert(0,str(ROOT/'native'))
from cueflora_setup.public_release import validate_identity
from cueflora_setup.package_policy import validate_package
from cueflora_setup.engine import Setup
from cueflora_setup.test_setup import FakeRegistration


class GitHubDistributionTests(unittest.TestCase):
    def configuration(self):
        return json.loads((ROOT/'packaging/github-identity.json').read_text())

    def bindings(self):
        return dict(zip(('sourceInventorySha256','runtimeInventorySha256','setupSha256','extensionSha256'),(c*64 for c in 'abcd')))

    def decisions(self, root):
        bindings=self.bindings(); result=pending(bindings,'github')
        for name in GITHUB_GATES:
            record={'artifacts':bindings,'gate':name,'status':'passed','reviewedBy':'Synthetic test only','reason':'Synthetic evidence, not release approval'}
            path=root/(name+'.json'); path.write_text(json.dumps(record))
            result['gates'][name]={key:record[key] for key in ('status','reviewedBy','reason')}
            result['gates'][name].update(report=path.name,reportSha256=digest(path))
        return result

    def test_real_retained_public_key_and_identity_are_exact(self):
        configuration=self.configuration()
        validate_identity(configuration,require_binding=False)
        self.assertEqual(extension_identity(configuration['chromePublicKey']),configuration['extensionIds']['chrome'])
        self.assertFalse(configuration['publicReleaseAuthorized'])
        self.assertFalse(configuration['redistributionApproved'])
        for edit in ({'chromePublicKey':None},{'repositoryUrl':None},{'distribution':'unknown'},
                {'extensionIds':{'chrome':'b'*32}}):
            with self.subTest(edit=edit),self.assertRaises(ValueError):
                validate_identity({**configuration,**edit},require_binding=False)

    def test_keyed_archive_preserves_every_byte_and_rejects_keyless_or_wrong_identity(self):
        configuration=self.configuration()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve(); extension=root/'extension'; extension.mkdir()
            manifest=extension/'manifest.json'
            manifest.write_text(json.dumps({'manifest_version':3,'version':'7.8.9','key':configuration['chromePublicKey']}))
            (extension/'index.js').write_text('const literal = "<not-html>";')
            archive=root/'extension.zip'
            keyed_archive(extension,archive,configuration['extensionIds']['chrome'])
            with zipfile.ZipFile(archive) as package:
                self.assertEqual(set(package.namelist()),{'manifest.json','index.js'})
                self.assertEqual(package.read('manifest.json'),manifest.read_bytes())
                self.assertIn('key',json.loads(package.read('manifest.json')))
            with self.assertRaises(ValueError): keyed_archive(extension,root/'wrong.zip','b'*32)
            manifest.write_text('{"manifest_version":3}')
            with self.assertRaises(ValueError): keyed_archive(extension,root/'keyless.zip',configuration['extensionIds']['chrome'])

    def test_github_guide_has_manual_install_update_and_no_store_step(self):
        text=render(self.configuration(),'7.8.9',acceptance=True)
        for marker in ('Chrome-extension','Load unpacked','same manifest key/Chrome ID','Do not remove the extension','only content you are entitled','Only Run starts AI work'):
            self.assertIn(marker,text)
        self.assertNotIn('Store',text)
        self.assertNotIn(self.configuration()['chromePublicKey'],text)
        with self.assertRaises(ValueError): render(self.configuration(),'7.8.9',acceptance=False)

    def test_channel_decisions_do_not_require_or_invent_store_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); decisions=self.decisions(root)
            result=verified_decisions(decisions,root,self.bindings(),'github')
            self.assertEqual(set(result),set(GITHUB_GATES))
            self.assertNotIn('storeApproval',result)
            self.assertNotIn('screenshots',result)
            with self.assertRaises(ValueError): verified_decisions(decisions,root,self.bindings())
            with self.assertRaises(ValueError): verified_decisions(pending(self.bindings()),root,self.bindings(),'github')
            configuration={**self.configuration(),**{k:v for k,v in self.bindings().items() if k.endswith('InventorySha256')}}
            engineering={'engineeringPassed':True,'artifactBindings':self.bindings()}
            source={'passed':True,'issues':[],'sourceInventorySha256':'a'*64}
            ledger={'correspondingSourceComplete':True,'remainingObligations':[]}
            self.assertTrue(assess(engineering,source,ledger,configuration,decisions,root)['publicReleaseReady'])
            for name in ('downloadPolicy','licences','nativeSecurity','publication'):
                broken=copy.deepcopy(decisions); broken['gates'][name]['status']='failed'
                self.assertFalse(assess(engineering,source,ledger,configuration,broken,root)['publicReleaseReady'])
            broken=copy.deepcopy(decisions); broken['gates']['downloadPolicy']['status']='reviewed'
            with self.assertRaises(ValueError): verified_decisions(broken,root,self.bindings(),'github')
            record={'artifacts':self.bindings(),'gate':'downloadPolicy','status':'reviewed','reviewedBy':'Synthetic test only',
                'reason':'Synthetic evidence, not release approval','authorizationEstablished':False,
                'publisherDirectedPublication':True,'publisherDirection':'Yes, publish anyway'}
            path=root/'downloadPolicy.json'; path.write_text(json.dumps(record))
            broken['gates']['downloadPolicy']['reportSha256']=digest(path)
            checked=assess(engineering,source,ledger,configuration,broken,root)
            self.assertTrue(checked['publicReleaseReady'])
            self.assertIs(checked['downloadPermissionEstablished'],False)
            for field,value in [('authorizationEstablished',True),('publisherDirectedPublication',False),('publisherDirection','assumed')]:
                changed={**record,field:value}; path.write_text(json.dumps(changed))
                broken['gates']['downloadPolicy']['reportSha256']=digest(path)
                with self.subTest(field=field),self.assertRaises(ValueError): verified_decisions(broken,root,self.bindings(),'github')

    @patch('cueflora_setup.engine.platform.machine',return_value='AMD64')
    def test_github_installer_lifecycle_preserves_identity_and_channel(self, simulated_windows_machine):
        # This fixture explicitly simulates Windows x64 on every CI host;
        # production architecture rejection stays enabled and unchanged.
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve(); payload=root/'payload'; payload.mkdir()
            (payload/'cueflora-host.exe').write_bytes(b'synthetic-not-executable')
            metadata={'schema':1,'prototype':True,'product':'cueflora','platform':'Windows','architecture':platform.machine(),
                'hostVersion':'7.8.9','transportPolicy':'https-remote','sourceInventorySha256':'a'*64,'publicEvidence':None,
                'files':{'cueflora-host.exe':digest(payload/'cueflora-host.exe')}}
            manifest=payload/'runtime-manifest.json'; manifest.write_text(json.dumps(metadata))
            config={**self.configuration(),'runtimeInventorySha256':digest(manifest),'sourceInventorySha256':'a'*64}
            validate_package(payload,config,metadata,['chrome'])
            setup=Setup(root/'CueFlora',root,'Windows',FakeRegistration())
            first=setup.install(payload,config,['chrome'])
            self.assertEqual(first['release']['distribution'],'github')
            metadata['hostVersion']='7.8.10'; manifest.write_text(json.dumps(metadata))
            second_config={**config,'runtimeInventorySha256':digest(manifest)}
            setup.install(payload,second_config,['chrome'])
            rolled=setup.rollback()
            self.assertEqual(rolled['release'],config)
            metadata['hostVersion']='7.8.9'; manifest.write_text(json.dumps(metadata))
            setup.repair(payload)
            setup.uninstall()
            self.assertTrue(any(path.name.startswith('removed-') for path in (root/'CueFlora').iterdir()))

    def test_github_pages_link_matching_assets_and_no_store(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            report=build(root/'pages',self.configuration(),{'setupSha256':'a'*64,'sha256':'b'*64},version='7.8.9')
            self.assertFalse(report['published'])
            download=(root/'pages/download.html').read_text()
            for name in ('CueFlora-7.8.9-Windows-x64.zip','CueFlora-Chrome-extension.zip','CueFlora-notices.zip','SHA256SUMS.txt'):
                self.assertIn('/releases/download/v7.8.9/'+name,download)
            self.assertIn('Developer mode',download)
            primary='/releases/download/v7.8.9/CueFlora-7.8.9-Windows-x64.zip'
            self.assertEqual(download.count('href="https://github.com/TearsOfTheDawn/CueFlora'+primary+'"'),1)
            self.assertEqual(download.count('class="primary-download"'),1)
            self.assertLess(download.index('class="primary-download"'),download.index('<ol>'))
            self.assertLess(download.index('</ol>'),download.index('For developers and verification'))
            steps=download.split('<ol>',1)[1].split('</ol>',1)[0]
            self.assertEqual(steps.count('<li>'),5)
            for marker in ('permanent folder','CueFlora Setup/Chrome-extension','CueFlora Setup.exe','AI services','press Run'):
                self.assertIn(marker,steps)
            for name in ('CueFlora-7.8.9-Setup.exe','CueFlora-Chrome-extension.zip','CueFlora-source.zip',
                    'CueFlora-third-party-sources.zip','CueFlora-notices.zip','CueFlora-CONSOLIDATED-NOTICES.txt',
                    'CueFlora-dependency-ledger.json','SHA256SUMS.txt'):
                self.assertIn(name,download.split('For developers and verification',1)[1])
            home=(root/'pages/index.html').read_text()
            self.assertIn(primary,home)
            self.assertEqual(home.count('class="primary-download"'),1)
            self.assertIn('five installation steps',home)
            for name,checksum in report['files'].items():
                self.assertEqual(digest(root/'pages'/name),checksum)
            self.assertNotIn('chromewebstore',download)
            self.assertNotIn('YouTube approval',download)
            for name in ('index','download','privacy','support'):
                self.assertNotIn('<script',(root/'pages'/(name+'.html')).read_text())
            build(root/'prelaunch',self.configuration(),version='7.8.9',prelaunch=True)
            self.assertNotIn('/releases/download/',(root/'prelaunch/download.html').read_text())
            self.assertNotIn('class="primary-download"',(root/'prelaunch/index.html').read_text())
            with self.assertRaises(ValueError): build(root/'bad',self.configuration(),{'setupSha256':'a'*64},version='7.8.9')

    def test_paired_pages_lead_with_setup_and_do_not_reuse_legacy_folder_steps(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);config={**self.configuration(),'extensionInventorySha256':'c'*64}
            build(root/'pages',config,{'setupSha256':'a'*64,'sha256':'b'*64},version='0.2.0')
            home=(root/'pages/index.html').read_text();download=(root/'pages/download.html').read_text()
            for text in (home,download):
                self.assertIn('class="primary-download" href="https://github.com/TearsOfTheDawn/CueFlora/releases/download/v0.2.0/CueFlora-0.2.0-Setup.exe"',text)
                self.assertNotIn('One ZIP includes',text)
            steps=download.split('<ol>',1)[1].split('</ol>',1)[0]
            self.assertIn('Setup.exe',steps);self.assertIn('stable extension folder',steps)
            self.assertNotIn('CueFlora Setup/Chrome-extension',download)
            for marker in ('one-time manual bootstrap','currently loaded CueFlora extension folder','Check for updates','ChatGPT','translation only'):
                self.assertIn(marker,download)
            self.assertIn('Complete Windows ZIP',download)

    def test_release_assets_ship_keyed_extension_full_package_and_original_notices(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve(); preparation=root/'preparation'; preparation.mkdir()
            files={'delivery/CueFlora Setup/CueFlora Setup.exe':b'synthetic installer',
                'delivery/CueFlora Setup/CueFlora-Chrome-extension.zip':b'synthetic keyed extension',
                'delivery/CueFlora-Windows-x64-Chrome.zip':b'synthetic complete package',
                'source-export/CueFlora-source.zip':b'synthetic source',
                'source-bundle/CueFlora-third-party-sources.zip':b'synthetic dependency source',
                'delivery/CueFlora Setup/notices/runtime/LICENSE':b'Original synthetic licence'}
            for name,data in files.items():
                path=preparation/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
            checksum=lambda name:hashlib.sha256(files[name]).hexdigest()
            report={'engineeringPassed':True,'artifactBindings':{'setupSha256':checksum('delivery/CueFlora Setup/CueFlora Setup.exe'),
                'extensionSha256':checksum('delivery/CueFlora Setup/CueFlora-Chrome-extension.zip')},
                'effectiveConfiguration':{'version':'7.8.9','distribution':'github'},
                'artifacts':{'archive':'CueFlora-Windows-x64-Chrome.zip','sha256':checksum('delivery/CueFlora-Windows-x64-Chrome.zip')},
                'sourceArchive':{'archiveSha256':checksum('source-export/CueFlora-source.zip')}}
            (preparation/'readiness.json').write_text(json.dumps(report))
            (preparation/'source-bundle/source-bundle-report.json').write_text(json.dumps({'archiveSha256':checksum('source-bundle/CueFlora-third-party-sources.zip')}))
            for name in ('release-gates.json','external-approvals.json','build-comparison.json'):
                (preparation/name).write_text('{}')
            (preparation/'release-ledger').mkdir(); (preparation/'release-ledger/ledger.json').write_text('{}')
            result=assemble(preparation,root/'assets')
            self.assertNotIn('CueFlora-Chrome-store-upload.zip',result['files'])
            self.assertIn('CueFlora-7.8.9-Windows-x64.zip',result['files'])
            with zipfile.ZipFile(root/'assets/CueFlora-notices.zip') as package:
                self.assertEqual(package.read('runtime/LICENSE'),b'Original synthetic licence')
