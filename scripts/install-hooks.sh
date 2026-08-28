#!/usr/bin/env bash
# =============================================================================
# install-hooks.sh — install the repo's git pre-commit hooks
# =============================================================================
# Copies scripts/git-hooks/* into .git/hooks/ so they run on every commit.
# Safe to re-run; it just overwrites the hooks for this repo.
#
#   bash scripts/install-hooks.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_SRC="$SCRIPT_DIR/git-hooks"
HOOKS_DST="$REPO_ROOT/.git/hooks"

if [[ ! -d "$HOOKS_DST" ]]; then
    echo "error: $HOOKS_DST does not exist (is this a git repo?)." >&2
    exit 1
fi

installed=0
for hook in "$HOOKS_SRC"/*; do
    [[ -e "$hook" ]] || continue
    name="$(basename "$hook")"
    cp "$hook" "$HOOKS_DST/$name"
    chmod +x "$HOOKS_DST/$name"
    echo "Installed hook: $name"
    installed=$((installed + 1))
done

if [[ "$installed" -eq 0 ]]; then
    echo "No hooks found in $HOOKS_SRC." >&2
    exit 1
fi

echo "Done. Hooks will run on the next 'git commit'."
