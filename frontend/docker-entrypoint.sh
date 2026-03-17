#!/bin/sh
set -e

CERT_DIR="/etc/nginx/certs"
CERT_FILE="$CERT_DIR/server.crt"
KEY_FILE="$CERT_DIR/server.key"

# Generate self-signed certificate if not provided
if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "TreeVuln: Generating self-signed TLS certificate..."
    mkdir -p "$CERT_DIR"
    openssl req -x509 -nodes -days 365 \
        -newkey rsa:2048 \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -subj "/CN=treevuln.local/O=TreeVuln" \
        2>/dev/null
    # Rendre les certificats lisibles par nginx-user (non-root)
    chown nginx-user:nginx-user "$CERT_FILE" "$KEY_FILE"
    chmod 640 "$CERT_FILE" "$KEY_FILE"
    echo "TreeVuln: Self-signed certificate generated."
    echo "TreeVuln: Mount real certificates at $CERT_DIR for production use."
fi

# Lancer nginx — les worker processes tournent en tant que nginx-user
# (configuré dans /etc/nginx/nginx.conf via la directive 'user')
exec nginx -g "daemon off;"
