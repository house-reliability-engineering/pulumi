"""Testing the style of the code."""

import sys
import unittest

# this is to avoid:
#   RuntimeError: dictionary changed size during iteration
# in asteroid from pylint
import pulumi_command.local.command as _
import pulumi_command.remote.command as _
import style_tests
import typeguard

with typeguard.install_import_hook("pulumi_state_splitter"):
    import pulumi_state_splitter


class TestStyle(unittest.TestCase, style_tests.TestStyle):
    """Testing the style of the package and tests code."""

    modules = [
        pulumi_state_splitter,
        sys.modules[__name__.split(".", 1)[0]],
    ]
