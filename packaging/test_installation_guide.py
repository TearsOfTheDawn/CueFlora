import unittest
from installation_guide import render


class InstallationGuideTests(unittest.TestCase):
    def test_guide_matches_packaged_extension_without_leaking_other_configuration(self):
        # Synthetic identity/configuration values remain confined to this test.
        configuration = {'extensionIds': {'chrome': 'a' * 32}, 'apiKey': 'synthetic-do-not-render',
            'chromePublicKey': 'synthetic-public-key-do-not-render', 'owner': 'synthetic-owner-do-not-render'}
        for mode, acceptance, expected_folder in [('private', False, 'Chrome-preview'),
                ('public', True, 'Chrome-acceptance'), ('public', False, None)]:
            with self.subTest(mode=mode, acceptance=acceptance):
                text = render({**configuration, 'mode': mode}, '7.8.9', acceptance)
                self.assertIn('CueFlora 7.8.9', text)
                self.assertIn('`' + 'a' * 32 + '`', text)
                self.assertIn('unreleased package', text)
                self.assertIn('Do not change or uninstall Substrata', text)
                self.assertIn('do not run both CueFlora identities together', text)
                self.assertIn('only Run starts AI work', text)
                self.assertIn('Store-submission ZIP is not an unpacked preview', text)
                for field in ('apiKey', 'chromePublicKey', 'owner'):
                    self.assertNotIn(configuration[field], text)
                if expected_folder:
                    self.assertIn('`' + expected_folder + '` folder', text)
                    self.assertIn('confirm Install', text)
                    other = 'Chrome-acceptance' if expected_folder == 'Chrome-preview' else 'Chrome-preview'
                    self.assertNotIn(other, text)
                else:
                    self.assertIn('No unpacked acceptance extension is included', text)
                    self.assertNotIn('Load unpacked', text)
                    self.assertNotIn('confirm Install', text)

    def test_missing_malformed_or_mismatched_profile_inputs_are_not_guessed(self):
        configuration = {'mode': 'public', 'extensionIds': {'chrome': 'a' * 32}}
        for release, version, acceptance in [(None, '1.2.3', False), ({}, '1.2.3', False),
                ({**configuration, 'mode': 'prototype'}, '1.2.3', False),
                ({**configuration, 'extensionIds': None}, '1.2.3', False),
                ({**configuration, 'extensionIds': {'chrome': 'invalid'}}, '1.2.3', False),
                (configuration, None, False), (configuration, '1.2.3\nother', False),
                (configuration, '1.2.3', 'yes'),
                ({**configuration, 'mode': 'private'}, '1.2.3', True)]:
            with self.subTest(release=release, version=version, acceptance=acceptance), self.assertRaises(ValueError):
                render(release, version, acceptance)
