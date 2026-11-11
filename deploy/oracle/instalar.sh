#!/usr/bin/env bash
# Instala (ou atualiza) o Radar Inteligente de Notícias numa VM Ubuntu da Oracle Cloud.
#
# Uso, já conectado na VM por SSH:
#   curl -fsSL -o instalar.sh https://raw.githubusercontent.com/llourencodev/radar-de-noticias/main/deploy/oracle/instalar.sh
#   sudo bash instalar.sh
#
# O que ele faz:
#   1. Instala Python, nginx, git e certbot.
#   2. Baixa o código em /opt/radar e cria o ambiente Python (.venv).
#   3. Cria o serviço "radar" (liga sozinho quando a VM reinicia; coleta de hora em hora).
#   4. Coloca o nginx na frente, com usuário e senha para só você entrar.
#   5. Libera as portas 80 e 443 no firewall do Ubuntu.
#   6. (Opcional) Ativa HTTPS grátis com Let's Encrypt.
#
# Rodar de novo = atualizar o código e reiniciar, sem perder o banco nem a senha.
# Nenhuma senha ou chave é gravada no repositório: ficam só na VM
# (/etc/nginx/radar.htpasswd e /opt/radar/.env).
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/llourencodev/radar-de-noticias.git}"
BRANCH="${BRANCH:-main}"
APP_DIR="/opt/radar"
APP_USER="radar"
HTPASSWD="/etc/nginx/radar.htpasswd"
NGINX_SITE="/etc/nginx/sites-available/radar"

ok()   { printf '\n\033[1;32m✔ %s\033[0m\n' "$*"; }
info() { printf '\n\033[1;34m→ %s\033[0m\n' "$*"; }
erro() { printf '\n\033[1;31m✘ %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || erro "Rode com sudo:  sudo bash instalar.sh"
grep -qi ubuntu /etc/os-release || erro "Este script foi feito para Ubuntu."

# Perguntas são lidas do teclado mesmo se o script vier por pipe.
perguntar() { local __v; read -r -p "$1" __v </dev/tty || true; printf '%s' "$__v"; }

# ---------------------------------------------------------------- 1. pacotes
info "Instalando pacotes do sistema (1 a 3 minutos)..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git nginx apache2-utils \
  certbot python3-certbot-nginx iptables-persistent curl >/dev/null
timedatectl set-timezone America/Sao_Paulo || true
ok "Pacotes instalados"

# ---------------------------------------------------------------- 2. código
id "$APP_USER" >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/radar --shell /usr/sbin/nologin "$APP_USER"

if [ -d "$APP_DIR/.git" ]; then
  info "Atualizando o código em $APP_DIR..."
  sudo -u "$APP_USER" git -C "$APP_DIR" fetch -q origin "$BRANCH"
  sudo -u "$APP_USER" git -C "$APP_DIR" reset -q --hard "origin/$BRANCH"
else
  info "Baixando o código em $APP_DIR..."
  mkdir -p "$APP_DIR"; chown "$APP_USER:$APP_USER" "$APP_DIR"
  sudo -u "$APP_USER" git clone -q --branch "$BRANCH" "$REPO_URL" "$APP_DIR" \
    || erro "Não consegui baixar $REPO_URL. Se o repositório for privado, deixe-o público ou me avise."
fi

info "Preparando o ambiente Python..."
[ -x "$APP_DIR/.venv/bin/python" ] || sudo -u "$APP_USER" python3 -m venv "$APP_DIR/.venv"
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -q --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
sudo -u "$APP_USER" mkdir -p "$APP_DIR/data"

if [ ! -f "$APP_DIR/.env" ]; then
  sudo -u "$APP_USER" cp "$APP_DIR/.env.example" "$APP_DIR/.env"
fi
# O app só escuta dentro da VM; quem fala com a internet é o nginx.
sed -i 's/^RADAR_HOST=.*/RADAR_HOST=127.0.0.1/; s/^RADAR_PORT=.*/RADAR_PORT=8000/' "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"; chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
ok "Código e dependências prontos"

# ---------------------------------------------------------------- 3. serviço
cat >/etc/systemd/system/radar.service <<EOF
[Unit]
Description=Radar Inteligente de Noticias
After=network-online.target
Wants=network-online.target

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python run.py --no-browser
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
NoNewPrivileges=true
ProtectSystem=full
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable -q radar
systemctl restart radar
ok "Serviço 'radar' ligado (reinicia sozinho se cair ou se a VM reiniciar)"

# ---------------------------------------------------------------- 4. login
if [ ! -s "$HTPASSWD" ]; then
  info "Crie o login do painel (só quem souber entra)."
  USUARIO="$(perguntar '  Usuário: ')"
  [ -n "$USUARIO" ] || USUARIO="admin"
  htpasswd -c -B "$HTPASSWD" "$USUARIO" </dev/tty
  chown root:www-data "$HTPASSWD"; chmod 640 "$HTPASSWD"
  ok "Login criado para '$USUARIO'"
else
  ok "Login já existente mantido (para trocar a senha: sudo htpasswd -B $HTPASSWD SEU_USUARIO)"
fi

# ---------------------------------------------------------------- 5. nginx
IP_PUBLICO="$(curl -fsS --max-time 5 https://ifconfig.me 2>/dev/null || curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || true)"
NOME_ATUAL=""
[ -f "$NGINX_SITE" ] && NOME_ATUAL="$(awk '/server_name/{gsub(";","",$2); print $2; exit}' "$NGINX_SITE")"

if [ ! -f "$NGINX_SITE" ]; then
cat >"$NGINX_SITE" <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 2m;

    auth_basic "Radar de Noticias";
    auth_basic_user_file /etc/nginx/radar.htpasswd;

    # Necessário para o Let's Encrypt validar o domínio
    location /.well-known/acme-challenge/ { auth_basic off; root /var/www/html; }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
EOF
fi
ln -sf "$NGINX_SITE" /etc/nginx/sites-enabled/radar
rm -f /etc/nginx/sites-enabled/default
nginx -t -q && systemctl reload nginx
ok "nginx configurado na porta 80, com login"

# ---------------------------------------------------------------- 6. firewall do Ubuntu
# As imagens Ubuntu da Oracle vêm com iptables bloqueando tudo menos SSH.
for PORTA in 80 443; do
  if ! iptables -C INPUT -p tcp --dport "$PORTA" -m state --state NEW -j ACCEPT 2>/dev/null; then
    # Entra antes da regra REJECT final (se existir); senão, no fim da lista.
    LINHA="$(iptables -L INPUT --line-numbers -n | awk '$2=="REJECT"{print $1; exit}')"
    if [ -n "$LINHA" ]; then
      iptables -I INPUT "$LINHA" -p tcp --dport "$PORTA" -m state --state NEW -j ACCEPT
    else
      iptables -A INPUT -p tcp --dport "$PORTA" -m state --state NEW -j ACCEPT
    fi
  fi
done
netfilter-persistent save >/dev/null 2>&1 || true
ok "Portas 80 e 443 liberadas no firewall do Ubuntu"

# ---------------------------------------------------------------- 7. HTTPS (opcional)
if [ -z "$NOME_ATUAL" ] || [ "$NOME_ATUAL" = "_" ]; then
  SUGESTAO=""
  [ -n "$IP_PUBLICO" ] && SUGESTAO="$(echo "$IP_PUBLICO" | tr . -).sslip.io"
  echo
  echo "  HTTPS deixa a senha e as páginas criptografadas. É grátis."
  echo "  Se você não tem domínio, pode usar o endereço gratuito: $SUGESTAO"
  RESP="$(perguntar "  Ativar HTTPS agora? Digite o domínio, Enter para usar ${SUGESTAO:-um domínio}, ou 'n' para pular: ")"
  [ -z "$RESP" ] && RESP="$SUGESTAO"
  if [ -n "$RESP" ] && [ "$RESP" != "n" ] && [ "$RESP" != "N" ]; then
    sed -i "s/server_name _;/server_name $RESP;/" "$NGINX_SITE"
    nginx -t -q && systemctl reload nginx
    if certbot --nginx -d "$RESP" --non-interactive --agree-tos --register-unsafely-without-email --redirect; then
      NOME_ATUAL="$RESP"
      ok "HTTPS ativo (o certificado renova sozinho)"
    else
      echo "  Não deu para ativar o HTTPS agora (confira se a porta 80 está aberta na Oracle). O site segue em HTTP."
      echo "  Para tentar de novo depois: sudo certbot --nginx -d $RESP --redirect"
    fi
  fi
fi

# ---------------------------------------------------------------- fim
sleep 3
if systemctl is-active -q radar && curl -fsS -o /dev/null http://127.0.0.1:8000/api/status; then
  ok "Radar no ar!"
else
  echo; echo "  O serviço ainda está subindo ou deu erro. Veja com:  sudo journalctl -u radar -n 50"
fi
echo
if [ -n "$NOME_ATUAL" ] && [ "$NOME_ATUAL" != "_" ]; then
  echo "  Abra no navegador:  https://$NOME_ATUAL"
else
  echo "  Abra no navegador:  http://${IP_PUBLICO:-IP-DA-VM}"
fi
echo "  A primeira coleta leva de 5 a 10 minutos; depois atualiza sozinho de hora em hora."
echo
echo "  Comandos úteis:"
echo "    sudo systemctl status radar        # ver se está rodando"
echo "    sudo journalctl -u radar -f        # acompanhar a coleta ao vivo"
echo "    sudo nano /opt/radar/.env          # mudar configurações (depois: sudo systemctl restart radar)"
echo "    sudo bash instalar.sh              # atualizar para a versão mais nova do GitHub"
echo
