import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.request import Request

from approval_evidence import pending
from github_candidate import ordinary, restore
from github_publication import ReleaseRedirect, anonymous_downloads, materialize, publish_pages, read_review, run
from release_inputs import digest, ROOT


class GitHubPublicationTests(unittest.TestCase):
    def review(self):
        bindings=dict(zip(('sourceInventorySha256','runtimeInventorySha256','setupSha256','extensionSha256'),(c*64 for c in 'abcd')))
        return {'schema':1,'distribution':'github','repository':'fixture-owner/fixture-project','version':'7.8.9',
            'candidateRunId':123,'sourceCommit':'e'*40,'artifacts':bindings,'decisions':pending(bindings,'github'),'reports':{}}

    def test_review_metadata_is_exact_bounded_and_rejects_extra_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'review.json'; value=self.review(); path.write_text(json.dumps(value))
            self.assertEqual(read_review(path),value)
            for edit in ({'apiKey':'synthetic'},{'version':'latest'},{'sourceCommit':'main'},{'candidateRunId':True},
                    {'candidateRunId':0},{'repository':'fixture-owner/fixture-project/../outside'},
                    {'reports':{'../outside.json':'{}'}},{'reports':{'key.json':{}}}):
                changed={**value,**edit}; path.write_text(json.dumps(changed))
                with self.subTest(edit=edit),self.assertRaises(ValueError): read_review(path)

    def test_unclear_or_missing_review_cannot_publish_or_read_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); path=root/'review.json'; path.write_text(json.dumps(self.review()))
            with patch('github_publication.subprocess.run') as command:
                with self.assertRaises(ValueError): run(root/'candidate',path,root/'receipt.json',execute=True,confirmed_version='7.8.8')
                command.assert_not_called()
            value=self.review(); value['decisions']['gates']['publication']['status']='passed'
            with self.assertRaises(ValueError): materialize(value,root/'evidence')
            self.assertFalse((root/'receipt.json').exists())

    def test_redirects_must_remain_https_on_github_release_hosts(self):
        handler=ReleaseRedirect(); request=Request('https://github.com/fixture-owner/fixture-project/releases/download/v7.8.9/asset.zip')
        for target in ('http://github.com/asset','https://evil.invalid/asset','https://github.com.evil.invalid/asset',
                'https://secret@github.com/asset','https://github.com:8443/asset'):
            with self.subTest(target=target),self.assertRaises(ValueError): handler.redirect_request(request,None,302,'',{},target)
        redirected=handler.redirect_request(request,None,302,'',{},'https://release-assets.githubusercontent.com/asset')
        self.assertEqual(redirected.full_url,'https://release-assets.githubusercontent.com/asset')

    def test_anonymous_hash_verification_includes_checksums_and_has_no_auth_header(self):
        class Response(io.BytesIO): status=200
        data=b'synthetic bytes'; checksum=b'synthetic checksums'
        staging={'repository':'fixture-owner/fixture-project','tag':'v7.8.9',
            'assets':[{'name':'asset.zip','sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}],
            'checksumAsset':{'name':'SHA256SUMS.txt','sha256':hashlib.sha256(checksum).hexdigest(),'bytes':len(checksum)}}
        observed=[]
        def opened(request,timeout):
            observed.append(request)
            self.assertNotIn('Authorization',request.headers)
            return Response(checksum if request.full_url.endswith('SHA256SUMS.txt') else data)
        with patch('github_publication.build_opener') as opener:
            opener.return_value.open.side_effect=opened
            result=anonymous_downloads(staging)
            self.assertEqual(len(result),2)
            self.assertTrue(all(item['verified'] for item in result))
            bad=copy.deepcopy(staging); bad['assets'][0]['bytes']-=1
            with self.assertRaises(ValueError): anonymous_downloads(bad)
            bad=copy.deepcopy(staging); bad['assets'][0]['sha256']='0'*64
            with self.assertRaises(ValueError): anonymous_downloads(bad)

    def test_pages_inventory_tampering_fails_before_any_git_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); pages=root/'public-pages'; pages.mkdir()
            (pages/'public-materials.json').write_text(json.dumps({'distribution':'github','files':{'../outside':'a'*64}}))
            with patch('github_publication.subprocess.run') as command:
                with self.assertRaises(ValueError): publish_pages(root,'fixture-owner/fixture-project')
                command.assert_not_called()

    def test_candidate_restore_rejects_missing_extra_changed_and_escaping_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve(); value=self.review(); file=root/'readiness.json'
            readiness={'artifactBindings':value['artifacts'],'effectiveConfiguration':{'distribution':'github','version':'7.8.9'},
                'artifacts':{'archive':'../outside.zip'}}
            file.write_text(json.dumps(readiness))
            manifest={'schema':1,'artifacts':value['artifacts'],'files':{'readiness.json':digest(file)}}
            (root/'CANDIDATE_INVENTORY.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError): restore(root)
            file.write_text('{}')
            with self.assertRaises(ValueError): restore(root)
            for name in ('../outside','C:/outside','a\\b','./readiness.json'):
                with self.subTest(name=name),self.assertRaises(ValueError): ordinary(root,name)

    def test_read_only_build_workflow_is_explicitly_version_bounded(self):
        workflow=(ROOT/'.github/workflows/github-candidate.yml').read_text()
        self.assertIn('codex/github-build-0.1.13',workflow)
        self.assertIn("$version -ne '0.1.13'",workflow)
        self.assertIn('--public-config packaging/github-identity.json',workflow)
        for forbidden in ('contents: write','--execute','secrets.','--allow-prototype'):
            self.assertNotIn(forbidden,workflow)

    def test_publication_workflow_is_one_release_only_not_a_future_publisher(self):
        workflow=(ROOT/'.github/workflows/github-publication.yml').read_text()
        self.assertIn("branches: ['codex/github-publish-0.1.13']",workflow)
        self.assertIn("paths: ['release/github-publication.json']",workflow)
        self.assertIn("v['version']=='0.1.13'",workflow)
        self.assertIn('--confirm-version 0.1.13',workflow)
        self.assertIn('release-source/packaging/github_publication.py',workflow)
        for forbidden in ('workflow_dispatch:','codex/github-publish-*','--clobber','secrets.','--allow-prototype'):
            self.assertNotIn(forbidden,workflow)
