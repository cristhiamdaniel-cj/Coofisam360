# syntax=docker/dockerfile:1

# ============ Base ==========
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# ============ Deps ==========
FROM base AS deps
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# ============ Build ==========
FROM base AS builder
WORKDIR /app
ENV DJANGO_SETTINGS_MODULE=coofisam_project.settings
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY django ./django
WORKDIR /app/django
RUN python manage.py collectstatic --noinput || true

# ============ Runtime ==========
FROM python:3.12-slim AS runner
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=coofisam_project.settings
WORKDIR /app/django

# Copiar dependencias
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Copiar proyecto ya preparado
COPY --from=builder /app/django /app/django

# Exponer puerto del backend
EXPOSE 8060

# Migraciones y arranque con Gunicorn
CMD sh -c "python manage.py migrate --noinput && gunicorn coofisam_project.wsgi:application --bind 0.0.0.0:8060 --workers 3"

