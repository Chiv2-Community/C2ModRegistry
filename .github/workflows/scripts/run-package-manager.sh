#!/bin/bash

poetry install
poetry run python3 src/c2modregistry/main.py "$@" > result.txt 2>&1

EXIT_CODE=$?

RESULT=$(cat result.txt)

# The EOF stuff is github actions nonsense
EOF=$(dd if=/dev/urandom bs=15 count=1 status=none | base64)

echo "result<<$EOF" >> $GITHUB_OUTPUT
echo "$RESULT" >> $GITHUB_OUTPUT
echo "$EOF" >> $GITHUB_OUTPUT

FAILED=false
if [ $EXIT_CODE -ne 0 ]; then
    echo ":x: Failed." >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY
    echo '```' >> $GITHUB_STEP_SUMMARY
    cat result.txt >> $GITHUB_STEP_SUMMARY
    echo '```' >> $GITHUB_STEP_SUMMARY
FAILED=true
else
    echo ":white_check_mark: All checks passed." >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY
    echo '```' >> $GITHUB_STEP_SUMMARY
    cat result.txt >> $GITHUB_STEP_SUMMARY
    echo '```' >> $GITHUB_STEP_SUMMARY
fi

echo "failed=$FAILED" >> $GITHUB_OUTPUT

exit $EXIT_CODE