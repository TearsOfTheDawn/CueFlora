import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from release_inputs import digest
from stage_release import plan,execute,ordinary


class StagingTests(unittest.TestCase):
    def candidate(self,root):
        bindings={name:letter*64 for name,letter in zip(
            ('sourceInventorySha256','runtimeInventorySha256','setupSha256','extensionSha256'),'abcd')}
        for directory in ('source-export','source-bundle','release-ledger','release-assets/release-ledger'):
            (root/directory).mkdir(parents=True,exist_ok=True)
        sources=root/'release-assets/CueFlora-source.zip'
        with zipfile.ZipFile(sources,'x') as archive: archive.writestr('LICENSE.md','synthetic source only')
        for name in ('CueFlora-0.1.9-Setup.exe','CueFlora-Chrome-store-upload.zip','CueFlora-third-party-sources.zip',
                'release-ledger/CONSOLIDATED_NOTICES.txt','release-ledger/dependency-ledger.json'):
            (root/'release-assets'/name).write_bytes(name.encode())
        bindings['setupSha256']=digest(root/'release-assets/CueFlora-0.1.9-Setup.exe')
        bindings['extensionSha256']=digest(root/'release-assets/CueFlora-Chrome-store-upload.zip')
        report={'engineeringPassed':True,'artifactBindings':bindings,'effectiveConfiguration':{'version':'0.1.9'}}
        (root/'readiness.json').write_text(json.dumps(report))
        (root/'source-export/source-audit.json').write_text(json.dumps({'archiveSha256':digest(sources)}))
        (root/'source-bundle/source-bundle-report.json').write_text(json.dumps(
            {'archiveSha256':digest(root/'release-assets/CueFlora-third-party-sources.zip')}))
        (root/'release-ledger/dependency-ledger.json').write_text('{}')
        assets={'schema':1,'version':'0.1.9','artifacts':bindings,'files':{
            path.relative_to(root/'release-assets').as_posix():digest(path)
            for path in (root/'release-assets').rglob('*') if path.is_file()}}
        (root/'release-assets/RELEASE_ASSETS.json').write_text(json.dumps(assets))
        configuration={'repositoryUrl':'https://github.com/fixture-owner/fixture-project'}
        return configuration

    def staging(self,root):
        configuration=self.candidate(root)
        with patch('stage_release.assess',return_value={'helperDownloadReady':True,'helperRemaining':[],
                'publicReleaseReady':False}):
            return plan(root,configuration,{},root,'e'*40)

    def test_plan_binds_six_real_assets_and_never_claims_store_or_stable_release(self):
        with tempfile.TemporaryDirectory() as directory:
            result=self.staging(Path(directory))
            self.assertEqual(len(result['assets']),6)
            self.assertEqual(result['assets'][4]['name'],'CueFlora-CONSOLIDATED-NOTICES.txt')
            for key in ('published','storeSubmitted','stableRelease'):
                self.assertFalse(result[key])

    def test_blocked_licence_gate_missing_notice_tampering_and_moving_commit_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); configuration=self.candidate(root)
            with patch('stage_release.assess',return_value={'helperDownloadReady':False,'helperRemaining':['redistributionEvidence']}):
                with self.assertRaisesRegex(ValueError,'redistributionEvidence'):
                    plan(root,configuration,{},root,'e'*40)
            with patch('stage_release.assess',return_value={'helperDownloadReady':True,'helperRemaining':[]}):
                for commit in ('main','e'*39,'../unsafe'):
                    with self.subTest(commit=commit),self.assertRaises(ValueError):
                        plan(root,configuration,{},root,commit)
                (root/'release-assets/release-ledger/CONSOLIDATED_NOTICES.txt').unlink()
                with self.assertRaises(ValueError): plan(root,configuration,{},root,'e'*40)

    def test_paths_and_hashes_cannot_escape_the_reviewed_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'notice.txt').write_bytes(b'synthetic')
            for name,checksum in (('../outside','a'*64),('C:/outside','a'*64),('a\\b','a'*64),('notice.txt','b'*64)):
                with self.subTest(name=name),self.assertRaises(ValueError): ordinary(root,name,checksum)

    def test_execution_requires_confirmation_cli_and_unchanged_assets_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            result=self.staging(Path(directory))
            with patch('stage_release.subprocess.run') as command:
                for version in (None,'0.1.8'):
                    with self.assertRaises(ValueError): execute(result,version)
                with patch('stage_release.shutil.which',return_value=None):
                    with self.assertRaisesRegex(ValueError,'CLI is unavailable'): execute(result,'0.1.9')
                command.assert_not_called()
                Path(result['assets'][0]['path']).write_bytes(b'changed')
                with patch('stage_release.shutil.which',return_value='gh'):
                    with self.assertRaisesRegex(ValueError,'changed'): execute(result,'0.1.9')
                command.assert_not_called()

    def transport(self,result,commands,*,failure=None):
        uploaded={}
        def run(command,**kwargs):
            commands.append(command)
            arguments=command[1:]
            def response(code=0,out='',error=''):
                return subprocess.CompletedProcess(command,code,out,error)
            if arguments[0]=='api':
                endpoint=arguments[1]
                if endpoint.endswith(('releases/tags/v0.1.9','git/ref/tags/v0.1.9')):
                    if failure=='conflict': return response(out='{}')
                    if failure=='auth': return response(1,error='HTTP 403: denied')
                    return response(1,error='HTTP 404: Not Found')
                if '/git/commits/' in endpoint:
                    return response(out=json.dumps({'sha':'e'*40,'tree':{'sha':'f'*40}}))
                if '/git/trees/' in endpoint:
                    data=b'synthetic source only'
                    blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
                    if failure=='source': blob='0'*40
                    return response(out=json.dumps({'truncated':False,'tree':[
                        {'type':'blob','path':'LICENSE.md','mode':'100644','sha':blob}]}))
                if endpoint.endswith('/git/refs'):
                    if failure=='tag': return response(1,error='HTTP 422: Reference already exists')
                    return response(out=json.dumps({'object':{'sha':'e'*40}}))
            if arguments[:2]==['release','create']:
                if failure=='upload': return response(1)
                for name in arguments[arguments.index('--notes-file')+2:]:
                    path=Path(name); uploaded[path.name]=path.read_bytes()
                return response(out='draft URL')
            if arguments[:2]==['release','download']:
                name=arguments[arguments.index('--pattern')+1]
                directory=Path(arguments[arguments.index('--dir')+1])
                (directory/name).write_bytes(b'changed' if failure=='download' else uploaded[name])
                return response()
            if arguments[:2]==['release','edit']: return response()
            raise AssertionError(command)
        return run

    def test_publish_checks_flat_names_remote_hashes_source_commit_and_never_promotes_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            staging=self.staging(Path(directory)); commands=[]
            with patch('stage_release.shutil.which',return_value='gh'),patch(
                    'stage_release.subprocess.run',side_effect=self.transport(staging,commands)):
                result=execute(staging,'0.1.9')
            self.assertTrue(result['published']); self.assertFalse(result['storeSubmitted'])
            upload=next(command for command in commands if command[1:3]==['release','create'])
            self.assertIn('--draft',upload)
            self.assertTrue(any(Path(value).name=='CueFlora-CONSOLIDATED-NOTICES.txt' for value in upload))
            self.assertFalse(any('#' in value for value in upload))
            self.assertEqual(sum(command[1:3]==['release','download'] for command in commands),7)
            self.assertIn('--latest=false',commands[-1])
            self.assertIn('--prerelease',commands[-1])

    def test_conflicts_auth_source_upload_download_and_tag_failures_never_publish(self):
        for failure in ('conflict','auth','source','upload','download','tag'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as directory:
                staging=self.staging(Path(directory)); commands=[]
                with patch('stage_release.shutil.which',return_value='gh'),patch(
                        'stage_release.subprocess.run',side_effect=self.transport(staging,commands,failure=failure)):
                    with self.assertRaises((ValueError,RuntimeError)): execute(staging,'0.1.9')
                self.assertFalse(any(command[1:3]==['release','edit'] for command in commands))
