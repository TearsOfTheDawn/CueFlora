import unittest
from notice_names import is_notice_name


class NoticeNameTests(unittest.TestCase):
    def test_original_and_british_spellings_and_unlicense(self):
        for name in ('LICENSE', 'LICENCE', 'licence.md', 'Licence-MIT',
                     'LICENSE.APACHE', 'UNLICENSE', 'UNLICENCE.txt',
                     'COPYING', 'NOTICE.txt', 'COPYRIGHT'):
            with self.subTest(name=name):
                self.assertTrue(is_notice_name(name))
                self.assertTrue(is_notice_name(name, strict=True))

    def test_strict_cargo_rule_does_not_expand_to_arbitrary_filename_substrings(self):
        for name in ('THIRD_PARTY_LICENSES.txt', 'third-party-licences.md',
                     'package-copyright.txt', 'LICENSES.json'):
            with self.subTest(name=name):
                self.assertTrue(is_notice_name(name))
                self.assertFalse(is_notice_name(name, strict=True))

    def test_matching_is_not_a_path_validator_or_generic_readme_fallback(self):
        for name in (None, 1, '', 'README.md', 'AUTHORS', 'Cargo.toml',
                     '../LICENSE', 'tests/LICENCE', 'tests\\LICENSE'):
            with self.subTest(name=name):
                self.assertFalse(is_notice_name(name))
                self.assertFalse(is_notice_name(name, strict=True))
