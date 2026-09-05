#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env.test ]; then
  echo ".env.test bulunamadı. Önce: cp .env.test.example .env.test"
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env.test
set +a

if [ -z "${LETSENCRYPT_EMAIL:-}" ] || [[ "$LETSENCRYPT_EMAIL" == *"YOUR_EMAIL"* ]]; then
  echo "LETSENCRYPT_EMAIL .env.test içinde gerçek bir e-posta olmalı."
  exit 1
fi

COMPOSE=(docker compose --env-file .env.test -f docker-compose.test.yml)

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
