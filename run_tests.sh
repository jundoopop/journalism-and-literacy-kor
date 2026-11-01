#!/usr/bin/env bash
# Run the complete offline Python and JavaScript suites from any directory.
set -euo pipefail

python_bin="${PYTHON_BIN:-python3}"
node_bin="${NODE_BIN:-node}"

for executable in "$python_bin" "$node_bin"; do
    if ! command -v "$executable" >/dev/null 2>&1; then
        echo "Required test runtime not found: $executable" >&2
        exit 1
    fi
done

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

# Install requirements-dev.txt in the selected Python environment beforehand.
# Extra arguments are forwarded to pytest, e.g. bash run_tests.sh -q.
"$python_bin" -m pytest tests --cov=scripts --cov-report=term-missing --cov-report=html "$@"
"$node_bin" --test tests/extension.test.cjs
