"""Test utilities."""

import contextlib
import json
import operator
import pathlib
import tempfile
import unittest
from typing import Iterable, Mapping, Sequence

import typeguard
import yaml

with typeguard.install_import_hook("pulumi_state_splitter"):
    import pulumi_state_splitter.stored_state

DATA_DIR = pathlib.Path(__file__).parent / "data"

resource_key = operator.attrgetter("urn")


def resource_map(
    seq: Sequence[pulumi_state_splitter.model.Resource],
) -> Mapping[str, pulumi_state_splitter.model.Resource]:
    """Builds a mapping from resource urn to resource."""
    return {resource.urn: resource for resource in seq}


def sorted_stored_states(
    stored_states: Iterable[pulumi_state_splitter.stored_state.StoredState],
):
    """Orders sorted states for comparison of sequences."""

    def _key(stored_state):
        return stored_state.project_name, stored_state.stack_name

    return sorted(stored_states, key=_key)


class Directory(dict):
    """Represents a filesystem directory tree."""

    @classmethod
    def load(cls, root: pathlib.Path):
        """Builds a Directory from a filesystem directory."""
        return cls(
            {
                entry.name: cls.load(entry) if entry.is_dir() else entry.read_text()
                for entry in root.iterdir()
            }
        )

    def save(self, root: pathlib.Path):
        """Writes a filesystem directory from a Directory."""
        for name, contents in self.items():
            path = root / name
            if isinstance(contents, dict):
                path.mkdir()
                Directory(contents).save(path)
            else:
                path.write_text(contents)

    def compare(
        self,
        other: "Directory",
        test_case: unittest.TestCase,
        subpath: pathlib.Path = pathlib.Path(),
    ):
        """Checks if two directories are identical."""
        test_case.assertCountEqual(
            [str(subpath / name) for name in self],
            [str(subpath / name) for name in other],
        )
        for name, contents in self.items():
            other_contents = other[name]
            if isinstance(contents, dict) and isinstance(other_contents, dict):
                Directory(contents).compare(other_contents, test_case, subpath / name)
                continue
            if name.endswith(".json"):
                contents = json.loads(contents)
                other_contents = json.loads(other_contents)
            if name.endswith(".yaml"):
                contents = yaml.load(contents, yaml.Loader)
                other_contents = yaml.load(other_contents, yaml.Loader)
            test_case.assertEqual(contents, other_contents, subpath / name)


class TmpDirTest(unittest.TestCase):
    """TestCase class providing a temporary directory."""

    def setUp(self):
        with contextlib.ExitStack() as es:
            self._tmp_dir = pathlib.Path(
                es.enter_context(tempfile.TemporaryDirectory())
            )
            self.addCleanup(es.pop_all().close)
