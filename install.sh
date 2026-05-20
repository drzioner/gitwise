#!/usr/bin/env bash
# install.sh — install gitwise to ~/.local/bin
# Usage: bash install.sh [--dry-run]
# To update: gitwise update
set -Eeuo pipefail

trap 'exit 130' INT TERM

BIN_DIR="${GITWISE_BIN_DIR:-$HOME/.local/bin}"
DRY_RUN=false

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
    esac
done

_SELF="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd "$(dirname "$_SELF")" && pwd)"
SOURCE="$SCRIPT_DIR/bin/gitwise"
TARGET="$BIN_DIR/gitwise"

if [[ ! -f "$SOURCE" ]]; then
    echo "error: bin/gitwise not found in $SCRIPT_DIR" >&2
    exit 1
fi

if [[ "$DRY_RUN" == "true" ]]; then
    echo "would install to: $TARGET"
    echo "would symlink: $SOURCE -> $TARGET"
    if ! printf '%s\n' "${PATH//:/$'\n'}" | grep -qx "$BIN_DIR"; then
        echo "would add to PATH: $BIN_DIR (not currently in PATH)"
    fi
    exit 0
fi

mkdir -p "$BIN_DIR"
ln -snf "$SOURCE" "$TARGET"
chmod +x "$SOURCE"

if command -v pip &>/dev/null; then
    pip install -e "$SCRIPT_DIR" --quiet || echo "warning: pip install failed (non-fatal)" >&2
elif command -v uv &>/dev/null; then
    uv pip install -e "$SCRIPT_DIR" --no-scripts || echo "warning: uv pip install failed (non-fatal)" >&2
fi

echo "gitwise installed at: $TARGET"

if ! printf '%s\n' "${PATH//:/$'\n'}" | grep -qx "$BIN_DIR"; then
    echo ""
    echo "NOTE: $BIN_DIR is not in PATH."
    echo "Add to ~/.zshrc:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo "Then: source ~/.zshrc"
fi

echo ""
echo "Try: gitwise doctor"
echo "To update: gitwise update"
