"""Testing the pulumi_state_splitter.main function."""

import sys
import unittest
import unittest.mock

import pulumi_state_splitter


class TestMain(unittest.TestCase):
    """Tests the pulumi_state_splitter.main function"""

    def test_smoke(self):
        """A smoke test."""
        with unittest.mock.patch("sys.argv", [sys.argv[0], "foo", "bar"]):
            pulumi_state_splitter.main()
