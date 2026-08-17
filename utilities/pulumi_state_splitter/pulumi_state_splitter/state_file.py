"""Manipulation of the Pulumi stack state file."""

import pathlib
import shutil
from typing import Iterable, List, Optional, Self, Sequence

import pulumi_state_splitter.fs
import pulumi_state_splitter.model
import pulumi_state_splitter.stored_state


def sorted_resources(
    resources: Iterable[pulumi_state_splitter.model.Resource],
) -> List[pulumi_state_splitter.model.Resource]:
    """Sorts resources to Pulumi's liking.

    Pulumi expects that resources in the resources list do not refer
    to resources later in the list, otherwise it complains, for example:

      ```
      error: snapshot integrity failure; refusing to use it:
       resource <urn-1> refers to unknown provider <urn-2>`
      ```
    """
    # sort by URN first
    urn2resource = dict(sorted((resource.urn, resource) for resource in resources))

    output = {}

    def dependencies_first(resource: pulumi_state_splitter.model.Resource):
        # https://github.com/pulumi/pulumi/blob/91bcce1/pkg/resource/deploy/snapshot.go#L194
        dependencies = resource.dependencies.copy()
        # https://github.com/pulumi/pulumi/blob/91bcce1/pkg/resource/deploy/snapshot.go#L156
        if resource.provider:
            provider_urn = resource.provider.rsplit("::", 1)[0]
            dependencies.append(provider_urn)
        # https://github.com/pulumi/pulumi/blob/91bcce1/pkg/resource/deploy/snapshot.go#L166
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
            self.backend_dir / ".pulumi" / "stacks" / str(self.stack_name)
        ).with_suffix(".json")

    @classmethod
    def find(
        cls,
        backend_dir: pathlib.Path,
        stacks_names: Optional[Sequence[pulumi_state_splitter.stored_state.StackName]],
    ) -> Iterable[Self]:
        """Finds file states in the Pulumi backend directory."""
        if stacks_names is None:
            glob_states = cls._glob_all().path
            stacks_names = (
                pulumi_state_splitter.stored_state.StackName(
                    project=path.parent.name,
                    stack=path.with_suffix("").name,
                )
                for path in backend_dir.glob(str(glob_states))
            )

        return cls._get_existing(backend_dir, stacks_names)

    def remove(self):
        self.path.unlink()

        # Pulumi leaves a lot of extra junk around, so cleaning it up

        for suffix in (
            ".json.attrs",
            ".json.bak",
            ".json.bak.attrs",
        ):
            self.path.with_suffix(suffix).unlink(missing_ok=True)

        for subdir in (
            "backups",
            "history",
            pathlib.Path("locks")
            / pulumi_state_splitter.stored_state.StackName.ORGANIZATION,
        ):
            d = (
                self.backend_dir
                / ".pulumi"
                / subdir
                / self.stack_name.project
                / self.stack_name.stack
            )
            if d.exists():
                shutil.rmtree(d)
                for p in d.parents:
                    if p == self.backend_dir:
                        break
                    pulumi_state_splitter.fs.rmdir_if_empty(p)

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
