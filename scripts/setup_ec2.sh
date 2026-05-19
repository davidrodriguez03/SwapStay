#!/bin/bash
# =============================================================================
# SwapStay — Setup inicial en EC2 Ubuntu 24.04 LTS (t2.medium)
# Ejecutar UNA sola vez después de crear la instancia:
#   chmod +x scripts/setup_ec2.sh && bash scripts/setup_ec2.sh
# =============================================================================

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/TU_USUARIO/SwapStay.git}"
APP_DIR="/opt/swapstay"

echo "=============================================="
echo " SwapStay — Setup EC2 Ubuntu 24.04"
echo "=============================================="

# 1. Actualizar paquetes del sistema
echo "[1/6] Actualizando sistema..."
sudo apt-get update -y && sudo apt-get upgrade -y

# 2. Instalar dependencias base
echo "[2/6] Instalando dependencias..."
sudo apt-get install -y git curl ca-certificates gnupg lsb-release

# 3. Instalar Docker Engine
echo "[3/6] Instalando Docker..."
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Agregar usuario actual al grupo docker (evita sudo en cada comando)
sudo usermod -aG docker "$USER"

# Habilitar Docker al inicio
sudo systemctl enable docker
sudo systemctl start docker

# 4. Clonar repositorio
echo "[4/6] Clonando repositorio en $APP_DIR..."
sudo mkdir -p "$APP_DIR"
sudo chown "$USER":"$USER" "$APP_DIR"
git clone "$REPO_URL" "$APP_DIR"
cd "$APP_DIR"

# 5. Configurar variables de entorno
echo "[5/6] Configurando .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANTE: edita el archivo .env con tus valores reales:"
    echo "    nano $APP_DIR/.env"
    echo ""
fi

# 6. Configurar firewall básico
echo "[6/6] Configurando firewall (UFW)..."
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS (futuro)
sudo ufw --force enable

echo ""
echo "=============================================="
echo " Setup completado."
echo " Pasos siguientes:"
echo "  1. Edita: nano $APP_DIR/.env"
echo "  2. Cierra sesión y vuelve a entrar (grupo docker)"
echo "  3. Ejecuta: bash $APP_DIR/scripts/deploy.sh"
echo "=============================================="
