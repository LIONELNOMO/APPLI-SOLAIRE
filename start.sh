#!/bin/sh
# Démarrage en hébergement : Render (comme Koyeb ou Northflank) impose le
# port d'écoute par la variable PORT. La valeur par défaut sert au test
# local de l'image.
set -e
exec uvicorn app.main:create_app \
    --factory \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips '*'
