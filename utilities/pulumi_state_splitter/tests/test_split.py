"""Testing `pulumi_state_splitter.split`."""

import pathlib
import unittest

import typeguard
import yaml

from . import data, util

with typeguard.install_import_hook("pulumi_state_splitter"):
    import pulumi_state_splitter.model
    import pulumi_state_splitter.split
    import pulumi_state_splitter.state_file


_TRIVIAL_MODEL = pulumi_state_splitter.model.State(
    checkpoint=pulumi_state_splitter.model.Checkpoint(stack="test-stack"),
    version=3,
)


class TestSplitPure(unittest.TestCase):
    """Testing `pulumi_state_splitter.split` without filesystem interactions."""

    def test_path(self):
        """Testing `StateDir.path`."""
        state_dir = pulumi_state_splitter.split.StateDir(
            backend_dir=pathlib.Path("var/tmp"),
            project_name="test-project",
            stack_name="test-stack",
        )
        self.assertEqual(
            state_dir.path,
            pathlib.Path("var/tmp/test-project/test-stack"),
        )

    def test_from_state_file(self):
        """Testing `StateDir.from_state_file`."""
        state_file = pulumi_state_splitter.state_file.StateFile(
            backend_dir=pathlib.Path("var/tmp"),
            project_name="test-project",
            stack_name="test-stack",
            state=_TRIVIAL_MODEL,
        )
        state_dir = pulumi_state_splitter.split.StateDir.from_state_file(state_file)
        self.assertEqual(
            state_dir.backend_dir,
            state_file.backend_dir,
        )
        self.assertEqual(
            state_dir.project_name,
            state_file.project_name,
        )
        self.assertEqual(
            state_dir.stack_name,
            state_file.stack_name,
        )
        self.assertEqual(
            state_dir.state,
            state_file.state,
        )

    def test_to_state_file(self):
        """Testing `StateDir.to_state_file`."""
        state_dir = pulumi_state_splitter.split.StateDir(
            backend_dir=pathlib.Path("var/tmp"),
            project_name="test-project",
            stack_name="test-stack",
            state=_TRIVIAL_MODEL,
        )
        state_file = pulumi_state_splitter.split.StateDir.to_state_file(state_dir)
        self.assertEqual(
            state_file.backend_dir,
            state_dir.backend_dir,
        )
        self.assertEqual(
            state_file.project_name,
            state_dir.project_name,
        )
        self.assertEqual(
            state_file.stack_name,
            state_dir.stack_name,
        )
        self.assertEqual(
            state_file.state,
            state_dir.state,
        )

    def test_resource_subpath_basic(self):
        """Testing `StateDir.resource_subpath` with a simple case."""
        resource = pulumi_state_splitter.model.Resource(
            type="foo",
            urn="resource_1",
        )
        got = pulumi_state_splitter.split.StateDir.resource_subpath(resource)
        want = pathlib.Path("foo/resource_1.yaml")
        self.assertEqual(got, want)

    def test_resource_subpath_parents(self):
        """Testing `StateDir.resource_subpath` with parents."""
        parent = pulumi_state_splitter.model.Resource(
            type="foo",
            urn="parent",
        )
        child = pulumi_state_splitter.model.Resource(
            type="bar",
            urn="child",
            parent=parent.urn,
            parent_resource=parent,
        )
        grandchild = pulumi_state_splitter.model.Resource(
            type="baz",
            urn="grandchild",
            parent=child.urn,
            parent_resource=child,
        )
        got = pulumi_state_splitter.split.StateDir.resource_subpath(child)
        want = pathlib.Path("foo/parent/bar/child.yaml")
        self.assertEqual(got, want)

        got = pulumi_state_splitter.split.StateDir.resource_subpath(grandchild)
        want = pathlib.Path("foo/parent/bar/child/baz/grandchild.yaml")
        self.assertEqual(got, want)


class TestStateFileFilesystem(util.TmpDirTest):
    """Testing pulumi_state_splitter.split with filesystem interactions"""

    _TRIVIAL_DIRECTORY = util.Directory(
        {
            "test-project": {
                "test-stack": {
                    "state.yaml": yaml.dump(
                        {
                            "checkpoint": {"stack": "test-stack"},
                            "version": 3,
                        }
                    ),
                },
            },
        }
    )

    _STACK_STATE = data.stack_state()
    _RESOURCES = _STACK_STATE["checkpoint"]["latest"].pop("resources")
    _RESOURCES[1].pop("outputs")
    _DIRECTORY = util.Directory(
        {
            "test-project": {
                "test-stack": {
                    "pulumi:providers:command": {
                        "default_0_9_2.yaml": yaml.dump(_RESOURCES[0]),
                    },
                    "command:local:Command": {
                        "true.yaml": yaml.dump(_RESOURCES[2]),
                    },
                    "outputs.yaml": yaml.dump({"test-output": "test string"}),
                    "pulumi:pulumi:Stack": {
                        "test-project-test-stack.yaml": yaml.dump(_RESOURCES[1]),
                    },
                    "state.yaml": yaml.dump(_STACK_STATE),
                },
            },
        }
    )

    def test_load_all(self):
        """Testing `StateDir.load_all`."""
        data.multi_stack_split.save(self._tmp_dir)
        state_files = pulumi_state_splitter.split.StateDir.load_all(self._tmp_dir)
        self.assertEqual(
            util.sorted_stored_states(state_files),
            util.sorted_stored_states(
                [
                    pulumi_state_splitter.split.StateDir(
                        backend_dir=self._tmp_dir, **kwargs
                    )
                    for kwargs in data.MULTI_STACK_MODELS
                ]
            ),
        )

    def test_load_trivial(self):
        """Testing `StateDir.load` with a trivial stack."""
        state_dir = pulumi_state_splitter.split.StateDir(
            backend_dir=self._tmp_dir,
            project_name="test-project",
            stack_name="test-stack",
        )

        self._TRIVIAL_DIRECTORY.save(self._tmp_dir)

        state_dir.load()

        self.assertEqual(
            state_dir.state.model_dump(),
            _TRIVIAL_MODEL.model_dump(),
        )

    def test_load(self):
        """Testing `StateDir.load` with a more complex stack."""
        state_dir = pulumi_state_splitter.split.StateDir(
            backend_dir=self._tmp_dir,
            project_name="test-project",
            stack_name="test-stack",
        )

        self._DIRECTORY.save(self._tmp_dir)

        state_dir.load()

        want = data.stack_model()

        for state in state_dir.state, want:
            state.checkpoint.latest.resources.sort(key=util.resource_key)

        self.assertEqual(
            state_dir.state,
            want,
        )

    def test_remove(self):
        """Testing `StateDir.remove`."""
        state_dir = pulumi_state_splitter.split.StateDir(
            backend_dir=self._tmp_dir,
            project_name="test-project",
            stack_name="test-stack",
        )

        self._DIRECTORY.save(self._tmp_dir)

        state_dir.load()
        state_dir.remove()
        self.assertFalse(state_dir.path.exists())

    def test_remove_not_too_much(self):
        """Testing that `StateDir.remove` does not remove other files."""
        state_dir = pulumi_state_splitter.split.StateDir(
            backend_dir=self._tmp_dir,
            project_name="test-project",
            stack_name="test-stack",
        )

        directory = util.Directory(
            {
                "test-project": {
                    "test-stack": {
                        **self._DIRECTORY["test-project"]["test-stack"],
                        "extra.txt": "hello",
                    },
                },
            }
        )

        directory.save(self._tmp_dir)

        state_dir.load()
        state_dir.remove()
        self.assertFalse((state_dir.path / "state.yaml").exists())
        self.assertTrue((state_dir.path / "extra.txt").exists())

    def test_save_trivial(self):
        """Testing `StateDir.save` with a trivial stack."""
        state_dir = pulumi_state_splitter.split.StateDir(
            backend_dir=self._tmp_dir,
            project_name="test-project",
            stack_name="test-stack",
            state=_TRIVIAL_MODEL,
        )

        state_dir.save()

        got = util.Directory.load(self._tmp_dir)
        self._TRIVIAL_DIRECTORY.compare(got, self)

    def test_save(self):
        """Testing `StateDir.save` with a more complex stack."""
        state_dir = pulumi_state_splitter.split.StateDir(
            backend_dir=self._tmp_dir,
            project_name="test-project",
            stack_name="test-stack",
            state=data.stack_model(),
        )

        state_dir.save()

        got = util.Directory.load(self._tmp_dir)

        self._DIRECTORY.compare(got, self)
