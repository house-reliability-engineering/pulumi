"""Testing `pulumi_state_splitter.state_file`."""

import json
import pathlib
import unittest

import typeguard

with typeguard.install_import_hook("pulumi_state_splitter"):
    import pulumi_state_splitter.model
    import pulumi_state_splitter.state_file

from . import data, util


class TestStateFilePure(unittest.TestCase):
    """Testing `pulumi_state_splitter.state_file` without filesystem interactions."""

    def test_sorted_resources_urns_only(self):
        """Testing sorting of resources without dependencies."""
        resources = [
            pulumi_state_splitter.model.Resource(
                type="foo",
                urn="resource_4",
            ),
            pulumi_state_splitter.model.Resource(
                type="foo",
                urn="resource_2",
            ),
            pulumi_state_splitter.model.Resource(
                type="foo",
                urn="resource_0",
            ),
            pulumi_state_splitter.model.Resource(
                type="foo",
                urn="resource_3",
            ),
            pulumi_state_splitter.model.Resource(
                type="foo",
                urn="resource_1",
            ),
        ]
        got = [
            resource.urn
            for resource in pulumi_state_splitter.state_file.sorted_resources(resources)
        ]
        want = [
            "resource_0",
            "resource_1",
            "resource_2",
            "resource_3",
            "resource_4",
        ]
        self.assertEqual(got, want)

    def test_sorted_resources_with_dependencies(self):
        """Testing sorting of the resources with dependencies."""
        got = [
            resource.urn
            for resource in pulumi_state_splitter.state_file.sorted_resources(
                data.resources().values()
            )
        ]
        want = [
            "resource_0",
            "resource_1",
            "urn:pulumi:test-stack::test-project::pulumi:providers:provider::default",
            "resource_3",
            "resource_2",
            "resource_4",
        ]
        self.assertEqual(got, want)

    def test_path(self):
        """Testing the `StateFile.path` property."""
        state_file = pulumi_state_splitter.state_file.StateFile(
            backend_dir=pathlib.Path("var/tmp"),
            stack_name=data.STACK_NAME,
        )
        self.assertEqual(
            state_file.path,
            pathlib.Path("var/tmp/.pulumi/stacks/test-project/test-stack.json"),
        )


class TestStateFileFilesystem(util.TmpDirTest):
    """Testing pulumi_state_splitter.state_file with filesystem interactions"""

    def test_find(self):
        """Testing `StateFile.find`."""
        data.multi_stack_unsplit().save(self._tmp_dir)
        self.assertCountEqual(
            pulumi_state_splitter.state_file.StateFile.find(self._tmp_dir),
            data.MULTI_STACK_NAMES,
        )

    def test_load(self):
        """Testing StateFile.load."""
        state_file = pulumi_state_splitter.state_file.StateFile(
            backend_dir=self._tmp_dir,
            stack_name=data.STACK_NAME,
        )

        directory = util.Directory(
            {
                ".pulumi": {
                    "stacks": {
                        "test-project": {
                            "test-stack.json": json.dumps(
                                data.stack_state(),
                                indent=4,
                            )
                        }
                    }
                }
            }
        )
        directory.save(self._tmp_dir)

        state_file.load()

        want = data.stack_model()

        for state in state_file.state, want:
            state.checkpoint.latest.resources.sort(key=util.resource_key)

        self.assertEqual(
            state_file.state,
            want,
        )

    def test_remove(self):
        """Testing StateFile.remove."""
        state_file = pulumi_state_splitter.state_file.StateFile(
            backend_dir=self._tmp_dir,
            stack_name=data.STACK_NAME,
        )

        state_file.path.parent.mkdir(parents=True)
        state_file.path.touch()
        self.assertTrue(state_file.path.is_file())
        state_file.remove()
        self.assertFalse(state_file.path.is_file())

    def test_save(self):
        """Testing StateFile.save."""
        state_file = pulumi_state_splitter.state_file.StateFile(
            backend_dir=self._tmp_dir,
            stack_name=data.STACK_NAME,
            state=data.stack_model(),
        )

        state_file.save()

        got = util.Directory.load(self._tmp_dir)
        stack = data.stack_state()
        for r in stack["checkpoint"]["latest"]["resources"]:
            r.pop("sourcePosition", None)
        want = util.Directory(
            {
                ".pulumi": {
                    "stacks": {
                        "test-project": {
                            "test-stack.json": json.dumps(
                                stack,
                                indent=4,
                            )
                        }
                    }
                }
            }
        )
        want.compare(got, self)
