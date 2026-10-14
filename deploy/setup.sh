#!/usr/bin/env bash
# Instalação em Ubuntu (ARM ou x86). Execute como root: sudo bash deploy/setup.sh
set -euo pipefail

APP_DIR=/opt/frota-litoral-med
DATA_DIR=/var/lib/frota-litoral-med
REPO_URL=${REPO_URL:-https://github.com/edgard2509/Frota-Litoral-Med.git}

[ "$(id -u)" -eq 0 ] || { echo "Execute como root (sudo)."; exit 1; }

apt-get update
apt-get install -y curl git ca-certificates debian-keyring debian-archive-keyring apt-transport-https gpg

# Node.js 24 (o servidor exige >= 22.13 por causa de node:sqlite)
curl -fsSL https://deb.nodesource.com/setup_24.x | bash -
apt-get install -y nodejs

# Caddy (proxy reverso com HTTPS automático)
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
apt-get update
apt-get install -y caddy

id frota >/dev/null 2>&1 || useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin frota

if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$APP_DIR"
fi
install -d -o frota -g frota -m 700 "$DATA_DIR"

install -m 644 "$APP_DIR/deploy/frota-litoral-med.service" /etc/systemd/system/frota-litoral-med.service
install -m 644 "$APP_DIR/deploy/Caddyfile" /etc/caddy/Caddyfile
install -m 755 "$APP_DIR/deploy/backup.sh" /usr/local/bin/frota-backup
echo '15 3 * * * root /usr/local/bin/frota-backup' > /etc/cron.d/frota-backup

# Imagens Ubuntu da Oracle bloqueiam portas por iptables além do grupo de segurança da nuvem
iptables -C INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || iptables -I INPUT 5 -p tcp --dport 80 -j ACCEPT
iptables -C INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || iptables -I INPUT 5 -p tcp --dport 443 -j ACCEPT
if command -v netfilter-persistent >/dev/null; then netfilter-persistent save; fi

systemctl daemon-reload
systemctl enable --now frota-litoral-med
systemctl restart caddy

sleep 2
curl -fsS http://127.0.0.1:8000/api/session && echo && echo "Instalado. Acesse http://IP_PUBLICO"
