"""Manipulation of the Pulumi stack state file."""

import abc
import pathlib
from typing import Iterable, Optional

import pydantic

import pulumi_state_splitter.model


class StackName(pydantic.BaseModel):
    """Represents a fully qualified stack name."""

    project: str
    stack: str

    @classmethod
    def from_path(cls, path: str) -> "StackName":
        """Converts a stack path to a `StackName`."""
        pieces = path.split("/")
        # https://github.com/pulumi/pulumi/blob/936ffe5d59ae665f8dbfa2e5eb6c2c2262a08e89/pkg/backend/filestate/store.go#L170-L172
        if len(pieces) == 3 and pieces[0] == "organization":
            pieces = pieces[1:]
        if len(pieces) != 2:
            raise ValueError(
                f"expected [organization/]project-name/stack-name, got {path}"
            )
        return cls(project=pieces[0], stack=pieces[1])

    def __str__(self) -> str:
        return f"{self.project}/{self.stack}"


class StoredState(pydantic.BaseModel, abc.ABC):
    """Represents a stored Pulumi stack state."""

    backend_dir: pathlib.Path
    stack_name: StackName
    state: Optional[pulumi_state_splitter.model.State] = None

    @classmethod
    def _glob_all(cls):
        return cls(
            backend_dir="",
            stack_name=StackName(
                project="*",
                stack="*",
            ),
        )

    @classmethod
    @abc.abstractmethod
    def find(cls, backend_dir: pathlib.Path) -> Iterable[StackName]:
        """Finds all states in the Pulumi backend directory."""

    @abc.abstractmethod
    def remove(self):
        """Removes the state from the Pulumi backend directory."""

    @abc.abstractmethod
    def load(self):
        """Loads the state from the Pulumi backend directory."""

    @abc.abstractmethod
    def save(self):
        """Writes the state to the Pulumi backend directory."""
