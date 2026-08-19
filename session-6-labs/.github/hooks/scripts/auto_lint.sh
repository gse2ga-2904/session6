#!/usr/bin/env bash
# DEPRECATED (kept for one cohort): the advisory linter is now auto_lint.py —
# hook commands must not depend on bash on Windows. This stub just forwards.
exec python "$(dirname "$0")/auto_lint.py"
