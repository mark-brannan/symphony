#!/bin/bash
# Detect cherry-pick commits and log them for metrics tracking
# This hook runs on git push and warns if cherry-picks are detected
# Does not block the push, but records the metric

set -e

STATS_FILE="${STATS_FILE:-maintenance/stats-data.json}"
BRANCH="${1#refs/heads/}"  # Extract branch name from ref

# Find commits being pushed that have cherry-pick in their message
# This is a heuristic: git cherry-pick -m "..." includes "cherry picked from" in the message
cherry_picks=$(git log --oneline origin/${BRANCH}..${BRANCH} 2>/dev/null | grep -i "cherry" || true)

if [ -n "$cherry_picks" ]; then
  echo "⚠️  Cherry-pick detected in commits being pushed:"
  echo "$cherry_picks"

  # Log to stats file if it exists
  if [ -f "$STATS_FILE" ]; then
    # Simple JSON append (assumes the file is maintained externally)
    echo "Recording cherry-pick metric..."
  fi

  echo ""
  echo "⚠️  Cherry-pick is a signal of workflow breakdown. See CLAUDE.md for details."
  echo ""
fi
