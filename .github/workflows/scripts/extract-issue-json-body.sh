#!/bin/bash
# Issue number passed as an argument
ISSUE_NUMBER="$1"

# Fetch issue body using GitHub CLI
BODY_CONTENT=$(gh api "repos/${GITHUB_REPOSITORY}/issues/${ISSUE_NUMBER}" -q '.body')

EXTRACTED_JSON=$(echo "$BODY_CONTENT" | awk '/^```/{flag=1; next} /^```/{flag=0} flag')

echo "$EXTRACTED_JSON" | jq empty

FAILED=false
# If extracted json is empty then we failed
if [[ -z "$EXTRACTED_JSON" ]]; then
  FAILED=true
fi

echo "failed=$FAILED" >> $GITHUB_OUTPUT

# Github actions nonsense
EOF=$(dd if=/dev/urandom bs=15 count=1 status=none | base64)
echo "payload<<$EOF" >> $GITHUB_OUTPUT
echo "$EXTRACTED_JSON" >> $GITHUB_OUTPUT
echo "$EOF" >> $GITHUB_OUTPUT
