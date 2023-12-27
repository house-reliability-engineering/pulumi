"""Model representing a Pulumi stack state."""

from typing import Any, ClassVar, Iterable, List, Mapping, Optional

import pydantic


class Resource(pydantic.BaseModel):
    """Represents a Pulumi resource."""

    model_config = pydantic.ConfigDict(extra="allow")

    file_exclude: ClassVar = {"parent_resource"}

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

    # workaround for https://github.com/pydantic/pydantic/discussions/5461
    @pydantic.model_serializer(mode="wrap")
    def _serialize(self, handler):
        """Omits serialization of some attributes with falsy values."""
        data = handler(self)
        for attribute in [
            "dependencies",
            "outputs",
            "parent",
            "provider",
        ]:
            if not data[attribute]:
                data.pop(attribute)
        return data


class Latest(pydantic.BaseModel):
    """Represents the latest Pulumi stack state checkpoint."""

    model_config = pydantic.ConfigDict(extra="allow")

    resources: Optional[List[Resource]] = pydantic.Field(default_factory=list)


class Checkpoint(pydantic.BaseModel):
    """Represents the Pulumi stack state checkpoint."""

    # workaround for https://github.com/pydantic/pydantic/discussions/5461
    @pydantic.model_serializer(mode="wrap")
    def _serialize(self, handler):
        """Omits serialization of latest if None."""
        data = handler(self)
        if not data["latest"]:
            data.pop("latest")
        return data

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
    version: int
