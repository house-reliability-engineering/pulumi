#!/bin/bash

set -o errexit
set -o nounset

cd "$(dirname $0)"

mkdir -p bin

poetry install \
  --quiet \
  --with test

PULUMI_PYTHON_VERSION="$(
  poetry show pulumi |
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

poetry run \
  coverage run \
    --source=pulumi_state_splitter \
    --omit=__main__.py \
    --module unittest

poetry run \
    coverage report --show-missing
