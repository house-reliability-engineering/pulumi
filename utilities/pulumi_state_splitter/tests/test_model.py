"""Testing `pulumi_state_splitter.model`."""

import unittest

import typeguard

with typeguard.install_import_hook("pulumi_state_splitter"):
    import pulumi_state_splitter.model

from . import data, util


class TestModel(unittest.TestCase):
    """Testing `pulumi_state_splitter.model`."""

    _RESOURCES = data.resources()

    def test_name(self):
        """Testing the `Resource.name` property."""
        resource = pulumi_state_splitter.model.Resource(
            type="foo",
            urn="urn:pulumi:stack::project::package:module:Class::resource-name",
        )
        self.assertEqual(
            resource.name,
            "resource-name",
        )

    def test_find_parents(self):
        """Testing `pulumi_state_splitter.model.Resource.find_parents`."""
        out = util.resource_map(
            pulumi_state_splitter.model.Resource.find_parents(self._RESOURCES.values())
        )

        self.assertIsNone(self._RESOURCES["resource_4"].parent_resource)
        self.assertIs(out["resource_4"].parent_resource, out["resource_1"])
        self.assertIsNone(out["resource_1"].parent_resource)

    def test_serialization_skip_attributes(self):
        """Testing that a particular attributes are skipped when falsy."""
        dump_0 = self._RESOURCES["resource_0"].model_dump()
        self.assertNotIn("dependencies", dump_0)
        self.assertIn("outputs", dump_0)
        self.assertNotIn("parent", dump_0)

        dump_4 = self._RESOURCES["resource_4"].model_dump()
        self.assertIn("dependencies", dump_4)
        self.assertNotIn("outputs", dump_4)
        self.assertIn("parent", dump_4)
