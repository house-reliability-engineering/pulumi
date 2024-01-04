"""Command line entry point"""

import functools
import pathlib
from typing import List, Sequence

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


# pylint: disable=unused-argument
def _from_paths(
    ctx: click.Context, param: str, values: Sequence[str]
) -> List[pulumi_state_splitter.stored_state.StackName]:
    return [pulumi_state_splitter.stored_state.StackName.from_path(v) for v in values]


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
        callback=_from_paths,
        multiple=True,
    )
    @click.pass_obj
    @functools.wraps(f)
    def check_arguments(backend_dir, all_stacks, stack):
        if all_stacks and stack:
            raise ValueError("--all-stacks is mutually exclusive with --stack")
        if not (all_stacks or stack):
            raise ValueError("either --all-stacks or --stack expected")
        f(backend_dir, all_stacks, stack)

    return check_arguments


@_command
def split(
    backend_dir: pathlib.Path,
    all_stacks: bool,
    stacks: Sequence[pulumi_state_splitter.stored_state.StackName],
):
    """Splits single Pulumi stack state files into multiple files each."""
    if all_stacks:
        stacks = pulumi_state_splitter.state_file.StateFile.find(backend_dir)
    for stack_name in stacks:
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
    stacks: Sequence[pulumi_state_splitter.stored_state.StackName],
):
    """Merges split Pulumi stack states into single state file each."""
    if all_stacks:
        stacks = pulumi_state_splitter.split.StateDir.find(backend_dir)
    for stack_name in stacks:
        state_dir = pulumi_state_splitter.split.StateDir(
            backend_dir=backend_dir,
            stack_name=stack_name,
        )
        state_dir.load()
        state_dir.unsplit()
