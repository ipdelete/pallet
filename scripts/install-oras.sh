#!/bin/bash
set -e

# Install ORAS CLI - OCI Registry As Storage
# https://oras.land/

VERSION="${ORAS_VERSION:-1.2.2}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"

echo "Installing ORAS CLI v${VERSION}..."

# Detect OS and architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "$ARCH" in
    x86_64)
        ARCH="amd64"
        ;;
    aarch64|arm64)
        ARCH="arm64"
        ;;
    armv7l)
        ARCH="armv7"
        ;;
    *)
        echo "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

case "$OS" in
    linux|darwin)
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

# Construct download URL
FILENAME="oras_${VERSION}_${OS}_${ARCH}.tar.gz"
URL="https://github.com/oras-project/oras/releases/download/v${VERSION}/${FILENAME}"

echo "Downloading from: $URL"

# Create temporary directory
TMP_DIR=$(mktemp -d)
trap "rm -rf $TMP_DIR" EXIT

# Download and extract
cd "$TMP_DIR"
curl -LO "$URL"
tar -xzf "$FILENAME"

# Create install directory if it doesn't exist
mkdir -p "$INSTALL_DIR"

# Install binary
mv oras "$INSTALL_DIR/oras"
chmod +x "$INSTALL_DIR/oras"

echo "✓ ORAS CLI v${VERSION} installed successfully to $INSTALL_DIR/oras"

# Check if install directory is in PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo ""
    echo "Warning: $INSTALL_DIR is not in your PATH"
    echo "Add it to your PATH by adding this line to your ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
fi

# Verify installation
if command -v oras &> /dev/null; then
    echo ""
    oras version
else
    echo ""
    echo "Run '$INSTALL_DIR/oras version' to verify installation"
fi
