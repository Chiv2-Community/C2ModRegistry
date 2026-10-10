#!/usr/bin/env bash
set -euo pipefail

# Also covers retries; unapproved package branches and unchanged/failed runs skip.
if [[ ${REGISTRY_ACTION:-} != add-package-release || ${REGISTRY_FAILED:-} != false ||
      ${COMMIT_OUTCOME:-} != success || ${CHANGES_DETECTED:-} != true ]]; then
  echo 'No successful release commit to sync.'
  exit 0
fi

bash "$(dirname "${BASH_SOURCE[0]}")/validate-rc-registry-source.sh"
[[ ${GITHUB_REF:-} == refs/heads/main ]]
[[ $(git branch --show-current) == main && $(git rev-parse HEAD) == "$SOURCE_SHA" ]]

# Must exist on the default branch: this handoff ships with the receiver in one PR.
gh api --method POST "repos/$GITHUB_REPOSITORY/actions/workflows/sync-rc-registry.yml/dispatches" \
  -f ref=main -f "inputs[source_branch]=$SOURCE_BRANCH" -f "inputs[source_sha]=$SOURCE_SHA"
