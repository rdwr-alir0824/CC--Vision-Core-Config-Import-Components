#!/usr/bin/env bash
set -euo pipefail

repository="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${repository}/src${PYTHONPATH:+:${PYTHONPATH}}"
exec python3 -B -m cc_vision_import.backup_setup "$@"
