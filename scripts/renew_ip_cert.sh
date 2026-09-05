#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
COMPOSE=(docker compose --env-file .env.test -f docker-compose.test.yml)

"${COMPOSE[@]}" --profile tools run --rm certbot renew --webroot --webroot-path /var/www/certbot --preferred-profile shortlived
"${COMPOSE[@]}" exec nginx nginx -s reload
