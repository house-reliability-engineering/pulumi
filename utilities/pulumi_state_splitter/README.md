# state_splitter manipulates a Pulumi state file to make it more VCS friendly

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
