#!/usr/bin/env bash
set -euo pipefail
# Execute como root em Ubuntu 24.04 LTS.
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y docker.io docker-compose-v2 git curl python3 openssl
systemctl enable --now docker
usermod -aG docker orbitaladmin
docker --version
docker compose version
echo 'Docker instalado. Reconecte por SSH para aplicar o grupo docker.'
