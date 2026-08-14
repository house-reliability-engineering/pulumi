"""Manipulation of the Pulumi stack state file."""

import abc
import pathlib
from typing import ClassVar, Iterable, Optional, Self, Sequence

import pydantic

import pulumi_state_splitter.model


class StackName(pydantic.BaseModel):
    """Represents a fully qualified stack name."""

    # https://github.com/pulumi/pulumi/blob/2b0c722/sdk/go/common/tokens/stack_type.go#L18
    TYPE: ClassVar[str] = "pulumi:pulumi:Stack"
    # https://github.com/pulumi/pulumi/blob/936ffe5d59ae665f8dbfa2e5eb6c2c2262a08e89/pkg/backend/filestate/store.go#L170-L172
    ORGANIZATION: ClassVar[str] = "organization"

    project: str
    stack: str

    @classmethod
    def from_path(cls, path: str) -> "StackName":
        """Converts a stack path to a `StackName`."""
        pieces = path.split("/")
        # https://github.com/pulumi/pulumi/blob/936ffe5d59ae665f8dbfa2e5eb6c2c2262a08e89/pkg/backend/filestate/store.go#L170-L172
        if len(pieces) == 3 and pieces[0] == cls.ORGANIZATION:
            pieces = pieces[1:]
        if len(pieces) != 2:
            raise ValueError(
                f"expected [organization/]project-name/stack-name, got {path}"
            )
        return cls(project=pieces[0], stack=pieces[1])

    def __str__(self) -> str:
        return f"{self.project}/{self.stack}"

    def __hash__(self):
        return hash(str(self))

    @property
    def urn(self):
        """URN of the stack resource with this name"""
        return (
            f"urn:pulumi:{self.stack}::{self.project}::"
            f"{self.TYPE}::{self.project}-{self.stack}"
        )


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

    @property
    @abc.abstractmethod
    def path(self) -> pathlib.Path:
        """Path to the state."""

    def exists(self) -> bool:
        """Checks if the state exists."""
        return self.path.exists()

    @classmethod
    def _get_existing(
        cls,
        backend_dir: pathlib.Path,
        stacks_names: Sequence[StackName],
        *args,
        **kwargs,
    ) -> Iterable[Self]:
        for stack_name in stacks_names:
            state = cls(
                backend_dir=backend_dir,
                stack_name=stack_name,
                *args,
                **kwargs,
            )
            if state.exists():
                yield state

    @classmethod
    @abc.abstractmethod
    def find(
        cls,
        backend_dir: pathlib.Path,
        stacks_names: Optional[Sequence[StackName]],
    ) -> Iterable[Self]:
        """Finds states in the Pulumi backend directory."""

    @abc.abstractmethod
    def remove(self):
        """Removes the state from the Pulumi backend directory."""

    @abc.abstractmethod
    def load(self):
        """Loads the state from the Pulumi backend directory."""

    @abc.abstractmethod
    def save(self):
        """Writes the state to the Pulumi backend directory."""
