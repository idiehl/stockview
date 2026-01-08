#!/usr/bin/env bash
set -euo pipefail

INPUT="${1:-docs/master_log/Master_Log.md}"
CSS="${2:-docs/master_log/pdf.css}"

# build_master_log.sh — Markdown -> PDF using md-to-pdf (Node)
# Usage:
#   bash scripts/build_master_log.sh
#   bash scripts/build_master_log.sh docs/master_log/Master_Log.md docs/master_log/pdf.css

if [[ ! -f "$INPUT" ]]; then echo "Missing input markdown: $INPUT" >&2; exit 1; fi
if [[ ! -f "$CSS" ]]; then echo "Missing stylesheet: $CSS" >&2; exit 1; fi

# md-to-pdf writes the PDF next to the .md file with the same base name.
DIR="$(dirname "$INPUT")"
FILE="$(basename "$INPUT")"
CSS_ABS="$(cd "$(dirname "$CSS")" && pwd)/$(basename "$CSS")"
OUTPUT="${INPUT%.md}.pdf"

if command -v npx >/dev/null 2>&1; then
  pushd "$DIR" >/dev/null
  # --yes supported on newer npm; if it fails, retry without it.
  if npx --yes md-to-pdf "$FILE" --stylesheet "$CSS_ABS" >/dev/null 2>&1; then
    :
  else
    npx md-to-pdf "$FILE" --stylesheet "$CSS_ABS"
  fi
  popd >/dev/null
  echo "Built $OUTPUT"
else
  echo "PDF build failed: npx not found. Install Node.js and md-to-pdf." >&2
  echo "Suggested: npm i -D md-to-pdf" >&2
  exit 1
fi
