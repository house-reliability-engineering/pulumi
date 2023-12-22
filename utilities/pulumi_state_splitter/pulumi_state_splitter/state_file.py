"""Manipulation of the Pulumi stack state file."""

import functools
import json
import pathlib
from typing import Mapping, Union

import pydantic


class State(pydantic.BaseModel):
    """Represents a Pulumi stack state file."""

    backend_dir: Union[pathlib.Path, str]
    project_name: str
    stack_name: str

    @property
    def path(self) -> pathlib.Path:
        """Path of the state file."""
        return (
            pathlib.Path(self.backend_dir)
            / ".pulumi"
            / "stacks"
            / self.project_name
            / f"{self.stack_name}.json"
        )

    @functools.cached_property
    def contents(self) -> Mapping:
        """Parsed contents of the state file."""
        with self.path.open() as f:
            return json.load(f)
