#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -f .env ]]; then echo '.env existente preservado.'; exit 0; fi
umask 077
printf 'POSTGRES_PASSWORD=%s\nDB_BIND_IP=127.0.0.1\n' "$(openssl rand -hex 24)" > .env
echo '.env criado com segredo aleatorio; nao exibir no video nem publicar.'
