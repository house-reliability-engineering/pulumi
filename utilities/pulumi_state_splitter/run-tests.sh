#!/bin/bash

set -o errexit
set -o nounset

cd "$(dirname $0)"

poetry install \
  --quiet \
  --with test

poetry run \
  coverage run \
    --source=pulumi_state_splitter \
    --omit=__main__.py \
    --module unittest

poetry run \
    coverage report --show-missing
