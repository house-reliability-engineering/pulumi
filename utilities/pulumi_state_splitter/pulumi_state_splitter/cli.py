"""Command line entry point"""

import functools
import pathlib
import subprocess
import sys
from typing import Sequence

import click

import pulumi_state_splitter.stored_state


@click.group()
@click.option(
    "-d",
    "--backend-directory",
    default=".",
    type=click.Path(
        dir_okay=True,
        exists=True,
        file_okay=False,
        path_type=pathlib.Path,
        resolve_path=True,
    ),
)
@click.pass_context
def cli(ctx: click.Context, backend_directory: str):
    """pulumi_yaml_splitter command line interface."""
    ctx.obj = backend_directory


class StackNameOptionType(click.types.StringParamType):
    """click option type for Pulumi fully qualified stack names."""

    name = "project-name/stack-name"

    def convert(self, value, param, ctx):
        return pulumi_state_splitter.stored_state.StackName.from_path(value)


def _command(f):
    @cli.command()
    @click.option(
        "-a",
        "--all-stacks",
        default=False,
        is_flag=True,
    )
    @click.option(
        "-s",
        "--stack",
        multiple=True,
        type=StackNameOptionType(),
    )
    @click.pass_obj
    @functools.wraps(f)
    def check_arguments(backend_dir, all_stacks, stack, **kwargs):
        if all_stacks and stack:
            raise ValueError("--all-stacks is mutually exclusive with --stack")
        if not (all_stacks or stack):
            raise ValueError("either --all-stacks or --stack expected")
        f(
            backend_dir=backend_dir,
            all_stacks=all_stacks,
            stacks_names=stack,
            **kwargs,
        )

    return check_arguments


@_command
def split(
    backend_dir: pathlib.Path,
    all_stacks: bool,
    stacks_names: Sequence["pulumi_state_splitter.stored_state.StackName"],
):
    """Splits single Pulumi stack state files into multiple files each."""
    if all_stacks:
        stacks_names = pulumi_state_splitter.state_file.StateFile.find(backend_dir)
    for stack_name in stacks_names:
        state_file = pulumi_state_splitter.state_file.StateFile(
            backend_dir=backend_dir,
            stack_name=stack_name,
        )
        state_file.load()
        pulumi_state_splitter.split.StateDir.split_state_file(state_file)


@_command
def unsplit(
    backend_dir: pathlib.Path,
    all_stacks: bool,
    stacks_names: Sequence[pulumi_state_splitter.stored_state.StackName],
):
    """Merges split Pulumi stack states into single state file each."""
    if all_stacks:
        stacks_names = pulumi_state_splitter.split.StateDir.find(backend_dir)
    for stack_name in stacks_names:
        state_dir = pulumi_state_splitter.split.StateDir(
            backend_dir=backend_dir,
            stack_name=stack_name,
        )
        state_dir.load()
        state_dir.unsplit()


@click.argument("command", nargs=-1)
@_command
def run(
    backend_dir: pathlib.Path,
    all_stacks: bool,
    stacks_names: Sequence[pulumi_state_splitter.stored_state.StackName],
    command: str,
):
    """Runs a command with the stack states unsplit."""
    with pulumi_state_splitter.split.Unsplitter(
        all_stacks=all_stacks,
        backend_dir=backend_dir,
        stacks_names=stacks_names,
    ):
        completed = subprocess.run(command, check=False)
    sys.exit(completed.returncode)
