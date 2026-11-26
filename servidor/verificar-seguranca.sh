#!/usr/bin/env bash
# Verificação de segurança do servidor do Radar. SÓ LÊ: não muda nada.
#   sudo bash servidor/verificar-seguranca.sh
# O resultado também fica em ~/verificacao-seguranca.txt (para mandar a quem for ajudar).
set -uo pipefail
[ "$(id -u)" = 0 ] || { echo "Rode com sudo: sudo bash servidor/verificar-seguranca.sh"; exit 1; }
CASA="$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)"
SAIDA="$CASA/verificacao-seguranca.txt"
exec > >(tee "$SAIDA") 2>&1

OK=0; AVISO=0; RISCO=0
ok()    { OK=$((OK+1));       printf '  [OK]    %s\n' "$*"; }
aviso() { AVISO=$((AVISO+1)); printf '  [ATENÇÃO] %s\n' "$*"; }
risco() { RISCO=$((RISCO+1)); printf '  [RISCO] %s\n' "$*"; }
info()  { printf '          %s\n' "$*"; }
secao() { printf '\n== %s\n' "$*"; }

echo "Verificação de segurança: $(hostname), $(date '+%d/%m/%Y %H:%M')"
. /etc/os-release 2>/dev/null; echo "Sistema: ${PRETTY_NAME:-?}, kernel $(uname -r)"

# ---------------------------------------------------------------------------
secao "1. Atualizações"
if systemctl is-enabled -q unattended-upgrades 2>/dev/null && grep -qs 'Unattended-Upgrade "1"' /etc/apt/apt.conf.d/20auto-upgrades; then
  ok "Atualizações automáticas de segurança ligadas"
else
  risco "Atualizações automáticas desligadas"
fi
ULT="$(ls -t /var/log/unattended-upgrades/unattended-upgrades.log 2>/dev/null | head -1)"
[ -n "$ULT" ] && info "Última atualização automática: $(date -r "$ULT" '+%d/%m %H:%M')"
PEND="$(apt-get -s -o Debug::NoLocking=1 upgrade 2>/dev/null | grep -c '^Inst ' || true)"
SEG="$(apt-get -s -o Debug::NoLocking=1 upgrade 2>/dev/null | grep '^Inst ' | grep -ci security || true)"
if [ "${SEG:-0}" -gt 0 ]; then aviso "$SEG atualização(ões) de segurança pendente(s) (de $PEND no total)"
elif [ "${PEND:-0}" -gt 0 ]; then ok "Sem atualização de segurança pendente ($PEND comuns)"
else ok "Sistema em dia"; fi
if [ -f /var/run/reboot-required ]; then aviso "O sistema pede reinício (será feito às 4h automaticamente)"; fi

# ---------------------------------------------------------------------------
secao "2. Firewall e portas abertas"
if ufw status 2>/dev/null | grep -q "Status: active"; then
  ok "Firewall (ufw) ligado"
  ufw status 2>/dev/null | sed -n '/^--/,$p' | tail -n +2 | sed 's/^/          /'
else
  risco "Firewall (ufw) DESLIGADO"
fi
echo "  Programas aceitando conexões de fora do servidor:"
EXPOSTAS="$(ss -H -tulpn 2>/dev/null | awk '$5 !~ /^(127\.|\[::1\]|::1|\[?fe80)/ {print $1, $5, $7}' | grep -v 'tailscaled\|systemd-resolve' || true)"
if [ -z "$EXPOSTAS" ]; then info "(nenhum)"; else echo "$EXPOSTAS" | sed 's/users:(("\([^"]*\)".*/\1/; s/^/          /'; fi
info "(o firewall bloqueia tudo isso menos o SSH; o que importa de verdade é a Docker, abaixo)"
if command -v docker >/dev/null && docker ps -q 2>/dev/null | grep -q .; then
  PUB="$(docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep -E '0\.0\.0\.0:|:::' || true)"
  if [ -n "$PUB" ]; then
    risco "Containers Docker com porta aberta para a rede (a Docker passa por cima do ufw):"
    echo "$PUB" | sed 's/^/          /'
  else ok "Containers Docker sem porta aberta para a rede"; fi
else
  ok "Nenhum container Docker rodando"
fi
if command -v tailscale >/dev/null; then
  FUN="$(tailscale funnel status 2>/dev/null | grep -i 'https://' || true)"
  if [ -n "$FUN" ]; then
    aviso "Tailscale Funnel ainda publica algo na internet (o túnel antigo do contador):"
    echo "$FUN" | sed 's/^/          /'
  else ok "Tailscale Funnel desligado"; fi
fi

# ---------------------------------------------------------------------------
secao "3. Acesso remoto (SSH)"
SSHCONF="$( (sshd -T 2>/dev/null || { mkdir -p /run/sshd && sshd -T 2>/dev/null; }) || true)"
if [ -z "$SSHCONF" ]; then aviso "Não consegui ler a configuração do SSH"; else
  val() { awk -v k="$1" '$1==k{print $2; exit}' <<<"$SSHCONF"; }
  [ "$(val permitrootlogin)" = "yes" ] && risco "Login direto como root permitido" || ok "Login direto como root bloqueado ($(val permitrootlogin))"
  if [ "$(val passwordauthentication)" = "yes" ]; then
    aviso "SSH aceita senha (mais seguro: entrar só com chave)"
  else ok "SSH só com chave (sem senha)"; fi
  [ "$(val permitemptypasswords)" = "yes" ] && risco "SSH aceita senha vazia" || ok "SSH não aceita senha vazia"
  info "Porta do SSH: $(val port)"
fi
CHAVES="$(find /home/*/.ssh /root/.ssh -name authorized_keys -exec cat {} + 2>/dev/null | grep -c . || true)"
info "Chaves SSH autorizadas: ${CHAVES:-0}"
FALHAS="$(journalctl -u ssh -u sshd --since '-7 days' --no-pager 2>/dev/null | grep -cE 'Failed password|Invalid user' || true)"
if [ "${FALHAS:-0}" -gt 50 ]; then aviso "$FALHAS tentativas de login SSH erradas em 7 dias"
else ok "Tentativas de login SSH erradas em 7 dias: ${FALHAS:-0}"; fi
journalctl -u ssh -u sshd --since '-7 days' --no-pager 2>/dev/null | grep -oE 'Failed password for (invalid user )?[^ ]+ from [0-9a-f.:]+' \
  | awk '{print $NF}' | sort | uniq -c | sort -rn | head -5 | sed 's/^/          tentativas vindas de: /'
command -v fail2ban-client >/dev/null && systemctl is-active -q fail2ban && ok "fail2ban ligado (bloqueia quem erra a senha muitas vezes)" \
  || info "fail2ban não instalado (opcional enquanto o SSH não estiver aberto na internet)"

# ---------------------------------------------------------------------------
secao "4. Usuários"
UID0="$(awk -F: '$3==0 && $1!="root"{print $1}' /etc/passwd)"
[ -n "$UID0" ] && risco "Outros usuários com poder de root: $UID0" || ok "Só o root tem UID 0"
SEMSENHA="$(awk -F: '$2==""{print $1}' /etc/shadow)"
[ -n "$SEMSENHA" ] && risco "Usuários SEM senha: $SEMSENHA" || ok "Nenhum usuário sem senha"
info "Quem pode usar sudo: $(getent group sudo | cut -d: -f4)"
info "Usuários que podem entrar: $(awk -F: '$7 !~ /(nologin|false|sync)$/ {printf "%s ", $1}' /etc/passwd)"

# ---------------------------------------------------------------------------
secao "5. Serviços do Radar"
for s in radar-contador nginx cloudflared; do
  systemctl is-active -q "$s" && ok "$s rodando" || risco "$s PARADO"
done
systemctl is-active -q radar-coleta.timer && ok "Coleta de hora em hora agendada" || risco "Coleta agendada DESLIGADA"
RES="$(systemctl show radar-coleta -p Result --value 2>/dev/null)"
[ "$RES" = success ] && ok "Última coleta terminou bem" || aviso "Última coleta: $RES (veja: journalctl -u radar-coleta -n 80)"
systemctl is-active -q radar-backup.timer && ok "Backup diário agendado" || risco "Backup diário DESLIGADO"
if ss -H -tlnp | grep -q ':8787 ' && ! ss -H -tlnp | grep ':8787 ' | grep -qv '127.0.0.1'; then ok "Contador escuta só dentro do servidor"
else aviso "Contador (porta 8787) não está só em 127.0.0.1"; fi
if ss -H -tlnp | grep ':8080 ' | grep -qv '127.0.0.1'; then aviso "nginx do Radar (8080) aberto além do 127.0.0.1"
else ok "Site (nginx) escuta só dentro do servidor"; fi
if [ -f /etc/cloudflared/config.yml ]; then
  info "Endereços publicados pelo túnel: $(grep -oP 'hostname:\s*\K\S+' /etc/cloudflared/config.yml | tr '\n' ' ')"
  grep -q 'http_status:404' /etc/cloudflared/config.yml && ok "Túnel recusa endereços desconhecidos" || aviso "Túnel sem regra final de recusa (http_status:404)"
fi
grep -qs '^CONTADOR_SENHA_HASH=pbkdf2' /etc/radar-contador.env && ok "Senha da aba Acessos guardada como hash forte (PBKDF2)" || risco "Login da aba Acessos sem senha configurada"

# ---------------------------------------------------------------------------
secao "6. Arquivos sensíveis (só o root deve ler)"
for f in /etc/radar.env /etc/radar-contador.env /etc/cloudflared/*.json /root/.cloudflared/cert.pem /etc/radar-backup.conf; do
  [ -e "$f" ] || continue
  m="$(stat -c '%a %U' "$f")"
  case "${m%% *}" in 600|400|640) ok "$f ($m)";; *) risco "$f pode ser lido por outros ($m). Corrija: sudo chmod 600 $f";; esac
done
for f in "$CASA/cert.pem" "$CASA/.cloudflared/cert.pem"; do
  [ -e "$f" ] && aviso "Cópia da chave da Cloudflare em $f: apague com: rm $f  (o servidor já usa a de /root)"
done
if grep -qsE '^ANTHROPIC_API_KEY=.+|^OPENAI_API_KEY=.+' /etc/radar.env; then info "Chave de IA configurada em /etc/radar.env"; fi

# ---------------------------------------------------------------------------
secao "7. Backup"
if [ -f /etc/radar-backup.conf ]; then
  . /etc/radar-backup.conf
  UB="$(ls -1d "$DESTINO"/20* 2>/dev/null | tail -1)"
  if [ -n "$UB" ]; then
    IDADE=$(( ( $(date +%s) - $(stat -c %Y "$UB") ) / 86400 ))
    [ "$IDADE" -le 2 ] && ok "Último backup: $(basename "$UB") em $DESTINO" || risco "Último backup tem $IDADE dias ($UB)"
  else risco "Nenhum backup encontrado em $DESTINO"; fi
  case "$DESTINO" in /var/backups*) aviso "Backups no mesmo SSD do sistema (se o SSD falhar, perde tudo). Melhor no HD.";; esac
  [ "$(stat -c %a "$DESTINO" 2>/dev/null)" = 700 ] && ok "Pasta de backup fechada para outros usuários" || aviso "Pasta de backup aberta: sudo chmod 700 $DESTINO"
else risco "Backup não configurado"; fi

# ---------------------------------------------------------------------------
secao "8. Outros"
SMART=""; command -v smartctl >/dev/null && for d in /dev/sd? /dev/nvme?n1; do [ -e "$d" ] && SMART+="$(basename "$d"): $(smartctl -H "$d" 2>/dev/null | grep -oE 'PASSED|FAILED|OK' | head -1) "; done
[ -n "$SMART" ] && info "Saúde dos discos: $SMART"
USO="$(df --output=pcent / | tail -1 | tr -dc 0-9)"
[ "${USO:-0}" -ge 85 ] && aviso "Disco do sistema com ${USO}% de uso" || ok "Disco do sistema com ${USO}% de uso"
info "Serviços que sobem com o sistema (para conferir se reconhece todos):"
systemctl list-units --type=service --state=running --no-legend --plain 2>/dev/null | awk '{print $1}' \
  | grep -vE '^(systemd-|dbus|cron|rsyslog|polkit|udisks|upower|accounts-daemon|ModemManager|NetworkManager|wpa_supplicant|avahi|cups|getty|user@|snapd|thermald|irqbalance|power-profiles|switcheroo|rtkit|colord|gdm|kerneloops|packagekit|fwupd|bolt|unattended|multipathd|networkd-dispatcher|serial-getty|console-setup|gnome|fprintd|openvpn|alsa|bluetooth|apport)' \
  | tr '\n' ' ' | fold -s -w 100 | sed 's/^/          /'; echo

printf '\nResumo: %s OK, %s atenção, %s risco.\n' "$OK" "$AVISO" "$RISCO"
echo "Resultado salvo em $SAIDA"
