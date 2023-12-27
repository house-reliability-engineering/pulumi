"""Manipulation of the Pulumi file:// backend directory."""

import pathlib

import pulumi_state_splitter.split
import pulumi_state_splitter.state_file


def split(backend_dir: pathlib.Path):
    """Splits single Pulumi stack state files into multiple files each."""
    for state_file in pulumi_state_splitter.state_file.StateFile.load_all(backend_dir):
        split_state = pulumi_state_splitter.split.StateDir.from_state_file(state_file)
        split_state.save()
        state_file.remove()


def unsplit(backend_dir: pathlib.Path):
    """Merges split Pulumi stack states into single state file each."""
    for state_dir in pulumi_state_splitter.split.StateDir.load_all(backend_dir):
        state_file = state_dir.to_state_file()
        state_file.save()
        state_dir.remove()
