#!/usr/bin/env bash
# install.sh — install gitwise via uv tool install (works remote: curl | bash)
# Usage: bash install.sh [--dry-run] [--version=X.Y.Z] [--help]
#
# Remote one-liner:
#   curl -fsSL https://raw.githubusercontent.com/drzioner/gitwise/main/install.sh | bash
#
# This installer:
#   1. Installs uv if not present (via https://astral.sh/uv/install.sh).
#   2. Runs `uv tool install --upgrade gitwise-cli` (isolated venv, no PyPI pollution).
#   3. Prints PATH guidance if `gitwise` is not yet on PATH.
#
# Supported OS: macOS, Linux. Windows users: see README for alternatives.

set -Eeuo pipefail

trap 'exit 130' INT TERM

# Allow override (e.g. pin a specific uv version: UV_INSTALLER_URL="https://astral.sh/uv/0.11.21/install.sh")
UV_INSTALLER_URL="${UV_INSTALLER_URL:-https://astral.sh/uv/install.sh}"

DRY_RUN=false
TARGET_VERSION=""

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --version=*)
            TARGET_VERSION="${arg#*=}"
            if ! printf '%s' "$TARGET_VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
                echo "error: --version must be in X.Y.Z format (got '$TARGET_VERSION')" >&2
                exit 2
            fi
            ;;
        --help|-h)
            cat <<'EOF'
gitwise installer

Usage: bash install.sh [OPTIONS]

Options:
  --dry-run         Print actions without executing them.
  --version=X.Y.Z   Pin a specific version (default: latest from PyPI).
  --help, -h        Show this help and exit.

Environment:
  UV_INSTALLER_URL  Override the uv installer URL (default: https://astral.sh/uv/install.sh).
                    Pin a version with: UV_INSTALLER_URL="https://astral.sh/uv/0.11.21/install.sh"

Remote:
  curl -fsSL https://raw.githubusercontent.com/drzioner/gitwise/main/install.sh | bash
EOF
            exit 0
            ;;
        *)
            echo "error: unknown argument '$arg' (try --help)" >&2
            exit 2
            ;;
    esac
done

OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
    Darwin) printf 'gitwise installer - macOS (%s)\n' "$ARCH" ;;
    Linux)  printf 'gitwise installer - Linux (%s)\n' "$ARCH" ;;
    *)
        echo "error: unsupported OS '$OS'. This installer supports macOS and Linux." >&2
        echo "Windows users: see README for alternative install methods." >&2
        exit 1
        ;;
esac
echo "-----------------------------------------"

if ! command -v curl >/dev/null 2>&1; then
    echo "error: curl is required. Install curl via your package manager and re-run." >&2
    exit 1
fi

NEED_UV_INSTALL=false
if command -v uv >/dev/null 2>&1; then
    echo "uv: present ($(uv --version 2>/dev/null || echo 'version unknown'))"
else
    NEED_UV_INSTALL=true
    echo "uv: not found"
fi

if [ -n "$TARGET_VERSION" ]; then
    PACKAGE_SPEC="gitwise-cli==$TARGET_VERSION"
    echo "target version: $TARGET_VERSION"
else
    PACKAGE_SPEC="gitwise-cli"
    echo "target version: latest"
fi

if [ "$DRY_RUN" = "true" ]; then
    echo ""
    echo "[dry-run] plan:"
    if [ "$NEED_UV_INSTALL" = "true" ]; then
        echo "  - curl -LsSf $UV_INSTALLER_URL | sh"
    fi
    if [ -n "$TARGET_VERSION" ]; then
        echo "  - uv tool install $PACKAGE_SPEC"
    else
        echo "  - uv tool install --upgrade $PACKAGE_SPEC"
    fi
    echo "  - print PATH guidance if 'gitwise' not on PATH"
    exit 0
fi

if [ "$NEED_UV_INSTALL" = "true" ]; then
    echo ""
    echo "Installing uv ($UV_INSTALLER_URL)..."
    curl -LsSf "$UV_INSTALLER_URL" | sh

    if [ -x "$HOME/.local/bin/uv" ]; then
        export PATH="$HOME/.local/bin:$PATH"
    fi
    if ! command -v uv >/dev/null 2>&1; then
        echo "error: uv installer finished but 'uv' is not on PATH." >&2
        echo "       Add $HOME/.local/bin to PATH and re-run, or open a new shell." >&2
        exit 1
    fi
    echo "uv installed: $(uv --version)"
fi

echo ""
if [ -n "$TARGET_VERSION" ]; then
    echo "Installing gitwise $TARGET_VERSION..."
    uv tool install "$PACKAGE_SPEC"
else
    echo "Installing/upgrading gitwise..."
    uv tool install --upgrade "$PACKAGE_SPEC"
fi

# No post-install verification needed here: `set -e` (line 15) already aborted
# the script if `uv tool install` returned non-zero. A `uv tool list | grep`
# check would be both redundant and fragile under `pipefail`. The PATH check
# below uses `command -v gitwise` directly, which is the actually useful signal.

UV_BIN_DIR="$HOME/.local/bin"
if command -v gitwise >/dev/null 2>&1; then
    INSTALLED_VERSION="$(gitwise --version 2>/dev/null || echo 'gitwise (version unknown)')"
    echo ""
    echo "$INSTALLED_VERSION is ready."
    echo ""
    echo "Try:           gitwise doctor"
    echo "Update later:  uv tool upgrade gitwise-cli"
    echo "Uninstall:     uv tool uninstall gitwise-cli"
else
    echo ""
    echo "gitwise installed, but the 'gitwise' command is not yet on PATH."
    echo "uv places tool entry points in: $UV_BIN_DIR"
    echo ""
    echo "Pick one:"
    echo "  1. Run:    uv tool update-shell"
    echo "     (uv will add $UV_BIN_DIR to your shell profile automatically.)"
    echo "  2. Or add this line to ~/.zshrc (or ~/.bashrc):"
    echo "       export PATH=\"$UV_BIN_DIR:\$PATH\""
    echo "Then open a new shell, or: source ~/.zshrc"
fi
