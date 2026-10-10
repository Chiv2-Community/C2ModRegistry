#!/usr/bin/env bash
set -euo pipefail

# Both the producer handoff and the receiver validate before any writes.
if [[ ${SOURCE_BRANCH:-} != main || ! ${SOURCE_SHA:-} =~ ^[0-9a-f]{40}$ ]]; then
  echo 'RC sync requires an immutable main commit.' >&2
  exit 1
fi
git fetch --no-tags origin '+refs/heads/main:refs/remotes/origin/main'
git cat-file -e "$SOURCE_SHA^{commit}"
git merge-base --is-ancestor "$SOURCE_SHA" refs/remotes/origin/main
