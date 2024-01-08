"""Testing `pulumi_state_splitter.cli`."""

import contextlib
import itertools
from typing import Sequence

import click.testing
import parameterized
import typeguard

with typeguard.install_import_hook("pulumi_state_splitter"):
    import pulumi_state_splitter

from . import data, util


class TestCli(util.TmpDirTest):
    """Testing `pulumi_state_splitter.cli`."""

    def _cli_run(self, args: Sequence[str], want_exit_code=0):
        runner = click.testing.CliRunner()
        result = runner.invoke(
            pulumi_state_splitter.cli,
            args,
            catch_exceptions=False,
        )
        self.assertEqual(result.exit_code, want_exit_code, result.output)

    @parameterized.parameterized.expand(
        itertools.product(
            [False, True],
            [
                "split",
                "unsplit",
            ],
            [
                [
                    "test-project-1/test-stack-1",
                    "test-project-1/test-stack-2",
                ],
                [],
            ],
        )
    )
    def test_split_unsplit(self, set_backend_dir, command, stacks):
        """Testing `pulumi_state_splitter.cli`, split and unsplit commands."""

        input_, want = (
            (data.multi_stack_unsplit(), data.multi_stack_split())
            if command == "split"
            else (data.multi_stack_split(), data.multi_stack_unsplit())
        )

        args = []
        if set_backend_dir:
            args.extend(
                [
                    "--backend-directory",
                    self._tmp_dir,
                ]
            )
        args.append(command)
        for stack in stacks:
            args.extend(["--stack", stack])
        if stacks:
            # if stacks is specified, then test-project-2 is not being processed
            if command == "split":
                want[".pulumi"] = {
                    "stacks": {
                        "test-project-2": input_[".pulumi"]["stacks"]["test-project-2"]
                    }
                }
                want.pop("test-project-2")
            else:
                want[".pulumi"]["stacks"].pop("test-project-2")
                want["test-project-2"] = input_["test-project-2"]

        input_.save(self._tmp_dir)

        with contextlib.chdir("." if set_backend_dir else self._tmp_dir):
            self._cli_run(args)

        got = util.Directory.load(self._tmp_dir)
        want.compare(got, self)

    def test_split_run(self):
        """Testing `pulumi_state_splitter.cli`, successful run command"""
        input_ = data.multi_stack_split()
        input_.save(self._tmp_dir)
        with contextlib.chdir(self._tmp_dir):
            self._cli_run(
                [
                    "run",
                    "--",
                    "cp",
                    "-r",
                    ".pulumi/stacks/test-project-2/test-stack-3.json",
                    ".pulumi/stacks/test-project-2/test-stack-4.json",
                ]
            )
        want = input_
        want["test-project-2"]["test-stack-4"] = want["test-project-2"]["test-stack-3"]
        got = util.Directory.load(self._tmp_dir)
        want.compare(got, self)

    def test_split_run_error(self):
        """Testing `pulumi_state_splitter.cli`, failing run command"""
        with contextlib.chdir(self._tmp_dir):
            self._cli_run(
                [
                    "run",
                    "--",
                    "false",
                ],
                want_exit_code=1,
            )
