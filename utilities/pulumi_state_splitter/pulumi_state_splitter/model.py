"""Model representing a Pulumi stack state."""

from typing import Any, ClassVar, Iterable, List, Literal, Mapping, Optional, Sequence

import pydantic


# workaround for https://github.com/pydantic/pydantic/discussions/5461
def _skip_some_falsy_values(
    model: pydantic.BaseModel, handler: str, attributes: Sequence[str]
):
    """Omits serialization of some attributes with falsy values."""
    return {
        name: value
        for name, value in handler(model).items()
        if value or name not in attributes
    }


class Resource(pydantic.BaseModel):
    """Represents a Pulumi resource."""

    model_config = pydantic.ConfigDict(extra="allow")

    file_exclude: ClassVar = {
        "parent_resource",
        # This is a position in the SDK, not the Pulumi program and
        # can change in a different environment (e.g. CI vs local),
        # causing huge state diffs, so ignoring.
        "sourcePosition",
    }

    dependencies: Optional[List[str]] = pydantic.Field(default_factory=list)
    outputs: Optional[Mapping[str, Any]] = None
    parent: Optional[str] = None
    provider: Optional[str] = None
    parent_resource: Optional["Resource"] = None
    type: str
    urn: str

    @classmethod
    def find_parents(cls, resources: Iterable["Resource"]) -> List["Resource"]:
        """Finds parenthood and relationships between resources."""
        urn2resource = {}
        for resource in resources:
            urn2resource[resource.urn] = resource.model_copy()
        for resource in urn2resource.values():
            if resource.parent:
                resource.parent_resource = urn2resource[resource.parent]
        return list(urn2resource.values())

    @property
    def name(self):
        """Pulumi name of the resource."""
        return self.urn.rsplit("::", 1)[-1]

    @pydantic.model_serializer(mode="wrap")
    def _serialize(self, handler):
        return _skip_some_falsy_values(
            self,
            handler,
            [
                "dependencies",
                "outputs",
                "parent",
                "provider",
            ],
        )


class Latest(pydantic.BaseModel):
    """Represents the latest Pulumi stack state checkpoint."""

    model_config = pydantic.ConfigDict(extra="allow")

    resources: Optional[List[Resource]] = pydantic.Field(default_factory=list)


class Checkpoint(pydantic.BaseModel):
    """Represents the Pulumi stack state checkpoint."""

    @pydantic.model_serializer(mode="wrap")
    def _serialize(self, handler):
        return _skip_some_falsy_values(
            self,
            handler,
            ["latest"],
        )

    stack: str
    latest: Optional[Latest] = None


class State(pydantic.BaseModel):
    """Represents the contents of the Pulumi stack state file."""

    file_exclude: ClassVar = {
        "checkpoint": {
            "latest": {
                "resources": {
                    "__all__": Resource.file_exclude,
                },
            },
        },
    }

    checkpoint: Checkpoint
    version: Literal[3]
