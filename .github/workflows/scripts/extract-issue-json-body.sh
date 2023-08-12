#!/bin/bash
# Issue number passed as an argument
ISSUE_NUMBER="$1"

# Fetch issue body using GitHub CLI
BODY_CONTENT=$(GH_TOKEN=$GITHUB_TOKEN gh api "repos/${GITHUB_REPOSITORY}/issues/${ISSUE_NUMBER}" -q '.body')

EXTRACTED_JSON=$(echo "$BODY_CONTENT" | awk '/^```/{flag=1; next} /^```/{flag=0} flag')

echo "$EXTRACTED_JSON" | jq empty

# Check the exit status to determine if JSON is valid
if [[ $? -eq 0 ]]; then
    # Github actions nonsense
    EOF=$(dd if=/dev/urandom bs=15 count=1 status=none | base64)
    echo "payload<<$EOF" >> $GITHUB_OUTPUT
    echo "$EXTRACTED_JSON" >> $GITHUB_OUTPUT
    echo "$EOF" >> $GITHUB_OUTPUT

    exit 0
else
    exit 1
fi

