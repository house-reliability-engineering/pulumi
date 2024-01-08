"""Manipulation of a split stack state file."""

import os
import pathlib
from typing import Iterable, Optional, Sequence

import pydantic
import yaml

import pulumi_state_splitter.fs
import pulumi_state_splitter.model
import pulumi_state_splitter.state_file
import pulumi_state_splitter.stored_state


class StateDir(pulumi_state_splitter.stored_state.StoredState):
    """Represents a split Pulumi stack state."""

    @property
    def path(self) -> pathlib.Path:
        """Path of the state directory."""
        return self.backend_dir / str(self.stack_name)

    @property
    def _state_path(self):
        return self.path / "state.yaml"

    @classmethod
    def from_state_file(cls, state_file: pulumi_state_splitter.state_file.StateFile):
        """Converts a Pulumi stack state file to a split state."""
        return cls(**state_file.model_dump())

    def to_state_file(self) -> pulumi_state_splitter.state_file.StateFile:
        """Converts a split state to a Pulumi stack state file."""
        return pulumi_state_splitter.state_file.StateFile(**self.model_dump())

    def remove(self):
        self._state_path.unlink()
        if self.state.checkpoint.latest:
            for resource in self.state.checkpoint.latest.resources:
                path = self.path / self.resource_subpath(resource)
                if resource.type == "pulumi:pulumi:Stack":
                    (self.path / "outputs.yaml").unlink()
                path.unlink()
                pulumi_state_splitter.fs.rmdir_if_empty(path.parent)
        for d in (self.path, self.path.parent):
            pulumi_state_splitter.fs.rmdir_if_empty(d)

    @classmethod
    def find(
        cls, backend_dir: pathlib.Path
    ) -> Iterable[pulumi_state_splitter.stored_state.StackName]:
        """Finds all directory states in the Pulumi backend directory."""
        glob_states = cls._glob_all()._state_path
        for state_path in backend_dir.glob(str(glob_states)):
            stack_dir = state_path.parent
            yield pulumi_state_splitter.stored_state.StackName(
                project=stack_dir.parent.name,
                stack=stack_dir.name,
            )

    def load(self):
        """Loads the contents of the state directory."""
        with self._state_path.open() as f:
            data = yaml.load(f, yaml.Loader)
        self.state = pulumi_state_splitter.model.State.model_validate(data)
        if not self.state.checkpoint.latest:
            return
        resources = []
        for dirpath, _, filenames in os.walk(self.path):
            dirpath = pathlib.Path(dirpath)
            if dirpath == self.path:
                continue
            for filename in filenames:
                with (dirpath / filename).open() as f:
                    data = yaml.load(f, yaml.Loader)
                resource = pulumi_state_splitter.model.Resource.model_validate(data)
                if resource.type == "pulumi:pulumi:Stack":
                    with (self.path / "outputs.yaml").open() as f:
                        resource.outputs = yaml.load(f, yaml.Loader)
                resources.append(resource)
        self.state.checkpoint.latest.resources = (
            pulumi_state_splitter.model.Resource.find_parents(resources)
        )

    @classmethod
    def resource_subpath(
        cls, resource: pulumi_state_splitter.model.Resource
    ) -> pathlib.Path:
        """Determines where should a resource state be written to."""
        if (
            resource.parent_resource
            and resource.parent_resource.type != "pulumi:pulumi:Stack"
        ):
            directory = cls.resource_subpath(resource.parent_resource).with_suffix("")
        else:
            directory = pathlib.Path()
        type_dir_name = resource.type.replace(":", "-")  # für Windows
        return directory / type_dir_name / f"{resource.name}.yaml"

    def save(self):
        """Writes the contents of the state to a directory."""
        dump = self.state.model_dump(
            exclude={
                "checkpoint": {
                    "latest": {"resources"},
                },
            },
        )
        self.path.mkdir(parents=True, exist_ok=True)
        with self._state_path.open("w") as f:
            yaml.dump(dump, f)
        if not self.state.checkpoint.latest:
            return
        for resource in self.state.checkpoint.latest.resources:
            if resource.type == "pulumi:pulumi:Stack":
                resource = resource.model_copy()
                with (self.path / "outputs.yaml").open("w") as f:
                    yaml.dump(resource.outputs or {}, f)
                    resource.outputs = {}
            path = self.path / self.resource_subpath(resource)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w") as f:
                yaml.dump(
                    resource.model_dump(
                        exclude=pulumi_state_splitter.model.Resource.file_exclude
                    ),
                    f,
                )

    @classmethod
    def split_state_file(cls, state_file: pulumi_state_splitter.state_file.StateFile):
        """Splits a Pulumi stack state file into multiple files."""
        split_state = cls.from_state_file(state_file)
        split_state.save()
        state_file.remove()

    def unsplit(self):
        """Merges a split Pulumi stack state into single state file."""
        state_file = self.to_state_file()
        state_file.save()
        self.remove()


class Unsplitter(pydantic.BaseModel):
    """A context manager unsplitting and splitting the states."""

    backend_dir: pathlib.Path
    stacks_names: Optional[
        Sequence[pulumi_state_splitter.stored_state.StackName]
    ] = pydantic.Field(default_factory=list)

    def __enter__(self):
        stacks_names = self.stacks_names
        if stacks_names is None:
            stacks_names = StateDir.find(self.backend_dir)
        for stack_name in stacks_names:
            state_dir = pulumi_state_splitter.split.StateDir(
                backend_dir=self.backend_dir,
                stack_name=stack_name,
            )
            state_dir.load()
            state_dir.unsplit()

    def __exit__(self, type_, value, traceback):
        stacks_names = self.stacks_names
        if stacks_names is None:
            stacks_names = pulumi_state_splitter.state_file.StateFile.find(
                self.backend_dir
            )
        for stack_name in stacks_names:
            state_file = pulumi_state_splitter.state_file.StateFile(
                backend_dir=self.backend_dir,
                stack_name=stack_name,
            )
            state_file.load()
            StateDir.split_state_file(state_file)
