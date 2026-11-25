#!/bin/sh
set -e
# Popula o banco na primeira subida (o seed não faz nada se já houver filmes).
if [ "${SEED_ON_START:-false}" = "true" ]; then
  python -m app.seed
fi
exec "$@"
