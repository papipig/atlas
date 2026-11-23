#!/usr/bin/env bash
set -euo pipefail

CERT_DIR="${1:-infra/docker/certs}"
CERT_KEY="${CERT_DIR}/atlas.local.key"
CERT_CRT="${CERT_DIR}/atlas.local.crt"

mkdir -p "${CERT_DIR}"

openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout "${CERT_KEY}" \
  -out "${CERT_CRT}" \
  -days 365 \
  -subj "/C=FR/ST=IDF/L=Paris/O=Atlas/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

echo "Generated: ${CERT_CRT}"
echo "Generated: ${CERT_KEY}"
