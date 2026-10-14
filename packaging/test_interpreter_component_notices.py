import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from interpreter_component_notices import collect,read_downloads,validate_evidence,ROOT,COMPONENTS


class InterpreterComponentNoticeTests(unittest.TestCase):
    def test_upstream_manifest_is_parsed_never_executed(self):
        self.assertEqual(read_downloads('DOWNLOADS={"fixture":{"version":"1.0"}}'),{'fixture':{'version':'1.0'}})
        for source in ('DOWNLOADS=load_remote_code()','DOWNLOADS={x:1 for x in range(3)}','DOWNLOADS=[]','pass'):
            with self.assertRaises(ValueError): read_downloads(source)

    def fixture(self,temp):
        root=Path(temp); notices=root/'notices'; notices.mkdir()
        data=b'synthetic original licence notice'
        from release_inputs import digest
        files={}
        for key,name in COMPONENTS.values():
            (notices/name).write_bytes(data); files[name]=digest(notices/name)
        recipe=root/'windows-build.py'; recipe.write_bytes(b'synthetic recipe evidence, not executed')
        main=json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text())
        record=next(item for item in main['files'] if item['file']=='python-build-standalone-20260814-source.zip')
        core=next(item for item in main['files'] if item['file']=='CPython-3.13.15-source.zip')
        report={'sourceInput':record,'cpythonSourceInput':core,'windowsBuildRecipeSha256':digest(recipe),'redistributionApproved':False,'nativeSourceClosureComplete':False,
            'noticeFiles':files,'notices':{name:{'sha256':value} for name,value in files.items()},
            'components':{family:{'notice':name,'noticeSha256':files[name],'binarySourceIdentityProven':False} for family,(key,name) in COMPONENTS.items()}}
        (root/'interpreter-component-notices.json').write_text(json.dumps(report))
        return root,report

    def test_exact_notice_inventory_and_recipe_are_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            root,report=self.fixture(temp)
            self.assertFalse(validate_evidence(root)['nativeSourceClosureComplete'])
            (root/'notices/LICENSE.openssl-3.txt').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Changed'): validate_evidence(root)

    def test_evidence_cannot_invent_closure_approval_or_component_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root,report=self.fixture(temp)
            for field in ('redistributionApproved','nativeSourceClosureComplete'):
                (root/'interpreter-component-notices.json').write_text(json.dumps({**report,field:True}))
                with self.assertRaises(ValueError): validate_evidence(root)
            report['components']['openssl']['binarySourceIdentityProven']=True
            (root/'interpreter-component-notices.json').write_text(json.dumps(report))
            with self.assertRaises(ValueError): validate_evidence(root)

    def test_missing_family_extra_file_and_wrong_recipe_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root,report=self.fixture(temp)
            (root/'notices/extra.txt').write_bytes(b'extra')
            with self.assertRaises(ValueError): validate_evidence(root)
        with tempfile.TemporaryDirectory() as temp:
            root,report=self.fixture(temp)
            report['components'].pop('sqlite'); (root/'interpreter-component-notices.json').write_text(json.dumps(report))
            with self.assertRaises(ValueError): validate_evidence(root)
        with tempfile.TemporaryDirectory() as temp:
            root,report=self.fixture(temp); (root/'windows-build.py').write_bytes(b'changed')
            with self.assertRaises(ValueError): validate_evidence(root)
