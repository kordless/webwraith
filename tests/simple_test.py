import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'webwraith')))
from click.testing import CliRunner
import cli

class TestCLI(unittest.TestCase):
    def test_cli(self):
        runner = CliRunner()
        result = runner.invoke(cli.cli, ['world'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Hello, world! Welcome to WebWraith CLI.', result.output)

if __name__ == '__main__':
    unittest.main()