"""Lifecycle tests use disposable files, not COM/Start Menu/registry."""
import base64
import json
import unittest
from unittest.mock import patch
from . import test_setup as fixtures
from .maintenance import Maintenance, checksum


class FakeMaintenance(Maintenance):
    def build(self, launcher):
        return ('owned-shortcut:' + str(launcher)).encode('utf-8')


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        fixtures.SetupTests.setUp(self)
        self.setup.maintenance = FakeMaintenance(self.base, 'Windows')
        self.launcher = self.base / 'CueFlora Setup.exe'
        self.launcher.write_bytes(b'fake-setup-v1')

    private_config = fixtures.SetupTests.private_config

    def with_launcher(self):
        return self.setup.install(self.payload, self.private_config(), ['chrome'], launcher=self.launcher)

    def test_launcher_lifecycle_and_substrata_isolation(self):
        sentinel = self.base / 'Substrata'
        sentinel.mkdir()
        (sentinel / 'settings').write_text('preserve')
        first = self.with_launcher()
        old_link = self.setup.maintenance.path.read_bytes()
        self.launcher.write_bytes(b'fake-setup-v2')
        second = self.with_launcher()
        self.assertNotEqual(first['maintenance']['launcher'], second['maintenance']['launcher'])
        rolled = self.setup.rollback()
        self.assertEqual(rolled['maintenance'], first['maintenance'])
        self.assertEqual(self.setup.maintenance.path.read_bytes(), old_link)
        repaired = self.setup.repair(self.payload)
        self.assertEqual(repaired['maintenance']['launcher'], first['maintenance']['launcher'])
        self.setup.uninstall()
        self.assertFalse(self.setup.maintenance.path.exists())
        self.assertTrue(self.setup._launcher(first['maintenance']['launcher']).exists())
        self.assertEqual((sentinel / 'settings').read_text(), 'preserve')

    def test_foreign_shortcut_never_overwritten(self):
        path = self.setup.maintenance.path
        path.parent.mkdir(parents=True)
        path.write_bytes(b'foreign')
        with self.assertRaisesRegex(ValueError, 'not owned'):
            self.with_launcher()
        self.assertEqual(path.read_bytes(), b'foreign')
        self.assertFalse(any(self.registration.values.values()))

    def test_shortcut_failure_recovers_previous_registration(self):
        first = self.with_launcher()
        pointers = dict(self.registration.values)
        original = self.setup.maintenance.write
        def fail_once(data):
            self.setup.maintenance.write = original
            raise OSError('interrupted shortcut write')
        self.setup.maintenance.write = fail_once
        with self.assertRaises(OSError):
            self.with_launcher()
        self.assertEqual(self.setup.state(), first)
        self.assertEqual(self.registration.values, pointers)

    def test_process_interruption_after_shortcut_write(self):
        first = self.with_launcher()
        original = self.setup.maintenance.write
        def interrupt(data):
            original(data)
            raise KeyboardInterrupt('simulated process interruption')
        with patch.object(self.setup.maintenance, 'write', side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.with_launcher()
        self.assertTrue((self.setup.root / 'pending-activation.json').exists())
        self.setup.recover()
        self.assertEqual(self.setup.state(), first)
        self.assertEqual(checksum(self.setup.maintenance.path.read_bytes()), first['maintenance']['shortcutSha256'])

    def test_malformed_maintenance_journal_cannot_mutate_registration(self):
        first = self.with_launcher()
        pointers = dict(self.registration.values)
        journal = {'schema': 1, 'previousState': first, 'changes': [],
                   'maintenance': {'old': base64.b64encode(b'foreign').decode(), 'newSha256': 'a'*64}}
        (self.setup.root / 'pending-activation.json').write_text(json.dumps(journal))
        with self.assertRaises(ValueError):
            self.setup.recover()
        self.assertEqual(self.registration.values, pointers)

    def test_modified_shortcut_blocks_uninstall(self):
        first = self.with_launcher()
        self.setup.maintenance.path.write_bytes(b'not-owned-anymore')
        pointers = dict(self.registration.values)
        with self.assertRaises(ValueError):
            self.setup.uninstall()
        self.assertEqual(self.registration.values, pointers)
        self.assertEqual(self.setup.state()['current'], first['current'])

    def test_repair_can_restore_a_missing_maintenance_launcher_from_valid_package(self):
        first = self.with_launcher()
        self.setup._launcher(first['maintenance']['launcher']).unlink()
        repaired = self.setup.repair(self.payload, launcher=self.launcher)
        launcher = self.setup._launcher(repaired['maintenance']['launcher'])
        self.assertEqual(launcher.read_bytes(), self.launcher.read_bytes())
        self.assertIn(str(launcher).encode('utf-8'),self.setup.maintenance.path.read_bytes())
