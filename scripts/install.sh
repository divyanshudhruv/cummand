#!/usr/bin/env bash
set -euo pipefail

# Usage install (removes dev-only directories)
# For development, skip this script.

echo "Removing public/ and tests/ directories..."
rm -rf "$(dirname "$0")/../public" "$(dirname "$0")/../tests"
echo "Done."

pip install -e "$(dirname "$0")/.."
