#!/usr/bin/bash
set -euo pipefail

INFILE="LC250.csv"

# Expected line format:
# number,title,difficulty
# Where 'title' may contain commas.
while IFS= read -r LINE; do
  # Skip empty lines
  [[ -z "$LINE" ]] && continue

  # Extract number (everything before the first comma)
  number="${LINE%%,*}"
  rest="${LINE#*,}"

  # Extract difficulty (everything after the last comma)
  difficulty="${rest##*,}"

  # Extract title (everything between the first and last comma)
  title="${rest%,*}"

  # Trim whitespace
  number="$(echo -n "$number" | xargs)"
  title="$(echo -n "$title" | xargs)"
  difficulty="$(echo -n "$difficulty" | xargs | tr '[:upper:]' '[:lower:]')"

  # Run the CLI command
  python3 lc_tracker.py add-problem "$number" "$title" "$difficulty"
done < "$INFILE"
