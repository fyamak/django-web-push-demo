#!/usr/bin/env bash
# LEGACY/UNUSED on testplatform.farmingo.com.tr: TLS is managed by the host Nginx/Certbot.
set -euo pipefail

cd "$(dirname "$0")/.."

# Let's Encrypt hesabı için e-posta adresini burada değiştir.
LETSENCRYPT_EMAIL="admin@example.com"

if [ "$LETSENCRYPT_EMAIL" = "admin@example.com" ]; then
  echo "scripts/bootstrap_test_https.sh içindeki LETSENCRYPT_EMAIL değerini kendi e-posta adresinle değiştir."
  exit 1
fi

COMPOSE=(docker compose -f docker-compose.test.yml)

mkdir -p nginx/active
cp nginx/test-http.conf nginx/active/default.conf
"${COMPOSE[@]}" up -d --build db web nginx

echo "Let's Encrypt IP sertifikası isteniyor..."
"${COMPOSE[@]}" --profile tools run --rm certbot certonly \
  --non-interactive \
  --agree-tos \
  --email "$LETSENCRYPT_EMAIL" \
  --preferred-profile shortlived \
  --webroot \
  --webroot-path /var/www/certbot \
  --ip-address 31.97.37.175

cp nginx/test-https.conf nginx/active/default.conf
"${COMPOSE[@]}" exec nginx nginx -t
"${COMPOSE[@]}" exec nginx nginx -s reload

echo "Hazır: https://31.97.37.175"
