#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose ps
docker compose logs --tail 30 app db
for container in zelacidade-orbital-app-rm558710 zelacidade-orbital-db-rm558710; do
  echo "=== $container ==="
  docker container exec "$container" sh -c 'pwd; ls -l; whoami'
  docker inspect --format 'Nome={{.Name}} Usuario={{.Config.User}} Redes={{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}} Portas={{json .NetworkSettings.Ports}}' "$container"
done
test "$(docker container exec zelacidade-orbital-app-rm558710 id -u)" -ne 0
docker volume inspect zelacidade-orbital-data-rm558710
docker container exec zelacidade-orbital-db-rm558710 psql -U orbital -d orbital -c '\dt'
docker container exec zelacidade-orbital-db-rm558710 psql -U orbital -d orbital -c '\d "Alertas"'
