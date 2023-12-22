"""Integration tests with Pulumi."""

import contextlib
import os
import pathlib
import tempfile
import unittest
import unittest.mock

import pulumi
import typeguard

with typeguard.install_import_hook("pulumi_state_splitter"):
    import pulumi_state_splitter.state_file


@unittest.mock.patch.dict(os.environ, PULUMI_CONFIG_PASSPHRASE="very secret")
class TestPulumiIntegration(unittest.TestCase):
    """Pulumi integration tests."""

    _PROJECT_NAME = "test-project"

    def setUp(self):
        with contextlib.ExitStack() as es:
            self._backend_dir = pathlib.Path(
                es.enter_context(tempfile.TemporaryDirectory())
            )
            self.addCleanup(es.pop_all().close)

        self._workspace_options = pulumi.automation.LocalWorkspaceOptions(
            project_settings=pulumi.automation.ProjectSettings(
                backend=pulumi.automation.ProjectBackend(f"file://{self._backend_dir}"),
                name=self._PROJECT_NAME,
                runtime="python",
            ),
        )

    @staticmethod
    def _pulumi_program_1():
        """A test pulumi program."""

    def test_pulumi_smoke(self):
        """A basic Pulumi smoke test."""
        stack_name = "test-stack"
        pulumi.automation.create_stack(
            program=self._pulumi_program_1,
            project_name=self._PROJECT_NAME,
            stack_name=stack_name,
            opts=self._workspace_options,
        )
        state = pulumi_state_splitter.state_file.State(
            backend_dir=self._backend_dir,
            project_name=self._PROJECT_NAME,
            stack_name=stack_name,
        )
        self.assertEqual(
            state.contents["checkpoint"]["stack"],
            f"organization/{self._PROJECT_NAME}/{stack_name}",
        )
