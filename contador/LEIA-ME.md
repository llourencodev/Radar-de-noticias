# Contador de acessos próprio

Um serviço pequeno que roda no seu servidor Ubuntu e conta as visitas do Radar publicado no GitHub Pages.
Os números aparecem na aba **Acessos** do próprio Radar, que só aparece depois de entrar com usuário e senha.

- Só Python 3 (já vem no Ubuntu); nenhuma biblioteca extra.
- As visitas ficam num arquivo SQLite no servidor (`/var/lib/radar-contador/acessos.db`).
- Sem cookies e sem guardar IP: cada visitante vira um código embaralhado que muda todo dia (LGPD).
- Seus acessos com login não entram na conta.
- Se o servidor cair, o site continua normal; só as visitas desse intervalo deixam de ser contadas.

```
Visitante ──► Radar (GitHub Pages) ──► https://contador.seudominio ──► túnel ──► servidor Ubuntu (127.0.0.1:8787)
```

O serviço escuta só dentro do servidor. Quem leva as visitas até ele é um túnel (Cloudflare ou Tailscale),
então **não é preciso abrir porta no roteador**.

## 1. Instalar no servidor

No terminal do Ubuntu:

```bash
git clone https://github.com/llourencodev/radar-de-noticias.git
cd radar-de-noticias
sudo bash contador/instalar.sh
```

Na primeira vez ele pede o **usuário e a senha** do painel (mínimo 10 caracteres). No fim deve aparecer
"Contador no ar". Para atualizar depois: `git pull && sudo bash contador/instalar.sh`.

## 2. Publicar com um túnel (escolha uma opção)

### Opção A: Cloudflare Tunnel (se você tem um domínio)

O domínio precisa estar na Cloudflare (plano grátis).

1. Entre em https://one.dash.cloudflare.com › **Networks › Tunnels › Create a tunnel** › **Cloudflared**, nome `radar-contador`.
2. Escolha **Debian/Ubuntu**, copie o comando de instalação que aparece e rode no servidor.
3. Em **Public hostname**: subdomínio `contador`, seu domínio, tipo **HTTP**, URL `localhost:8787`. Salve.
4. Teste no navegador: `https://contador.seudominio.com.br/saude` deve mostrar `ok`.

Com a Cloudflare, o painel também mostra o país exato de cada visita.

### Opção B: Tailscale Funnel (sem domínio, grátis)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up            # abre um link para entrar na sua conta Tailscale
sudo tailscale funnel --bg 8787
```

Na primeira vez o comando do funnel mostra um link para liberar o recurso na sua conta; abra, aceite e
rode o comando de novo. Ele mostra o endereço fixo, algo como `https://servidor.tail1234.ts.net`.
Teste `https://servidor.tail1234.ts.net/saude` no navegador.

Sem a Cloudflare, o país é estimado pelo fuso horário do navegador.

## 3. Ligar o Radar ao contador

No GitHub: **Settings › Secrets and variables › Actions › Variables › New repository variable**

- Nome: `CONTADOR_URL`
- Valor: o endereço do túnel, só a parte `https://...` sem barra no fim (ex.: `https://contador.seudominio.com.br`)

Depois rode **Actions › Coletar notícias e publicar o site › Run workflow** (ou espere a próxima coleta).

## 4. Ver os acessos

No Radar, clique em **Entrar** (embaixo do seu nome, no menu lateral) ou abra `.../#/acessos`.
Depois do login, a aba **Acessos** aparece no menu daquele navegador por 30 dias.

O painel mostra: visitantes agora, hoje, ontem e no período (hoje, 7, 30, 90 dias, 1 ano); visitantes por dia
(ou páginas por hora, hoje); abas mais abertas; de onde vieram (Google, WhatsApp, LinkedIn...);
celular, computador ou tablet; país; navegador e sistema.

## Comandos úteis

| Para | Comando |
|---|---|
| Trocar usuário/senha (derruba quem estava logado) | `sudo python3 /opt/radar-contador/servidor.py --definir-senha && sudo systemctl restart radar-contador` |
| Ver se está rodando | `systemctl status radar-contador` |
| Ver erros | `journalctl -u radar-contador -n 50` |
| Cópia de segurança das visitas | `sudo cp /var/lib/radar-contador/acessos.db ~/acessos-backup.db` |
| Mudar opções (dias guardados, site permitido) | editar `/etc/radar-contador.env` e `sudo systemctl restart radar-contador` |

## Segurança

- A senha fica só como hash (PBKDF2, 600 mil rodadas) em `/etc/radar-contador.env`, legível só pelo root.
- Depois de 5 senhas erradas, o mesmo IP fica bloqueado por 15 minutos.
- Só o endereço do Radar (`CONTADOR_ORIGENS`) pode enviar visitas e abrir o painel.
- O serviço roda com usuário próprio do systemd, sem acesso às suas pastas, e com no máximo 200 MB de memória.
