#!/usr/bin/env bash
set -euo pipefail
PACK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${1:-.}"
OUT="${2:-$REPO/.qdw/review}"

PYTHONPATH="$PACK/reference/src" python -m qdw_review.cli scan "$REPO" --profile quick --out "$OUT" || true
PYTHONPATH="$PACK/reference/src" python -m qdw_review.cli report "$OUT/latest.json" --html "$OUT/report.html"
PYTHONPATH="$PACK/reference/src" python -m qdw_review.cli sarif "$OUT/latest.json" --out "$OUT/review.sarif"
echo "Review: $OUT/latest.json"
echo "HTML:   $OUT/report.html"
echo "SARIF:  $OUT/review.sarif"
