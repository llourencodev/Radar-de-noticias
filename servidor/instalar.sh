#!/usr/bin/env bash
# Instala o Radar de Notícias num servidor Ubuntu, publicado no seu domínio pela Cloudflare.
#
#   sudo bash servidor/instalar.sh             tudo no servidor: site, coleta de hora em hora e contador
#   sudo bash servidor/instalar.sh --hibrido   site continua no GitHub Pages; aqui fica só o contador
#
# Também liga: atualizações automáticas de segurança, firewall (ufw, liberando o SSH) e backup diário
# dos bancos (de preferência no HD). Pode rodar de novo quando quiser: ele só ajusta o que faltar.
# Detalhes e comandos úteis: servidor/LEIA-ME.md
set -Eeuo pipefail
# se algum comando falhar, mostra qual foi (em vez de sair calado)
trap 'printf "\n\033[1;31m    ✘ Parou na linha %s: %s\033[0m\n    Mande um print desta tela.\n" "$LINENO" "$BASH_COMMAND"' ERR

DOMINIO="${DOMINIO:-datavexsolucoes.com.br}"
HOST_RADAR="${HOST_RADAR:-radar.$DOMINIO}"
HOST_CONTADOR="${HOST_CONTADOR:-contador.$DOMINIO}"
TUNEL="${TUNEL:-radar-servidor}"
PORTA_SITE=8080                       # nginx, só dentro do servidor
MODO=completo
[ "${1:-}" = "--hibrido" ] && MODO=hibrido

passo() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
ok()    { printf '\033[1;32m    ✔ %s\033[0m\n' "$*"; }
aviso() { printf '\033[1;33m    ! %s\033[0m\n' "$*"; }
erro()  { printf '\033[1;31m    ✘ %s\033[0m\n' "$*"; exit 1; }

[ "$(id -u)" = 0 ] || erro "Rode com sudo: sudo bash servidor/instalar.sh"
grep -qi ubuntu /etc/os-release || aviso "Feito para Ubuntu; neste sistema pode precisar de ajustes."
REPO="$(cd "$(dirname "$0")/.." && pwd)"
[ -f "$REPO/contador/instalar.sh" ] || erro "Rode de dentro da pasta do repositório (cd ~/radar-de-noticias)."
export DEBIAN_FRONTEND=noninteractive

echo "Radar de Notícias: instalação no servidor (modo: $MODO)"
[ "$MODO" = completo ] && echo "  Site:     https://$HOST_RADAR"
echo "  Contador: https://$HOST_CONTADOR"

# ---------------------------------------------------------------------------------------------
passo "1/8 Pacotes do sistema"
apt-get update -q
PACOTES=(git curl ca-certificates python3 python3-venv sqlite3 ufw unattended-upgrades)
[ "$MODO" = completo ] && PACOTES+=(nginx)
apt-get install -y -q "${PACOTES[@]}" >/dev/null
ok "Pacotes instalados"

# ---------------------------------------------------------------------------------------------
passo "2/8 Atualizações automáticas de segurança"
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'CONF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
CONF
cat > /etc/apt/apt.conf.d/52radar-unattended <<'CONF'
// Radar: reinicia sozinho às 4h quando uma atualização pedir (ex.: kernel novo)
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "04:00";
CONF
systemctl enable --now unattended-upgrades >/dev/null 2>&1 || true
ok "Atualizações de segurança diárias; reinício automático às 4h só quando necessário"

# ---------------------------------------------------------------------------------------------
passo "3/8 Firewall (ufw)"
# no Ubuntu 24.04 o SSH sobe sob demanda e "sshd -T" falha; nesse caso vale a porta padrão 22
PORTA_SSH="$( (sshd -T 2>/dev/null || true) | awk '/^port /{print $2; exit}')"
PORTA_SSH="${PORTA_SSH:-22}"
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw allow "$PORTA_SSH/tcp" comment 'SSH' >/dev/null
if ip link show tailscale0 >/dev/null 2>&1; then
  ufw allow in on tailscale0 comment 'Tailscale' >/dev/null
  ok "Rede do Tailscale liberada"
fi
ufw --force enable >/dev/null
ok "Firewall ligado: entra só SSH (porta $PORTA_SSH). O site chega pelo túnel, sem abrir porta no roteador"

# ---------------------------------------------------------------------------------------------
passo "4/8 Contador de acessos"
bash "$REPO/contador/instalar.sh"   # sem filtrar a saída: na primeira vez ele pergunta usuário e senha
ENV_CONT=/etc/radar-contador.env
ORIGENS="$(grep -oP '^CONTADOR_ORIGENS=\K.*' "$ENV_CONT" || true)"
if ! grep -q "https://$HOST_RADAR" <<<"$ORIGENS"; then
  ORIGENS="${ORIGENS:+$ORIGENS,}https://$HOST_RADAR"
  if grep -q '^CONTADOR_ORIGENS=' "$ENV_CONT"; then
    sed -i "s#^CONTADOR_ORIGENS=.*#CONTADOR_ORIGENS=$ORIGENS#" "$ENV_CONT"
  else
    echo "CONTADOR_ORIGENS=$ORIGENS" >> "$ENV_CONT"
  fi
  systemctl restart radar-contador
fi
ok "O contador aceita visitas de: $ORIGENS"

# ---------------------------------------------------------------------------------------------
if [ "$MODO" = completo ]; then
  passo "5/8 Radar: código, coleta de hora em hora e site"
  como_radar() { (cd /opt/radar && sudo -H -u radar "$@"); }
  id radar >/dev/null 2>&1 || useradd --system --home-dir /opt/radar --shell /usr/sbin/nologin radar
  install -d -o radar -g radar -m 755 /opt/radar /var/lib/radar
  install -d -o radar -g radar -m 700 /var/lib/radar/dados
  URL_GIT="$(git -C "$REPO" remote get-url origin 2>/dev/null || echo https://github.com/llourencodev/radar-de-noticias.git)"
  if [ ! -d /opt/radar/codigo/.git ]; then
    como_radar git clone -q "$URL_GIT" /opt/radar/codigo
  fi
  [ -x /opt/radar/venv/bin/python ] || como_radar python3 -m venv /opt/radar/venv
  como_radar /opt/radar/venv/bin/pip install -q --upgrade pip
  como_radar /opt/radar/venv/bin/pip install -q -r /opt/radar/codigo/requirements.txt
  ok "Código em /opt/radar/codigo (atualiza sozinho a partir do GitHub, ramo main)"

  if [ ! -f /etc/radar.env ]; then
    cat > /etc/radar.env <<CONF
# Configuração do Radar no servidor (depois de editar: sudo systemctl start radar-coleta)
TZ=America/Sao_Paulo
RADAR_DB=/var/lib/radar/dados/radar.db
GITHUB_REPOSITORY=llourencodev/radar-de-noticias
CONTADOR_URL=https://$HOST_CONTADOR

# IA opcional para resumos (a mesma do GitHub): descomente e preencha
#LLM_PROVIDER=anthropic
#ANTHROPIC_API_KEY=
#ANTHROPIC_MODEL=claude-haiku-5-5
#LLM_MAX_PER_RUN=40
CONF
    chmod 600 /etc/radar.env
  fi

  cat > /opt/radar/atualizar.sh <<'SCRIPT'
#!/usr/bin/env bash
# Roda de hora em hora (radar-coleta.timer): atualiza o código, coleta e troca o site no ar.
# Se algo falhar, o site anterior continua no ar.
set -euo pipefail
cd /opt/radar/codigo
antes="$(git rev-parse HEAD)"
if git fetch -q origin main && git merge -q --ff-only FETCH_HEAD; then
  if ! git diff --quiet "$antes" HEAD -- requirements.txt; then
    /opt/radar/venv/bin/pip install -q -r requirements.txt
  fi
else
  echo "Aviso: não consegui atualizar o código pelo GitHub; sigo com a versão atual."
fi
/opt/radar/venv/bin/python -m unittest discover -s tests -q
atual="$(readlink /var/lib/radar/site 2>/dev/null || true)"
novo=/var/lib/radar/site-a
[ "$atual" = /var/lib/radar/site-a ] && novo=/var/lib/radar/site-b
/opt/radar/venv/bin/python gerar_site.py --saida "$novo"
ln -sfn "$novo" /var/lib/radar/site.tmp
mv -T /var/lib/radar/site.tmp /var/lib/radar/site
echo "Site atualizado ($novo)"
SCRIPT
  chmod 755 /opt/radar/atualizar.sh

  cat > /etc/systemd/system/radar-coleta.service <<'UNIT'
[Unit]
Description=Radar de Noticias: coleta e gera o site
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=radar
Group=radar
EnvironmentFile=/etc/radar.env
ExecStart=/opt/radar/atualizar.sh
TimeoutStartSec=50min
Nice=10
NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=/opt/radar /var/lib/radar
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
MemoryMax=1500M
UNIT
  cat > /etc/systemd/system/radar-coleta.timer <<'UNIT'
[Unit]
Description=Radar de Noticias: coleta de hora em hora

[Timer]
OnCalendar=*-*-* *:07:00
Persistent=true

[Install]
WantedBy=timers.target
UNIT

  cat > /etc/nginx/sites-available/radar <<CONF
# Radar de Notícias: só dentro do servidor; quem leva até a internet é o túnel da Cloudflare
server {
    listen 127.0.0.1:$PORTA_SITE;
    server_name $HOST_RADAR;
    root /var/lib/radar/site;
    index index.html;
    server_tokens off;
    gzip on;
    gzip_types application/json application/javascript text/css;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

    location / { try_files \$uri \$uri/ =404; add_header Cache-Control "no-cache" always; }
    location ~* \.(js|css)\$ { add_header Cache-Control "public, max-age=300" always; }
    location ~ /\. { deny all; }
}
CONF
  ln -sfn /etc/nginx/sites-available/radar /etc/nginx/sites-enabled/radar
  # o site padrão do nginx (porta 80) não é usado
  [ "$(readlink -f /etc/nginx/sites-enabled/default 2>/dev/null)" = /etc/nginx/sites-available/default ] \
    && rm -f /etc/nginx/sites-enabled/default
  nginx -t -q
  systemctl enable --now nginx >/dev/null 2>&1
  systemctl reload nginx

  systemctl daemon-reload
  systemctl enable --now radar-coleta.timer >/dev/null 2>&1
  if [ ! -L /var/lib/radar/site ]; then
    echo "    Primeira coleta: lê todas as fontes, leva uns 10 a 30 minutos. Pode acompanhar em outro"
    echo "    terminal com: journalctl -fu radar-coleta"
    systemctl start radar-coleta || aviso "A primeira coleta falhou. Veja: journalctl -u radar-coleta -n 80"
  else
    systemctl start --no-block radar-coleta
  fi
  [ -L /var/lib/radar/site ] && ok "Site gerado; nova coleta a cada hora (minuto 7)"
else
  passo "5/8 Radar: fica no GitHub Pages (modo híbrido), nada a instalar aqui"
fi

# ---------------------------------------------------------------------------------------------
passo "6/8 Túnel da Cloudflare ($TUNEL)"
if ! command -v cloudflared >/dev/null; then
  install -d -m 755 /usr/share/keyrings
  curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg -o /usr/share/keyrings/cloudflare-main.gpg
  echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' \
    > /etc/apt/sources.list.d/cloudflared.list
  apt-get update -q && apt-get install -y -q cloudflared >/dev/null
fi
# o cloudflared também recebe as atualizações automáticas
echo 'Unattended-Upgrade::Origins-Pattern { "site=pkg.cloudflare.com"; };' > /etc/apt/apt.conf.d/53radar-cloudflared
ok "cloudflared $(cloudflared --version 2>/dev/null | awk '{print $3}')"

export HOME=/root
if [ ! -f /root/.cloudflared/cert.pem ]; then
  echo
  echo "    >>> Abra o link que vai aparecer abaixo (pode ser no seu computador ou celular),"
  echo "    >>> entre na Cloudflare e clique em $DOMINIO > Authorize. Depois volte aqui."
  echo
  cloudflared tunnel login
fi
id_do_tunel() {  # a lista do cloudflared já deixa de fora os túneis apagados
  cloudflared tunnel list -o json 2>/dev/null | python3 -c '
import json, sys
print(next((t["id"] for t in json.load(sys.stdin) or [] if t["name"] == sys.argv[1]), ""))' "$TUNEL"
}
ID="$(id_do_tunel || true)"
if [ -z "$ID" ]; then
  cloudflared tunnel create "$TUNEL" >/dev/null
  ID="$(id_do_tunel || true)"
fi
[ -n "$ID" ] || erro "Não consegui criar o túnel na Cloudflare. Veja a mensagem acima."
install -d -m 755 /etc/cloudflared
if [ ! -f "/etc/cloudflared/$ID.json" ]; then
  [ -f "/root/.cloudflared/$ID.json" ] || erro "O túnel $TUNEL já existe mas a chave dele não está neste servidor. Apague o túnel no painel da Cloudflare (Zero Trust > Networks > Tunnels) e rode de novo."
  install -m 600 "/root/.cloudflared/$ID.json" "/etc/cloudflared/$ID.json"
fi
{
  echo "tunnel: $ID"
  echo "credentials-file: /etc/cloudflared/$ID.json"
  echo "ingress:"
  if [ "$MODO" = completo ]; then
    echo "  - hostname: $HOST_RADAR"
    echo "    service: http://127.0.0.1:$PORTA_SITE"
  fi
  echo "  - hostname: $HOST_CONTADOR"
  echo "    service: http://127.0.0.1:$(grep -oP '^CONTADOR_PORTA=\K\d+' "$ENV_CONT" || echo 8787)"
  echo "  - service: http_status:404"
} > /etc/cloudflared/config.yml
cloudflared tunnel ingress validate --config /etc/cloudflared/config.yml >/dev/null
HOSTS=("$HOST_CONTADOR")
[ "$MODO" = completo ] && HOSTS+=("$HOST_RADAR")
for h in "${HOSTS[@]}"; do
  if cloudflared tunnel route dns --overwrite-dns "$TUNEL" "$h" >/dev/null 2>&1; then
    ok "DNS: $h aponta para o túnel"
  else
    aviso "Não consegui criar o DNS de $h (confira se o domínio $DOMINIO está ativo na Cloudflare)"
  fi
done
if [ ! -f /etc/systemd/system/cloudflared.service ]; then
  cloudflared --config /etc/cloudflared/config.yml service install >/dev/null 2>&1
fi
systemctl enable cloudflared >/dev/null 2>&1
systemctl restart cloudflared
ok "Túnel ligado (serviço cloudflared, sobe sozinho quando o servidor liga)"

# ---------------------------------------------------------------------------------------------
passo "7/8 Backup diário dos bancos"
CONF_BKP=/etc/radar-backup.conf
if [ -f "$CONF_BKP" ]; then
  # shellcheck disable=SC1090
  . "$CONF_BKP"
else
  DESTINO=""; MONTAGEM=""
  if [ -n "${BACKUP_DIR:-}" ]; then
    DESTINO="$BACKUP_DIR"
  else
    # disco físico onde está o sistema (funciona também com LVM, padrão do Ubuntu Server)
    DISCO_RAIZ="$( (lsblk -srno NAME,TYPE "$(findmnt -no SOURCE /)" 2>/dev/null || true) | awk '$2=="disk"{print $1; exit}')"
    # outra unidade (o HD) já montada?
    mapfile -t MONTADOS < <(lsblk -rno NAME,PKNAME,TYPE,MOUNTPOINT | awk -v r="$DISCO_RAIZ" \
      '$3=="part" && $2!=r && $2!="" && $4!="" && $4!="/" && $4!~/^\/boot/ && $4!="[SWAP]" {print $4}')
    if [ "${#MONTADOS[@]}" -eq 1 ]; then
      MONTAGEM="${MONTADOS[0]}"
    elif [ "${#MONTADOS[@]}" -eq 0 ]; then
      # HD conectado mas não montado: oferece montar (só ext4; nada é formatado)
      mapfile -t LIVRES < <(lsblk -rno NAME,PKNAME,TYPE,FSTYPE,MOUNTPOINT,SIZE | awk -v r="$DISCO_RAIZ" \
        '$3=="part" && $2!=r && $2!="" && $4=="ext4" && NF==5 {print $1" "$5}')
      if [ "${#LIVRES[@]}" -eq 1 ]; then
        PART="/dev/${LIVRES[0]%% *}"; TAM="${LIVRES[0]##* }"
        read -r -p "    Montar o HD $PART ($TAM) em /mnt/hd para os backups? [S/n] " R </dev/tty || R=n
        if [[ ! "$R" =~ ^[nN] ]]; then
          UUID="$(blkid -s UUID -o value "$PART")"
          install -d /mnt/hd
          grep -q "$UUID" /etc/fstab || echo "UUID=$UUID /mnt/hd ext4 defaults,nofail 0 2" >> /etc/fstab
          systemctl daemon-reload; mount /mnt/hd && MONTAGEM=/mnt/hd
        fi
      fi
    else
      aviso "Achei mais de uma unidade montada: ${MONTADOS[*]}"
      read -r -p "    Em qual pasta guardar os backups? " DESTINO </dev/tty || true
    fi
    [ -n "$MONTAGEM" ] && DESTINO="$MONTAGEM/backup-radar"
  fi
  if [ -z "$DESTINO" ]; then
    DESTINO=/var/backups/radar
    aviso "Não achei o HD: os backups vão para $DESTINO (no SSD). Veja no LEIA-ME como mudar para o HD."
  fi
  [ -n "$MONTAGEM" ] || MONTAGEM="$(findmnt -no TARGET --target "$(dirname "$DESTINO")" 2>/dev/null || echo /)"
  printf 'DESTINO=%q\nMONTAGEM=%q\nDIAS=30\n' "$DESTINO" "$MONTAGEM" > "$CONF_BKP"
  # shellcheck disable=SC1090
  . "$CONF_BKP"
fi
install -d -m 700 "$DESTINO"

cat > /usr/local/sbin/radar-backup <<'SCRIPT'
#!/usr/bin/env bash
# Cópia diária dos bancos e configurações do Radar (radar-backup.timer). Guarda DIAS dias.
set -euo pipefail
. /etc/radar-backup.conf
if [ "$MONTAGEM" != / ] && ! mountpoint -q "$MONTAGEM"; then
  echo "O HD ($MONTAGEM) não está montado: backup não feito"; exit 1
fi
dia="$DESTINO/$(date +%F)"
install -d -m 700 "$dia"
for banco in /var/lib/radar-contador/acessos.db /var/lib/radar/dados/radar.db; do
  [ -f "$banco" ] || continue
  sqlite3 "$banco" ".backup '$dia/$(basename "$banco")'"
  gzip -f "$dia/$(basename "$banco")"
done
tar -czf "$dia/configuracao.tar.gz" --ignore-failed-read -C / \
  etc/radar.env etc/radar-contador.env etc/cloudflared etc/radar-backup.conf 2>/dev/null || true
find "$DESTINO" -mindepth 1 -maxdepth 1 -type d -name '20*' -mtime +"${DIAS:-30}" -exec rm -rf {} +
echo "Backup em $dia ($(du -sh "$dia" | cut -f1))"
SCRIPT
chmod 700 /usr/local/sbin/radar-backup
cat > /etc/systemd/system/radar-backup.service <<'UNIT'
[Unit]
Description=Radar de Noticias: backup diario dos bancos

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/radar-backup
UNIT
cat > /etc/systemd/system/radar-backup.timer <<'UNIT'
[Unit]
Description=Radar de Noticias: backup diario as 3h30

[Timer]
OnCalendar=*-*-* 03:30:00
Persistent=true

[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now radar-backup.timer >/dev/null 2>&1
/usr/local/sbin/radar-backup | sed 's/^/    /' || aviso "O primeiro backup falhou (veja a mensagem acima)"
ok "Backup todo dia às 3h30 em $DESTINO (guarda 30 dias)"

# ---------------------------------------------------------------------------------------------
passo "8/8 Conferindo os links (a Cloudflare pode levar 1 ou 2 minutos)"
confere() {  # $1 = endereço
  for _ in $(seq 1 24); do
    curl -fsS -o /dev/null --max-time 10 "$1" 2>/dev/null && return 0
    sleep 5
  done
  return 1
}
TUDO_OK=1
if confere "https://$HOST_CONTADOR/saude"; then ok "https://$HOST_CONTADOR/saude responde"; else aviso "https://$HOST_CONTADOR ainda não responde"; TUDO_OK=0; fi
if [ "$MODO" = completo ]; then
  if confere "https://$HOST_RADAR/"; then ok "https://$HOST_RADAR responde"; else aviso "https://$HOST_RADAR ainda não responde"; TUDO_OK=0; fi
fi

echo
echo "================================================================================"
if [ "$TUDO_OK" = 1 ]; then echo " Pronto!"; else
  echo " Instalado, mas algum link ainda não respondeu. Espere uns minutos e abra no navegador;"
  echo " se continuar fora, veja: journalctl -u cloudflared -n 50"
fi
echo
if [ "$MODO" = completo ]; then
  echo " Abra: https://$HOST_RADAR"
  echo
  echo " Para o link antigo (github.io) levar ao novo endereço, no GitHub crie a variável"
  echo "   Settings > Secrets and variables > Actions > Variables > New repository variable"
  echo "   Nome: SITE_URL    Valor: https://$HOST_RADAR"
else
  echo " No GitHub, troque a variável CONTADOR_URL para: https://$HOST_CONTADOR"
  echo "   Settings > Secrets and variables > Actions > Variables"
  echo " e ligue o endereço radar.$DOMINIO ao GitHub Pages (passo a passo em servidor/LEIA-ME.md)."
fi
echo "================================================================================"
