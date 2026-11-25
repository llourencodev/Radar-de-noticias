# Radar no seu servidor Ubuntu (com domínio próprio)

Um comando instala tudo no servidor e publica o Radar no seu domínio pela Cloudflare:

- **Site** em `https://radar.datavexsolucoes.com.br`, com coleta de hora em hora (minuto 7).
- **Contador de acessos** em `https://contador.datavexsolucoes.com.br`.
- **Atualizações automáticas** de segurança do Ubuntu (e do cloudflared), com reinício às 4h só quando precisar.
- **Firewall** (ufw): só o SSH entra. O site chega pelo túnel da Cloudflare, **sem abrir porta no roteador**.
- **Backup diário** (3h30) dos bancos e das configurações, de preferência no HD de 1 TB, guardando 30 dias.

O domínio raiz (`datavexsolucoes.com.br`) e o `www` ficam livres para o site da empresa.

```
Visitante ─► Cloudflare ─► túnel (cloudflared) ─► servidor Ubuntu
                                                   ├─ nginx 127.0.0.1:8080   → site do Radar
                                                   └─ contador 127.0.0.1:8787 → acessos
```

## Antes de começar

O domínio precisa estar **ativo** na Cloudflare: no painel da Cloudflare, o domínio aparece como *Active*
(isso acontece algumas horas depois de trocar os nameservers no Registro.br).

## 1. Instalar

No terminal do Ubuntu:

```bash
cd ~/radar-de-noticias
git pull
sudo bash servidor/instalar.sh
```

Durante a instalação ele pode pedir duas coisas:

1. **Usuário e senha do painel de acessos** (só se o contador ainda não tiver login).
2. **Um link da Cloudflare** (só na primeira vez): abra no computador ou no celular, entre na Cloudflare,
   clique em `datavexsolucoes.com.br` e em **Authorize**. O script continua sozinho.

Se achar o HD conectado mas sem uso, ele pergunta se pode montá-lo em `/mnt/hd` para os backups (nada é apagado).

No fim aparece **Pronto!** e o link. Abra `https://radar.datavexsolucoes.com.br` no navegador.
A primeira coleta roda em segundo plano e leva de 10 a 30 minutos; até lá o site mostra um aviso
(se a conexão SSH cair nesse meio-tempo, a coleta continua).

> O histórico começa do zero no servidor: as notícias recentes das fontes entram na primeira coleta.

## 2. Levar o link antigo para o novo

Depois de conferir o site novo, no GitHub:
**Settings › Secrets and variables › Actions › Variables › New repository variable**

- Nome: `SITE_URL`
- Valor: `https://radar.datavexsolucoes.com.br`

Depois rode **Actions › Coletar notícias e publicar o site › Run workflow**. A partir daí o GitHub para de
coletar e quem abrir `llourencodev.github.io/radar-de-noticias` vai direto para o endereço novo (mantendo a aba).
Para voltar atrás, é só apagar a variável e rodar o workflow de novo.

Troque também a variável `CONTADOR_URL` para `https://contador.datavexsolucoes.com.br`. Opcionalmente,
desligue o túnel antigo do Tailscale: `sudo tailscale funnel reset`.

## Login da Cloudflare

Se depois de clicar em **Authorize** a Cloudflare disser que o navegador **baixou o certificado**, o arquivo
`cert.pem` está na pasta **Downloads** do computador onde você abriu o link. Leve-o para o servidor e rode de novo:

```powershell
# no Windows (PowerShell), troque usuario@IP-do-servidor pelos seus
scp $HOME\Downloads\cert.pem usuario@IP-do-servidor:~/
```

```bash
# no servidor
cd ~/radar-de-noticias && git pull && sudo bash servidor/instalar.sh
```

O script acha o `cert.pem` na sua pasta pessoal e segue sem pedir login de novo.

## Como funciona

- O código fica em `/opt/radar/codigo` e se atualiza sozinho a partir do GitHub (ramo `main`) antes de cada
  coleta. Mudou `config/sources.json` no GitHub? Vale na próxima coleta.
- Antes de publicar, os testes rodam. Se algo falhar, **o site anterior continua no ar**.
- Configuração: `/etc/radar.env` (IA para resumos, contador). Depois de editar: `sudo systemctl start radar-coleta`.
- Banco de notícias: `/var/lib/radar/dados/radar.db`. Banco de acessos: `/var/lib/radar-contador/acessos.db`.

## Comandos úteis

| Para | Comando |
|---|---|
| Coletar agora | `sudo systemctl start radar-coleta` |
| Ver a última coleta | `journalctl -u radar-coleta -n 80` |
| Acompanhar uma coleta | `journalctl -fu radar-coleta` |
| Próximas coletas e backups | `systemctl list-timers 'radar-*'` |
| Ver o túnel | `systemctl status cloudflared` |
| Fazer backup agora | `sudo radar-backup` |
| Onde estão os backups | `cat /etc/radar-backup.conf` |
| Firewall | `sudo ufw status` |
| Reinstalar/ajustar (pode rodar quantas vezes quiser) | `cd ~/radar-de-noticias && git pull && sudo bash servidor/instalar.sh` |

## Backup no HD

Os backups ficam em `<HD>/backup-radar/AAAA-MM-DD/` (`acessos.db.gz`, `radar.db.gz` e `configuracao.tar.gz`).
Se o HD não estiver montado no horário, o backup não é feito (para não lotar o SSD) e o erro aparece em
`journalctl -u radar-backup`.

Para trocar a pasta: edite `DESTINO=` e `MONTAGEM=` em `/etc/radar-backup.conf` (MONTAGEM é onde o HD está montado).

Para restaurar o banco de acessos de um dia:

```bash
sudo systemctl stop radar-contador
gunzip -c /mnt/hd/backup-radar/2026-11-24/acessos.db.gz | sudo tee /var/lib/radar-contador/acessos.db >/dev/null
sudo systemctl start radar-contador
```

## Só o contador (site no GitHub Pages)

`sudo bash servidor/instalar.sh --hibrido` instala só o contador, o túnel, o firewall, as atualizações e o backup.
