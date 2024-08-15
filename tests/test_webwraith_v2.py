import unittest
from click.testing import CliRunner
from webwraith_v2 import cli

class TestWebWraithCLI(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_setup_valid_key(self):
        result = self.runner.invoke(cli, ['setup', '--substrate-key', 'valid-key'])
        self.assertIn('Substrate key is valid and configured.', result.output)
        self.assertEqual(result.exit_code, 0)

    def test_setup_invalid_key(self):
        result = self.runner.invoke(cli, ['setup', '--substrate-key', 'invalid-key'])
        self.assertIn('Invalid substrate key!', result.output)
        self.assertEqual(result.exit_code, 0)

if __name__ == '__main__':
    unittest.main()