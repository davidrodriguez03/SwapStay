#!/bin/bash
# =============================================================================
# SwapStay — Script de despliegue en AWS EC2
# Uso: bash scripts/deploy.sh [--no-cache]
# =============================================================================

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_FLAGS=""

if [[ "${1:-}" == "--no-cache" ]]; then
    BUILD_FLAGS="--no-cache"
    echo "[deploy] Build sin caché solicitado"
fi

echo "=============================================="
echo " SwapStay — Deploy"
echo " Dir: $APP_DIR"
echo " Fecha: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="

cd "$APP_DIR"

# Verificar que .env existe
if [ ! -f .env ]; then
    echo "ERROR: .env no encontrado. Copia .env.example y completa los valores."
    exit 1
fi

# Verificar que ENV_TYPE está en el .env
if ! grep -q "^ENV_TYPE=" .env; then
    echo "ERROR: ENV_TYPE no definido en .env"
    exit 1
fi

# 1. Pull del código más reciente
echo "[1/5] Actualizando código..."
git pull origin main

# 2. Build de imágenes
echo "[2/5] Construyendo imágenes Docker..."
docker compose build $BUILD_FLAGS

# 3. Ejecutar migraciones de Django
echo "[3/5] Aplicando migraciones..."
docker compose run --rm django python manage.py migrate --noinput

# 4. Levantar todos los servicios
echo "[4/5] Levantando servicios..."
docker compose up -d --remove-orphans

# 5. Verificar estado
echo "[5/5] Verificando servicios..."
sleep 5
docker compose ps

echo ""
echo "=============================================="
echo " Deploy completado."
echo " Servicios activos:"
echo "   Frontend:        http://$(curl -s ifconfig.me 2>/dev/null || echo 'TU_IP')/"
echo "   API v1 (DRF):    http://$(curl -s ifconfig.me 2>/dev/null || echo 'TU_IP')/api/v1/"
echo "   Health Nginx:    http://$(curl -s ifconfig.me 2>/dev/null || echo 'TU_IP')/health"
echo "   μS Moneda:       http://$(curl -s ifconfig.me 2>/dev/null || echo 'TU_IP')/api/v2/moneda/tasas"
echo "   μS Geo:          http://$(curl -s ifconfig.me 2>/dev/null || echo 'TU_IP')/api/v2/geolocalizacion/ciudades"
echo "=============================================="
