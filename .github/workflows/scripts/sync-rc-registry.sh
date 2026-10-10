#!/usr/bin/env bash
set -euo pipefail

export SOURCE_BRANCH=${SOURCE_BRANCH:-main}
export SOURCE_SHA=${SOURCE_SHA:-$(git rev-parse HEAD)}
[[ ${GITHUB_REF:-refs/heads/main} == refs/heads/main ]]
bash "$(dirname "${BASH_SOURCE[0]}")/validate-rc-registry-source.sh"
source_commit=$SOURCE_SHA
destination=update-registry-format
git fetch --no-tags origin "refs/heads/$destination:refs/remotes/origin/$destination"
git checkout --detach "refs/remotes/origin/$destination"
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'

if git merge-base --is-ancestor "$source_commit" HEAD; then
  echo 'Compatibility branch already contains the source snapshot.'
  exit 0
fi

if ! git merge --no-edit "$source_commit"; then
  git merge --abort
  echo 'Compatibility merge conflicted; destination was not pushed.' >&2
  exit 1
fi

git push origin "HEAD:refs/heads/$destination"
