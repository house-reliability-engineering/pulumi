"""Integration tests with Pulumi."""

import os
import unittest
import unittest.mock
from typing import Sequence

import pulumi
import pulumi_command
import typeguard
import yaml

from . import util

with typeguard.install_import_hook("pulumi_state_splitter"):
    import pulumi_state_splitter.state_file
    import pulumi_state_splitter.stored_state


@unittest.mock.patch.dict(os.environ, PULUMI_CONFIG_PASSPHRASE="very secret")
class TestPulumiIntegration(util.TmpDirTest):
    """Pulumi integration tests."""

    _PROJECT_NAME = "test-project"

    def setUp(self):
        super().setUp()
        self._workspace_options = pulumi.automation.LocalWorkspaceOptions(
            project_settings=pulumi.automation.ProjectSettings(
                backend=pulumi.automation.ProjectBackend(f"file://{self._tmp_dir}"),
                name=self._PROJECT_NAME,
                runtime="python",
            ),
        )

    def _cli_run(self, *args: Sequence[str]):
        super()._cli_run(
            "--backend-directory",
            self._tmp_dir,
            *args,
        )

    def _create_stack(self, name, program):
        return pulumi.automation.create_stack(
            program=program,
            project_name=self._PROJECT_NAME,
            stack_name=name,
            opts=self._workspace_options,
        )

    def _check_outputs(self, stack_name, want):
        path = self._tmp_dir / self._PROJECT_NAME / stack_name / "outputs.yaml"
        with path.open() as f:
            got = yaml.load(f, yaml.Loader)
        self.assertEqual(got, want)

    def test_pulumi_smoke(self):
        """A basic Pulumi smoke test."""
        stack = self._create_stack("test-stack", lambda: None)
        state_file = pulumi_state_splitter.state_file.StateFile(
            backend_dir=self._tmp_dir,
            stack_name=pulumi_state_splitter.stored_state.StackName(
                project=self._PROJECT_NAME,
                stack=stack.name,
            ),
        )
        state_file.load()
        self.assertEqual(
            state_file.state.checkpoint.stack,
            f"organization/{self._PROJECT_NAME}/{stack.name}",
        )

    def test_single_program(self):
        """Pulumi integration test with one Pulumi program."""

        test_string = "test string 1"

        class Counts:  # pylint: disable=too-few-public-methods
            """How many resources to create."""

            nestor = 10
            intermediate = 10
            infant = 10
            ref = 10
            deep = 10

        def pulumi_program():
            nestors = [
                pulumi_command.local.Command(
                    f"nestor-{i}",
                    create="true",
                )
                for i in range(Counts.nestor)
            ]

            intermediates = [
                pulumi_command.local.Command(
                    f"intermediate-{i}",
                    create=f"echo {test_string}",
                    opts=pulumi.ResourceOptions(parent=nestors[i // 3]),
                )
                for i in range(Counts.intermediate)
            ]

            for i in range(Counts.infant):
                pulumi_command.local.Command(
                    f"infant-{i}",
                    create="true",
                    opts=pulumi.ResourceOptions(parent=intermediates[i // 3]),
                )
            for i in range(Counts.ref):
                pulumi_command.local.Command(
                    f"ref-{i}",
                    create="cat",
                    stdin=intermediates[i // 3 + 1].stdout,
                    opts=pulumi.ResourceOptions(parent=nestors[i // 3 + 1]),
                )

            parent = intermediates[-1]
            ref = intermediates[-2]
            for i in range(Counts.deep):
                parent = pulumi_command.local.Command(
                    f"deep-child-{i}",
                    create="true",
                    opts=pulumi.ResourceOptions(parent=parent),
                )
                ref = pulumi_command.local.Command(
                    f"deep-ref-{i}",
                    create="cat",
                    stdin=ref.stdout,
                    opts=pulumi.ResourceOptions(parent=parent),
                )

            pulumi.export("test-output", ref.stdout)

        stack = self._create_stack("test-stack", pulumi_program)

        resource_count = (
            1  # the provider
            + Counts.nestor
            + Counts.intermediate
            + Counts.infant
            + Counts.ref
            + 2 * Counts.deep
        )

        def split():
            self._cli_run("split", f"{self._PROJECT_NAME}/test-stack")

        def unsplit():
            self._cli_run("unsplit", f"{self._PROJECT_NAME}/test-stack")

        split()
        unsplit()

        summary = stack.up().summary
        self.assertEqual(summary.result, "succeeded")
        self.assertEqual(
            summary.resource_changes,
            {"create": resource_count},
        )

        split()
        self._check_outputs(stack.name, {"test-output": test_string})
        unsplit()

        summary = stack.up().summary
        self.assertEqual(summary.result, "succeeded")
        self.assertEqual(
            summary.resource_changes,
            {"same": resource_count},
        )

        split()
        unsplit()

        test_string = "test string 2"
        summary = stack.up().summary
        self.assertEqual(summary.result, "succeeded")
        changed_count = Counts.intermediate + Counts.ref + Counts.deep
        self.assertEqual(
            summary.resource_changes,
            {
                "same": resource_count - changed_count,
                "update": changed_count,
            },
        )

        split()
        self._check_outputs(stack.name, {"test-output": test_string})
        unsplit()

        summary = stack.destroy().summary
        self.assertEqual(summary.result, "succeeded")
        self.assertEqual(
            summary.resource_changes,
            {"delete": resource_count},
        )

    def test_stack_reference(self):
        """Pulumi integration test with a stack reference."""

        test_string = "test string 1"

        def pulumi_program_with_output():
            pulumi.export("test-output", test_string)

        stack_with_output = self._create_stack(
            "with-output", pulumi_program_with_output
        )

        summary = stack_with_output.up().summary
        self.assertEqual(summary.result, "succeeded")
        self.assertEqual(
            summary.resource_changes,
            {"create": 1},
        )

        def split():
            self._cli_run("split", "--all")

        def unsplit():
            self._cli_run("unsplit", "--all")

        split()
        self._check_outputs(stack_with_output.name, {"test-output": test_string})
        unsplit()

        def pulumi_program_with_reference():
            reference = pulumi.StackReference(
                f"organization/{self._PROJECT_NAME}/with-output"
            )
            pulumi.export(
                "test-ref-output",
                reference.get_output("test-output"),
            )

        stack_with_reference = self._create_stack(
            "with-reference", pulumi_program_with_reference
        )

        summary = stack_with_reference.up().summary
        self.assertEqual(summary.result, "succeeded")
        self.assertEqual(
            summary.resource_changes,
            {"create": 1},
        )

        split()
        self._check_outputs(stack_with_reference.name, {"test-ref-output": test_string})
        unsplit()

        test_string = "test string 2"
        summary = stack_with_output.up().summary
        self.assertEqual(summary.result, "succeeded")
        self.assertEqual(
            summary.resource_changes,
            {
                "same": 1,
            },
        )

        split()
        self._check_outputs(stack_with_output.name, {"test-output": test_string})
        unsplit()

        summary = stack_with_reference.up().summary
        self.assertEqual(summary.result, "succeeded")
        self.assertEqual(
            summary.resource_changes,
            {
                "read": 1,
                "same": 1,
            },
        )

        split()
        self._check_outputs(stack_with_reference.name, {"test-ref-output": test_string})
