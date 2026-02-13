#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Check for changes (staged, unstaged, untracked)
if git diff --quiet --exit-code 2>/dev/null \
   && git diff --cached --quiet --exit-code 2>/dev/null \
   && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    echo "No changes to commit."
    exit 0
fi

# Build commit message
if [ $# -eq 0 ]; then
    MSG="WIP: $(date '+%Y-%m-%d %H:%M:%S')"
else
    MSG="$*"
fi

echo "Committing: $MSG"
git add -A
git commit -m "$MSG"
git push

echo "Done."
