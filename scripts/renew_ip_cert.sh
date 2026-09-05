#!/usr/bin/env bash
# LEGACY/UNUSED on testplatform.farmingo.com.tr: TLS is managed by the host Nginx/Certbot.
set -euo pipefail

cd "$(dirname "$0")/.."
COMPOSE=(docker compose -f docker-compose.test.yml)

"${COMPOSE[@]}" --profile tools run --rm certbot renew \
  --webroot \
  --webroot-path /var/www/certbot \
  --preferred-profile shortlived

"${COMPOSE[@]}" exec nginx nginx -s reload
