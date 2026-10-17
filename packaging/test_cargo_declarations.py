import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from cargo_declarations import declaration,collect,validate,standard_terms


class CargoDeclarationTests(unittest.TestCase):
    def fixture(self,root,licence='MIT',authors=None,header=b'// Copyright 2001 Actual Upstream Holder\nfn example() {}\n'):
        filename='example-1.2.3.crate'; path=root/filename
        metadata='[package]\nname="example"\nversion="1.2.3"\nlicense='+json.dumps(licence)+'\n'
        if authors is not None: metadata+='authors='+json.dumps(authors)+'\n'
        with tarfile.open(path,'w:gz') as archive:
            for name,raw in {'Cargo.toml':metadata.encode(),'src/lib.rs':header}.items():
                member=tarfile.TarInfo('example-1.2.3/'+name); member.size=len(raw)
                archive.addfile(member,io.BytesIO(raw))
        return {'name':'example','version':'1.2.3','crateFile':filename,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'declaredLicence':licence,'declaredLicenceFile':None,'packageRootNoticeAvailable':False},path

    def test_original_author_metadata_and_actual_copyright_are_not_conflated(self):
        with tempfile.TemporaryDirectory() as temp:
            item,path=self.fixture(Path(temp),authors=['Metadata Author'])
            record=declaration(item,path)
            self.assertEqual(record['upstreamAuthorsMetadata'],['Metadata Author'])
            self.assertEqual(record['suppliedCopyrightStatements'][0]['verbatimLine'],'// Copyright 2001 Actual Upstream Holder')
            self.assertNotIn('Metadata Author',record['suppliedCopyrightStatements'][0]['verbatimLine'])
            self.assertIn('not relabelled',record['interpretation'])

    def test_absent_copyright_does_not_get_an_invented_holder_or_year(self):
        with tempfile.TemporaryDirectory() as temp:
            item,path=self.fixture(Path(temp),authors=['Known Author'],header=b'fn example() {}\n')
            record=declaration(item,path)
            self.assertEqual(record['suppliedCopyrightStatements'],[])
            self.assertEqual(record['upstreamAuthorsMetadata'],['Known Author'])

    def test_archive_and_manifest_mismatches_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            item,path=self.fixture(Path(temp))
            with self.assertRaisesRegex(ValueError,'declaration differs'): declaration({**item,'declaredLicence':'Apache-2.0'},path)
            with self.assertRaisesRegex(ValueError,'archive changed'): declaration({**item,'sha256':'0'*64},path)

    def test_complete_source_is_supplied_including_mpl_not_just_download_url(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); item,path=self.fixture(root,licence='MPL-2.0')
            output=root/'output'; output.mkdir()
            notices,sources=collect([item],root,output)
            self.assertEqual((output/'sources/registry'/path.name).read_bytes(),path.read_bytes())
            report={'packages':[item],'declarationNotices':notices,'sourceArchives':sources}
            result=validate(report,output)
            self.assertEqual(result['fullRegistrySourcesSupplied'],1)
            self.assertNotIn('redistributionApproved',result)

    def test_missing_changed_source_or_attribution_fails_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); item,path=self.fixture(root); output=root/'output'; output.mkdir()
            notices,sources=collect([item],root,output)
            report={'packages':[item],'declarationNotices':notices,'sourceArchives':sources}
            with self.assertRaisesRegex(ValueError,'archives missing'): validate({**report,'sourceArchives':{}},output)
            notice=output/'declarations/example-1.2.3.json'; original=notice.read_bytes(); notice.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError,'attribution record'): validate(report,output)
            notice.write_bytes(original)
            (output/'sources/registry'/path.name).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'corresponding Cargo source'): validate(report,output)

    def test_standard_reference_files_are_actual_pinned_bytes_not_package_notices(self):
        result=standard_terms()
        self.assertEqual(set(result),{'MIT','Apache-2.0','CC0-1.0'})
        for record,path in result.values():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),record['sha256'])
            self.assertIn('/v3.20/',record['url'])
