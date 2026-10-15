#!/usr/bin/env bash
# Devuelve el entorno al estado inicial: borra contenedores y volúmenes (la base legacy
# se recarga desde db/init, sin el cambio de esquema; la cola del gateway también se borra).
# Vuelve el dominio Afiliaciones a su estado inicial (borra state/*.mode). No modifica su código ni su .env.
set -euo pipefail
cd "$(dirname "$0")"
docker compose --profile "*" down -v --remove-orphans
rm -f state/*.mode
[ -f .env ] || cp .env.example .env
mkdir -p logs state test-results
docker compose up -d --build
docker compose ps
