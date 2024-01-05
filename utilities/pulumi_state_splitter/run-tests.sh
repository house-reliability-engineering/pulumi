#!/bin/bash

set -o errexit
set -o nounset

PYTHON=python3.11

$PYTHON -m pip \
  install \
  --quiet \
  poetry

cd "$(dirname $0)"

mkdir -p bin

$PYTHON -m poetry \
  install \
  --quiet \
  --with test

PULUMI_PYTHON_VERSION="$(
  $PYTHON -m poetry show pulumi |
  awk '$1 == "version" { print "v" $3}'
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

$PYTHON -m poetry \
  run \
  coverage run \
    --source=pulumi_state_splitter \
    --omit=__main__.py \
    --module unittest

TESTS_EXIT_CODE="$?"

set -o errexit

$PYTHON -m poetry \
  run \
  coverage \
  report \
  --fail-under=100 \
  --show-missing &&
exit "$TESTS_EXIT_CODE"
