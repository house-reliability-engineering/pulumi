"""Testing `pulumi_state_splitter.stored_state`."""

import unittest

import typeguard

with typeguard.install_import_hook("pulumi_state_splitter"):
    import pulumi_state_splitter.stored_state


class TestStackName(unittest.TestCase):
    """Testing `pulumi_state_splitter.stored_state.StackName`."""

    def test_from_path_no_org(self):
        """Testing `pulumi_state_splitter.stored_state.StackName.from_path`

        without the organization component.
        """
        path = "foo/bar"
        name = pulumi_state_splitter.stored_state.StackName.from_path(path)
        self.assertEqual(name.project, "foo")
        self.assertEqual(name.stack, "bar")

    def test_from_path_org(self):
        """Testing `pulumi_state_splitter.stored_state.StackName.from_path`

        with a valid organization name.
        """
        path = "organization/foo/bar"
        name = pulumi_state_splitter.stored_state.StackName.from_path(path)
        self.assertEqual(name.project, "foo")
        self.assertEqual(name.stack, "bar")

    def test_from_path_bad(self):
        """Testing `pulumi_state_splitter.stored_state.StackName.from_path`

        with an invalid organization name.
        """
        path = "acme/foo/bar"
        with self.assertRaises(ValueError):
            pulumi_state_splitter.stored_state.StackName.from_path(path)
