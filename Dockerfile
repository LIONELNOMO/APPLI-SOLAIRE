# Image de la version web : l'interface construite est servie par FastAPI,
# donc une seule origine et aucun problème de requêtes croisées.
#
# L'accès est protégé par un mot de passe partagé, défini par la variable
# DIMSOLAIRE_MOT_DE_PASSE. Sans elle, le service démarre ouvert : c'est
# acceptable en local, jamais sur internet.
#
# Les comptes utilisateurs individuels (JWT, Argon2) restent prévus en
# phase 6 et ne sont pas écrits.

# --- 1. Construction de l'interface ---------------------------------
FROM node:22-slim AS interface

WORKDIR /interface
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# --- 2. Image finale -------------------------------------------------
FROM python:3.12-slim

# Le moteur de calcul n'a pas besoin de compilateur : seules les roues
# sont installées, ce qui garde l'image légère.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DIMSOLAIRE_MODE=web \
    DIMSOLAIRE_STATIC_DIR=/app/static

WORKDIR /app

COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY start.sh ./

RUN pip install --upgrade pip \
    && pip install ".[web]" \
    && chmod +x start.sh \
    && adduser --disabled-password --gecos "" --uid 10001 dimsolaire \
    && chown -R dimsolaire:dimsolaire /app

COPY --from=interface --chown=dimsolaire:dimsolaire /interface/dist ./static

USER dimsolaire
ENV PORT=8000
EXPOSE 8000

# Le conteneur est considéré sain dès que le moteur répond, sur
# le port que l'hébergeur a choisi.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/api/v1/health',timeout=3).status==200 else 1)"

CMD ["./start.sh"]
