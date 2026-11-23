#!/usr/bin/env bash
# Instala (ou atualiza) o contador de acessos do Radar num Ubuntu. Uso: sudo bash contador/instalar.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Rode com sudo: sudo bash contador/instalar.sh"; exit 1; }
cd "$(dirname "$0")"

command -v python3 >/dev/null || { apt-get update && apt-get install -y python3; }
python3 -c 'import sys; assert sys.version_info >= (3, 9)' || { echo "Precisa do Python 3.9 ou mais novo"; exit 1; }

install -d -m 755 /opt/radar-contador
install -m 644 servidor.py /opt/radar-contador/servidor.py
install -m 644 radar-contador.service /etc/systemd/system/radar-contador.service

if [ ! -f /etc/radar-contador.env ]; then
  install -m 600 contador.env.exemplo /etc/radar-contador.env
  echo "Configuração criada em /etc/radar-contador.env"
fi

# login do painel: pergunta na primeira instalação (para trocar depois: --definir-senha)
if ! grep -q '^CONTADOR_SENHA_HASH=.\+' /etc/radar-contador.env; then
  echo
  echo "Crie o login que vai abrir a aba Acessos do Radar:"
  CONTADOR_ENV=/etc/radar-contador.env python3 /opt/radar-contador/servidor.py --definir-senha
fi

systemctl daemon-reload
systemctl enable radar-contador >/dev/null 2>&1
systemctl restart radar-contador
sleep 1
if curl -fsS "http://127.0.0.1:$(grep -oP '^CONTADOR_PORTA=\K\d+' /etc/radar-contador.env || echo 8787)/saude" >/dev/null; then
  echo "Contador no ar (só dentro do servidor, porta $(grep -oP '^CONTADOR_PORTA=\K\d+' /etc/radar-contador.env || echo 8787))."
else
  echo "O serviço não respondeu. Veja o erro com: journalctl -u radar-contador -n 50"; exit 1
fi
echo
echo "Próximo passo: publicar o contador na internet com o túnel (veja contador/LEIA-ME.md)."
