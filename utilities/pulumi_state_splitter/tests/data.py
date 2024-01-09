"""Test data."""

import pathlib

import typeguard

from . import util

with typeguard.install_import_hook("pulumi_state_splitter"):
    import pulumi_state_splitter.model
    import pulumi_state_splitter.stored_state

_DATA_DIR = pathlib.Path(__file__).parent / "data"


def resources():
    """Returns a test resource map."""
    provider_urn = (
        "urn:pulumi:test-stack::test-project::pulumi:providers:provider::default"
    )
    provider_id = "deadbeef-dead-beef-dead-beefdeadbeef"
    return util.resource_map(
        [
            pulumi_state_splitter.model.Resource(
                type="foo",
                urn="resource_4",
                dependencies=["resource_2"],
                parent="resource_1",
            ),
            pulumi_state_splitter.model.Resource(
                type="foo",
                urn="resource_2",
                dependencies=[
                    "resource_3",
                    "resource_1",
                ],
            ),
            pulumi_state_splitter.model.Resource(
                type="foo",
                urn="resource_3",
                dependencies=["resource_1"],
                provider=f"{provider_urn}::{provider_id}",
            ),
            pulumi_state_splitter.model.Resource(
                type="foo",
                outputs={"out": "val"},
                urn="resource_0",
            ),
            pulumi_state_splitter.model.Resource(
                type="foo",
                urn="resource_1",
            ),
            pulumi_state_splitter.model.Resource(
                type="provider",
                id=provider_id,
                urn=provider_urn,
            ),
        ]
    )


def multi_stack_split() -> util.Directory:
    """Loads the multi_stack_split data directory."""
    return util.Directory.load(_DATA_DIR / "multi_stack_split")


def multi_stack_unsplit() -> util.Directory:
    """Loads the multi_stack_unsplit data directory."""
    return util.Directory.load(_DATA_DIR / "multi_stack_unsplit")


MULTI_STACK_NAMES = [
    pulumi_state_splitter.stored_state.StackName.from_path(p)
    for p in [
        "test-project-1/test-stack-1",
        "test-project-1/test-stack-2",
        "test-project-2/test-stack-3",
    ]
]

MULTI_STACK_MODELS = [
    {
        "stack_name": pulumi_state_splitter.stored_state.StackName(
            project=project_name,
            stack=stack_name,
        ),
        "state": pulumi_state_splitter.model.State(
            checkpoint=pulumi_state_splitter.model.Checkpoint(
                stack=f"organization/{project_name}/{stack_name}",
            ),
            version=3,
        ),
    }
    for project_name, stacks_names in {
        "test-project-1": ["test-stack-1", "test-stack-2"],
        "test-project-2": ["test-stack-3"],
    }.items()
    for stack_name in stacks_names
]

STACK_NAME = pulumi_state_splitter.stored_state.StackName(
    project="test-project",
    stack="test-stack",
)


def stack_state():
    """Returns a test stack state."""
    stack_urn = "urn:pulumi:test-stack::test-project"
    provider_id = "7160bd4d-b7cb-4fdd-acd5-3a173fd01793"
    provider_urn = f"{stack_urn}::pulumi:providers:command::default_0_9_2"
    return {
        "checkpoint": {
            "latest": {
                "manifest": {
                    "magic": "deadbeef" * 8,
                    "time": "1970-01-01T00:12:34.0+00:00",
                    "version": "v3.99.0",
                },
                "resources": [
                    {
                        "created": "1970-01-01T00:12:37.0Z",
                        "custom": True,
                        "id": provider_id,
                        "inputs": {"version": "0.9.2"},
                        "modified": "1970-01-01T00:12:38.0Z",
                        "outputs": {"version": "0.9.2"},
                        "type": "pulumi:providers:command",
                        "urn": provider_urn,
                    },
                    {
                        "created": "1970-01-01T00:12:35.0Z",
                        "custom": False,
                        "modified": "1970-01-01T00:12:36.0Z",
                        "outputs": {"test-output": "test string"},
                        "sourcePosition": "project:///.../foo.py#1",
                        "type": "pulumi:pulumi:Stack",
                        "urn": stack_urn
                        + "::pulumi:pulumi:Stack::test-project-test-stack",
                    },
                    {
                        "created": "1970-01-01T00:12:39.0Z",
                        "custom": True,
                        "modified": "1970-01-01T00:12:40.0Z",
                        "urn": f"{stack_urn}::command:local:Command::true",
                        "id": "true-15dde2980",
                        "inputs": {"create": "true"},
                        "outputs": {
                            "create": "true",
                            "stderr": "",
                            "stdout": "",
                        },
                        "parent": stack_urn
                        + "::pulumi:pulumi:Stack::test-project-test-stack",
                        "propertyDependencies": {"create": None},
                        "provider": f"{provider_urn}::{provider_id}",
                        "sourcePosition": "project:///.../foo.py#2",
                        "type": "command:local:Command",
                    },
                ],
                "secrets_providers": {
                    "state": {"salt": "v1:foo:v1:bar:baz"},
                    "type": "passphrase",
                },
            },
            "stack": "organization/test-project/test-stack",
        },
        "version": 3,
    }


def stack_model():
    """Returns a test stack model."""
    stack_urn = "urn:pulumi:test-stack::test-project"
    provider_urn = f"{stack_urn}::pulumi:providers:command::default_0_9_2"
    return pulumi_state_splitter.model.State(
        checkpoint=pulumi_state_splitter.model.Checkpoint(
            latest=pulumi_state_splitter.model.Latest(
                manifest={
                    "magic": "deadbeef" * 8,
                    "time": "1970-01-01T00:12:34.0+00:00",
                    "version": "v3.99.0",
                },
                resources=[
                    pulumi_state_splitter.model.Resource(
                        created="1970-01-01T00:12:37.0Z",
                        custom=True,
                        id="7160bd4d-b7cb-4fdd-acd5-3a173fd01793",
                        inputs={"version": "0.9.2"},
                        modified="1970-01-01T00:12:38.0Z",
                        outputs={"version": "0.9.2"},
                        type="pulumi:providers:command",
                        urn=provider_urn,
                    ),
                    parent := pulumi_state_splitter.model.Resource(
                        created="1970-01-01T00:12:35.0Z",
                        custom=False,
                        modified="1970-01-01T00:12:36.0Z",
                        outputs={
                            "test-output": "test string",
                        },
                        sourcePosition="project:///.../foo.py#1",
                        type="pulumi:pulumi:Stack",
                        urn=stack_urn
                        + "::pulumi:pulumi:Stack::test-project-test-stack",
                    ),
                    pulumi_state_splitter.model.Resource(
                        created="1970-01-01T00:12:39.0Z",
                        custom=True,
                        modified="1970-01-01T00:12:40.0Z",
                        id="true-15dde2980",
                        inputs={"create": "true"},
                        outputs={
                            "create": "true",
                            "stderr": "",
                            "stdout": "",
                        },
                        parent=stack_urn
                        + "::pulumi:pulumi:Stack::test-project-test-stack",
                        parent_resource=parent,
                        propertyDependencies={"create": None},
                        provider=provider_urn
                        + "::7160bd4d-b7cb-4fdd-acd5-3a173fd01793",
                        sourcePosition="project:///.../foo.py#2",
                        type="command:local:Command",
                        urn=f"{stack_urn}::command:local:Command::true",
                    ),
                ],
                secrets_providers={
                    "state": {"salt": "v1:foo:v1:bar:baz"},
                    "type": "passphrase",
                },
            ),
            stack="organization/test-project/test-stack",
        ),
        version=3,
    )
