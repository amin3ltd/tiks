#!/usr/bin/env sh
set -eu

if command -v make >/dev/null 2>&1; then
    make install
else
    python3 scripts/install.py --mode local --quick
fi

printf '\nDone. Start tiks with:\n  make run-local\n\nThen open:\n  http://localhost:8000/control/\n'
