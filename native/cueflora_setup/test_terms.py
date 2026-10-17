import contextlib
import io
import unittest
from unittest.mock import patch
from .terms import TERMS,confirmation,requires_acceptance
from .cli import main


class TermsTests(unittest.TestCase):
    def test_install_repair_need_acknowledgement_not_readonly_or_uninstall(self):
        for action in ('install','repair'):
            self.assertTrue(requires_acceptance(action,True))
            self.assertFalse(requires_acceptance(action,False))
        for action in ('self-check','detect','status','terms','rollback','uninstall'):
            self.assertFalse(requires_acceptance(action,True))

    def test_cli_refuses_unacknowledged_mutation_before_setup_access(self):
        for action in ('install','repair'):
            with patch('cueflora_setup.cli.Setup') as setup,contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit): main([action,'--apply'])
                setup.assert_not_called()

    def test_terms_can_be_read_without_installation(self):
        with patch('cueflora_setup.cli.Setup') as setup,contextlib.redirect_stdout(io.StringIO()) as output:
            main(['terms'])
            setup.return_value.install.assert_not_called()
            self.assertIn('Microsoft Distributable Code',output.getvalue())

    def test_confirmation_is_explicit_but_not_imposed_on_removal(self):
        self.assertIn('agree',confirmation('install'))
        self.assertIn('agree',confirmation('repair'))
        self.assertNotIn('agree',confirmation('uninstall'))

    def test_third_party_rights_are_not_overridden_or_misrepresented(self):
        for text in ('Microsoft Distributable Code only','no prohibition on reverse engineering',
                     'Original source archives','original Substrata attribution','not a claim of Chrome Store approval'):
            self.assertIn(text,TERMS)
