# pulumi_state_splitter manipulates a Pulumi state file to make it more VCS friendly

## Purpose

It is intended to be used with
[Pulumi](https://www.pulumi.com/product/) and
[gitolize](https://github.com/house-reliability-engineering/gitolize).
It makes the state change commit diffs more useful.

## What it does

It converts the state file from JSON to YAML,
writing each resource to a separate file.

It can also reverse the operation for ingestion of the
state by the Pulumi command.

## Usage

```console
utilities/pulumi_state_splitter$ poetry run pulumi_state_splitter --help
Usage: pulumi_state_splitter [OPTIONS] COMMAND [ARGS]...

  pulumi_yaml_splitter command line interface.

Options:
  -d, --backend-directory DIRECTORY
  --help                          Show this message and exit.

Commands:
  run      Runs a command with the stack states unsplit.
  split    Splits single Pulumi stack state files into multiple files each.
  unsplit  Merges split Pulumi stack states into single state file each.
utilities/pulumi_state_splitter$
```

```console
utilities/pulumi_state_splitter$ poetry run pulumi_state_splitter run --help
Usage: pulumi_state_splitter run [OPTIONS] [COMMAND]...

  Runs a command with the stack states unsplit.

Options:
  -a, --all-stacks
  -s, --stack PROJECT-NAME/STACK-NAME
  --help                          Show this message and exit.
utilities/pulumi_state_splitter$
```

```console
utilities/pulumi_state_splitter$ poetry run pulumi_state_splitter split --help
Usage: pulumi_state_splitter split [OPTIONS]

  Splits single Pulumi stack state files into multiple files each.

Options:
  -a, --all-stacks
  -s, --stack PROJECT-NAME/STACK-NAME
  --help                          Show this message and exit.
utilities/pulumi_state_splitter$
```

```console
utilities/pulumi_state_splitter$ poetry run pulumi_state_splitter unsplit --help
Usage: pulumi_state_splitter unsplit [OPTIONS]

  Merges split Pulumi stack states into single state file each.

Options:
  -a, --all-stacks
  -s, --stack PROJECT-NAME/STACK-NAME
  --help                          Show this message and exit.
utilities/pulumi_state_splitter$
```
