#!/usr/bin/env bash
# install.sh — instala gitwise en ~/.local/bin
# Uso: bash install.sh [--dry-run]
# Para actualizar: gitwise update
set -euo pipefail

BIN_DIR="${GITWISE_BIN_DIR:-$HOME/.local/bin}"
DRY_RUN=false

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$SCRIPT_DIR/bin/gitwise"
TARGET="$BIN_DIR/gitwise"

if [[ ! -f "$SOURCE" ]]; then
    echo "error: no se encontró bin/gitwise en $SCRIPT_DIR" >&2
    exit 1
fi

if [[ "$DRY_RUN" == "true" ]]; then
    echo "would install to: $TARGET"
    echo "would symlink: $SOURCE → $TARGET"
    if ! printf '%s\n' "${PATH//:/$'\n'}" | grep -qx "$BIN_DIR"; then
        echo "would add to PATH: $BIN_DIR (no está en PATH actualmente)"
    fi
    exit 0
fi

mkdir -p "$BIN_DIR"
ln -snf "$SOURCE" "$TARGET"
chmod +x "$SOURCE"

echo "✓ gitwise instalado en: $TARGET"

if ! printf '%s\n' "${PATH//:/$'\n'}" | grep -qx "$BIN_DIR"; then
    echo ""
    echo "AVISO: $BIN_DIR no está en PATH."
    echo "Agrega a ~/.zshrc:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo "Luego: source ~/.zshrc"
fi

echo ""
echo "Prueba con: gitwise doctor"
echo "Para actualizar: gitwise update"
