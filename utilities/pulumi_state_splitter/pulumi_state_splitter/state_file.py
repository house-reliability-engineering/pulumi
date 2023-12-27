"""Manipulation of the Pulumi stack state file."""

import pathlib
from typing import Iterable, List

import pulumi_state_splitter.fs
import pulumi_state_splitter.model
import pulumi_state_splitter.stored_state


def sorted_resources(
    resources: Iterable[pulumi_state_splitter.model.Resource],
) -> List[pulumi_state_splitter.model.Resource]:
    """Sorts resources to Pulumi's liking."""
    # sort by URN first
    urn2resource = dict(sorted((resource.urn, resource) for resource in resources))

    output = {}

    def dependencies_first(resource: pulumi_state_splitter.model.Resource):
        dependencies = resource.dependencies.copy()
        if resource.provider:
            provider_urn = resource.provider.rsplit("::", 1)[0]
            dependencies.append(provider_urn)
        if resource.parent:
            dependencies.append(resource.parent)
        dependencies.sort()
        for dependency in dependencies:
            dependencies_first(urn2resource[dependency])
        output.setdefault(resource.urn, resource)

    for resource in urn2resource.values():
        dependencies_first(resource)
    return list(output.values())


class StateFile(pulumi_state_splitter.stored_state.StoredState):
    """Represents a Pulumi stack state file."""

    @property
    def path(self) -> pathlib.Path:
        """Path of the state file."""
        return (
            self.backend_dir
            / ".pulumi"
            / "stacks"
            / self.project_name
            / self.stack_name
        ).with_suffix(".json")

    @classmethod
    def load_all(cls, backend_dir: pathlib.Path) -> Iterable["StateFile"]:
        """Finds all file states in the Pulumi backend directory."""
        glob_state = cls(
            backend_dir="",
            project_name="*",
            stack_name="*",
        ).path
        for stack_path in backend_dir.glob(str(glob_state)):
            state_file = cls(
                backend_dir=backend_dir,
                project_name=stack_path.parent.name,
                stack_name=stack_path.with_suffix("").name,
            )
            state_file.load()
            yield state_file

    def remove(self):
        self.path.unlink()
        for d in (
            self.path.parent,
            self.path.parent.parent,
            self.path.parent.parent.parent,
        ):
            pulumi_state_splitter.fs.rmdir_if_empty(d)

    def load(self):
        """Loads the contents of the state file."""
        self.state = pulumi_state_splitter.model.State.model_validate_json(
            self.path.read_text()
        )
        if self.state.checkpoint.latest:
            self.state.checkpoint.latest.resources = (
                pulumi_state_splitter.model.Resource.find_parents(
                    self.state.checkpoint.latest.resources
                )
            )

    def save(self):
        """Writes the contents of the state to a file."""
        state = self.state.model_copy(deep=True)
        if state.checkpoint.latest:
            state.checkpoint.latest.resources = sorted_resources(
                state.checkpoint.latest.resources
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w") as f:
            f.write(
                state.model_dump_json(
                    exclude=pulumi_state_splitter.model.State.file_exclude,
                    indent=4,
                )
            )
