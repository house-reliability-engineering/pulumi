"""Manipulation of a split stack state file."""

import pathlib
from typing import Iterable, Optional, Self, Sequence

import pydantic
import yaml

import pulumi_state_splitter.fs
import pulumi_state_splitter.model
import pulumi_state_splitter.state_file
import pulumi_state_splitter.stored_state


class StateDir(pulumi_state_splitter.stored_state.StoredState):
    """Represents a split Pulumi stack state."""

    outputs_only: bool = False

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
                if resource.type == self.stack_name.ROOT_STACK_TYPE:
                    (self.path / "outputs.yaml").unlink()
                path.unlink()
                pulumi_state_splitter.fs.rmdir_if_empty(path.parent)
        for d in (self.path, self.path.parent):
            pulumi_state_splitter.fs.rmdir_if_empty(d)

    def exists(self) -> bool:
        """Checks if the split state exists."""
        return self._state_path.is_file()

    @classmethod
    def find(
        cls,
        backend_dir: pathlib.Path,
        stacks_names: Optional[Sequence[pulumi_state_splitter.stored_state.StackName]],
        outputs: bool = False,
    ) -> Iterable[Self]:
        """Finds directory states in the Pulumi backend directory."""
        if outputs or stacks_names is None:
            glob_all_states = cls._glob_all()._state_path
            all_stacks_names = [
                pulumi_state_splitter.stored_state.StackName(
                    project=path.parent.parent.name,
                    stack=path.parent.name,
                )
                for path in backend_dir.glob(str(glob_all_states))
            ]
            if stacks_names is None:
                stacks_names = all_stacks_names
            if outputs:
                yield from cls._get_existing(
                    backend_dir,
                    set(all_stacks_names) - set(stacks_names),
                    outputs_only=True,
                )

        yield from cls._get_existing(
            backend_dir,
            stacks_names,
            outputs_only=False,
        )

    def _load_resource(
        self, path: pathlib.Path
    ) -> pulumi_state_splitter.model.Resource:
        with path.open() as f:
            data = yaml.load(f, yaml.Loader)
        resource = pulumi_state_splitter.model.Resource.model_validate(data)
        if resource.type == self.stack_name.ROOT_STACK_TYPE:
            with (self.path / "outputs.yaml").open() as f:
                resource.outputs = yaml.load(f, yaml.Loader)
        return resource

    def load(self):
        """Loads the contents of the state directory."""
        with self._state_path.open() as f:
            data = yaml.load(f, yaml.Loader)
        self.state = pulumi_state_splitter.model.State.model_validate(data)
        if not self.state.checkpoint.latest:
            return
        if self.outputs_only:
            stack_resource_path = self.path / self.resource_subpath(
                pulumi_state_splitter.model.Resource(
                    type=self.stack_name.ROOT_STACK_TYPE,
                    urn=self.stack_name.urn,
                ),
            )
            # `pulumi stack new` does not create the stack resource
            # and we do not want to explode on such state here.
            if not stack_resource_path.exists():
                return
            self.state.checkpoint.latest.resources = [
                self._load_resource(stack_resource_path)
            ]
        else:
            self.state.checkpoint.latest.resources = (
                pulumi_state_splitter.model.Resource.find_parents(
                    self._load_resource(dirpath / filename)
                    for dirpath, _, filenames in self.path.walk()
                    if dirpath != self.path
                    for filename in filenames
                )
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
        basename = resource.name.strip("/").replace("/", "-")
        return directory / type_dir_name / f"{basename}.yaml"

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
            resource = resource.model_copy()
            resource.dependencies = sorted(resource.dependencies)
            if resource.type == "pulumi:pulumi:Stack":
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
        if not self.outputs_only:
            self.remove()


class Unsplitter(pydantic.BaseModel):
    """A context manager unsplitting and splitting the states."""

    backend_dir: pathlib.Path
    stacks_names: Optional[Sequence[pulumi_state_splitter.stored_state.StackName]] = (
        pydantic.Field(default_factory=list)
    )
    outputs: bool = False

    def __enter__(self):
        for state_dir in StateDir.find(
            self.backend_dir,
            self.stacks_names,
            self.outputs,
        ):
            state_dir.load()
            state_dir.unsplit()

    def __exit__(self, type_, value, traceback):
        for state_file in pulumi_state_splitter.state_file.StateFile.find(
            self.backend_dir,
            None if self.outputs else self.stacks_names,
        ):
            if (
                self.stacks_names is not None
                and state_file.stack_name not in self.stacks_names
            ):
                state_file.remove()
                continue
            state_file.load()
            StateDir.split_state_file(state_file)

        pulumi_dir = self.backend_dir / ".pulumi"
        if pulumi_dir.exists():
            for fn in (
                "meta.yaml",
                "meta.yaml.attrs",
            ):
                (pulumi_dir / fn).unlink(missing_ok=True)
            pulumi_dir.rmdir()
