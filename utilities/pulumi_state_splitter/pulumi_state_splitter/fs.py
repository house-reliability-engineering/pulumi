"""Filesystem operations."""

import errno
import pathlib


def rmdir_if_empty(path: pathlib.Path):
    """Removes a directory if it is empty."""
    try:
        path.rmdir()
    except OSError as e:
        if e.errno != errno.ENOTEMPTY:
            raise
