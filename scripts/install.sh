#!/usr/bin/env bash
set -euo pipefail

# Production install — skips dev-only directories.

pip install -e "$(dirname "$0")/.."

echo ""
echo "Installed cummand. To remove dev files (public/, tests/) run:"
echo "  rm -rf public tests"
