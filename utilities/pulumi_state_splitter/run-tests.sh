#!/bin/bash

set -o errexit
set -o nounset

cd "$(dirname $0)"

mkdir -p bin

uv sync --quiet

PULUMI_PYTHON_VERSION="$(
  uv pip show pulumi |
  awk '$1 == "Version:" { print "v" $2}'
)"

PULUMI_BIN_VERSION="$(bin/pulumi version 2>/dev/null || echo none)"


if [[ ! "$PULUMI_BIN_VERSION" = "$PULUMI_PYTHON_VERSION" ]]
then
  URL="https://get.pulumi.com/releases/sdk/pulumi-v$PULUMI_PYTHON_VERSION-linux-x64.tar.gz"
  cat 1>&2 <<EOF
Pulumi binary version ($PULUMI_BIN_VERSION) does not match
the Python SDK version ($PULUMI_PYTHON_VERSION),
fetching $URL
EOF
  curl -s "https://get.pulumi.com/releases/sdk/pulumi-$PULUMI_PYTHON_VERSION-linux-x64.tar.gz" |
  tar \
    --directory bin \
    --gunzip \
    --extract \
    --strip-components 1
fi

PATH="$PWD/bin:$PATH"

set +o errexit

uv run \
  coverage run \
    --source=pulumi_state_splitter \
    --omit=__main__.py \
    --module unittest

TESTS_EXIT_CODE="$?"

set -o errexit

uv run \
  coverage \
  report \
  --fail-under=100 \
  --show-missing


export TEST_BACKEND_DIRECTORY="$(mktemp -d)"
cp -r tests/data/multi_stack_split/* "$TEST_BACKEND_DIRECTORY"

# Basic smoke test for the CLI
uv run -- \
  pulumi_state_splitter \
  --backend-directory "$TEST_BACKEND_DIRECTORY" \
  run -- \
    diff \
      --new-file \
      --recursive \
      --unified \
      tests/data/multi_stack_unsplit \
      "$TEST_BACKEND_DIRECTORY"

exit "$TESTS_EXIT_CODE"
