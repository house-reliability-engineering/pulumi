"""Manipulation of the Pulumi stack state file."""

import abc
import pathlib
from typing import Iterable, Optional

import pydantic

import pulumi_state_splitter.model


class StoredState(pydantic.BaseModel, abc.ABC):
    """Represents a stored Pulumi stack state."""

    backend_dir: pathlib.Path
    project_name: str
    stack_name: str
    state: Optional[pulumi_state_splitter.model.State] = None

    @classmethod
    @abc.abstractmethod
    def load_all(cls, backend_dir: pathlib.Path) -> Iterable["StoredState"]:
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
