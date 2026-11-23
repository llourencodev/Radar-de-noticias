# Radar Inteligente de Notícias

Central de notícias com coleta real e atualização automática, organizada em abas: Fiscal e Tributário, Reforma Tributária, Inteligência Artificial, Programação, Tecnologia, Mercado de TI e Todas as notícias, além da aba **Eventos de tecnologia**.

## Como executar no Windows

1. Dê dois cliques em **`iniciar.bat`** dentro da pasta do projeto (`Documentos\Projetos\Radar-Inteligente-Noticias`).
2. Na primeira vez, o script cria o ambiente Python (`.venv`) e instala as dependências. Isso leva cerca de 1 minuto.
3. O navegador abre em **http://localhost:8000**. A primeira coleta começa sozinha e leva de 5 a 10 minutos, porque passa por 62 fontes respeitando o limite de acesso de cada site. As notícias vão aparecendo durante esse tempo.
4. Para encerrar, feche a janela preta (ou pressione Ctrl+C nela).

Requisito: Python 3.11 ou mais recente (o seu PC tem o 3.14). Se o Python não estiver instalado, baixe em https://www.python.org/downloads/ e marque “Add python.exe to PATH”.

Para abrir no celular na mesma rede Wi-Fi, mude `RADAR_HOST=0.0.0.0` no arquivo `.env` e acesse `http://IP-DO-PC:8000`.

## Atualização automática

Configure no arquivo `.env`, criado na primeira execução a partir do `.env.example`:

| Variável | Padrão | O que faz |
| --- | --- | --- |
| `RADAR_INTERVAL_MIN` | 60 | Minutos entre coletas de cada fonte |
| `RADAR_AUTO_UPDATE` | true | `false` desliga a coleta automática (fica só o botão Atualizar) |
| `RADAR_COLLECT_ON_START` | true | Coleta ao abrir o programa |
| `RADAR_MAX_AGE_DAYS` | 30 | Notícias mais antigas não entram como novidade |
| `RADAR_FISCAL_MAX_AGE_DAYS` | 120 | O mesmo para as abas fiscais |

Cada fonte também pode ter seu próprio intervalo (`interval_min` em `config/sources.json`). Depois de alterar o `.env`, feche e abra o programa de novo.

Como a coleta evita trabalho repetido:

- Feeds são baixados com ETag e Last-Modified; se nada mudou, o site responde “inalterado” e nada é baixado.
- Links já conhecidos são descartados antes de qualquer processamento.
- A página original é lida apenas uma vez, só para notícias novas.
- Uma fonte com 3 falhas seguidas passa a ser consultada com intervalo maior, até 24 horas, e aparece em vermelho na tela **Fontes e coleta**.

## Como adicionar novas fontes

**Pela tela:** abra **Fontes e coleta** e use **Adicionar fonte**. A fonte é testada antes de ser salva. Os tipos são:

- **RSS/Atom:** informe a URL do feed.
- **Busca (Google Notícias ou Bing Notícias):** informe o termo, por exemplo `ICMS Minas Gerais SEFAZ`.
- **Página sem RSS:** informe a URL da página de notícias e uma expressão regular que os links das publicações atendem, por exemplo `/noticias/20\d\d/`.

**Pelo arquivo:** acrescente um item em `config/sources.json` e reinicie:

```json
{"id": "sefaz-mg", "name": "SEFAZ-MG", "type": "html", "url": "https://...", "category": "fiscal",
 "official": true, "priority": 2, "options": {"link_pattern": "/noticias/[^/]+$", "limit": 15}}
```

Opções úteis: `filter: "keywords"` aceita só itens cujo título tenha palavras-chave das abas (para fontes generalistas); `order: "last"` serve para listas em que o mais recente fica no fim; `date_from_text: true` lê a data no texto do ato normativo; `days` e `lang` (`pt` ou `en`) servem para as buscas; `country` (`"BR"` para fontes brasileiras, outro código para as estrangeiras) alimenta o filtro **Notícias Brasil**.

**Filtro Notícias Brasil:** disponível em todas as categorias, mostra só notícias brasileiras e continua marcado ao trocar de aba. Uma notícia é brasileira quando o site do veículo termina em `.br`; senão vale o `country` da fonte; nas buscas (Google/Bing), sem país definido, conta o texto em português (sites de Portugal e de outros países lusófonos ficam de fora).

Para conferir todas as fontes sem gravar nada: `.venv\Scripts\python.exe verificar_fontes.py`.

As palavras-chave de cada aba ficam em `config/categories.json` e o glossário de termos técnicos fica em `config/glossary.json`.

## Eventos de tecnologia

A aba **Eventos de tecnologia** reúne workshops, meetups, conferências, feiras e webinars de IA, programação, cibersegurança, dados/cloud/DevOps, IA no comércio e varejo, agro/AgTech, indústria 4.0 e inovação, online e presenciais.

- **Fontes reais** (em `config/events.json`): Sympla (tecnologia e negócios em SP, RJ e BH), Meetup (buscas por tecnologia, IA, programação, segurança e dados em SP, Rio, BH, Curitiba, Porto Alegre, Recife, Florianópolis, Brasília e Campinas, e a agenda .ics de grupos), Luma (São Paulo), dev.events (Brasil, meetups e feed mundial) e confs.tech (conferências internacionais).
- **O que entra:** eventos no Brasil (presenciais ou híbridos) e eventos online de qualquer país. Presenciais no exterior ficam de fora. Fontes generalistas só trazem eventos com algum tema de tecnologia; festas, shows e similares são descartados.
- **Cada evento mostra** nome, data e hora, formato (online, presencial, híbrido), cidade/UF e local, organizador, temas e o link da página do evento.
- **Filtros:** tema, período (7 dias, 30 dias, 3 meses, todos), formato, estado, "Eventos Brasil" (no Brasil ou online em português), "Grátis", "Com certificado" e busca por texto.
- **Grátis e Com certificado:** um evento é marcado como grátis quando a fonte informa preço zero (Luma, Meetup sem taxa, schema.org `offers`/`isAccessibleForFree`), quando vem da seção Grátis da Sympla (`mark_free`) ou quando o título/descrição diz "gratuito", "entrada franca" etc. "Com certificado" vale quando a descrição menciona emissão de certificado (certificado de participação/conclusão; "certificado digital" não conta). Para isso, nas fontes com `"details": true`, a página de cada evento novo é aberta uma vez (até 60 por execução). Eventos cuja fonte não informa preço ficam fora do filtro "Grátis".
- **Eventos encerrados somem sozinhos**, tanto na coleta quanto no navegador. Cursos longos que já começaram também não entram.
- A coleta de eventos roda a cada 6 horas (`interval_min` em `config/events.json`), junto com a coleta de notícias. Uma fonte que falha não impede a publicação do site; a situação de cada fonte aparece em **Fontes e coleta**.
- Para adicionar uma agenda: inclua um item em `config/events.json` com `type` `page` (página com dados estruturados schema.org ou JSON embutido), `ical` (agenda .ics) ou `devevents`. Para conferir todas as fontes sem gravar nada: `.venv\Scripts\python.exe verificar_eventos.py`.
- O Eventbrite foi testado e bloqueia leitura automática (erro 405), por isso não está na lista.

## Inteligência artificial

Funciona sem nenhuma chave paga. A classificação, o estágio das normas fiscais, a detecção de duplicidade e de atualizações, o glossário e os impactos sinalizados são feitos por regras locais. O resumo é extrativo: usa frases da própria fonte, sem acrescentar nada.

Para ligar uma IA mais tarde, sem mudar o código, edite o `.env`:

```
LLM_PROVIDER=anthropic          # ou openai, ou ollama (local e gratuito)
ANTHROPIC_API_KEY=sua-chave
```

A IA passa a gerar o resumo em português (inclusive de fontes em inglês), os pontos principais e os impactos para empresas e ERP das notícias novas. Ela também processa as notícias dos últimos 7 dias. `LLM_MAX_PER_RUN` limita o custo por coleta.

## Versão online gratuita (GitHub Pages)

O Radar também roda sem o seu PC ligado, de graça, no GitHub:

- O **GitHub Actions** executa `gerar_site.py` a cada hora: coleta as fontes vencidas, processa as notícias e gera um site estático na pasta `site/`.
- O site é publicado no **GitHub Pages** com a mesma interface. Busca, filtros, painel e detalhes funcionam no navegador, a partir de `data/radar.json`.
- O banco SQLite fica guardado no cache do Actions entre uma execução e outra (duplicidade, histórico e ETags continuam funcionando).
- Para coletar na hora: aba **Actions** › **Coletar notícias e publicar o site** › **Run workflow**. O botão **Atualizar** do site só busca a publicação mais recente.
- Para adicionar ou desativar fontes, edite `config/sources.json` no GitHub; o site é refeito sozinho em alguns minutos.

Configuração única no repositório: **Settings › Pages › Source: GitHub Actions**.

IA opcional, sem expor a chave: em **Settings › Secrets and variables › Actions**, crie o secret `ANTHROPIC_API_KEY` e a variável `LLM_PROVIDER` = `anthropic`. O arquivo `.env` nunca vai para o GitHub.

### Contador de acessos

**Contador próprio (no seu servidor):** a pasta `contador/` tem um serviço pequeno que roda num servidor Ubuntu e guarda as visitas num SQLite. Os números aparecem na aba **Acessos** do Radar, que só aparece para quem entra com usuário e senha (link **Entrar** no menu lateral). Sem cookies e sem guardar IP. Passo a passo em [contador/LEIA-ME.md](contador/LEIA-ME.md); depois de instalar, crie no GitHub a variável `CONTADOR_URL` com o endereço do contador.

**GoatCounter (reserva):** o site também conta com o [GoatCounter](https://www.goatcounter.com), conta `leandro` (painel em https://leandro.goatcounter.com). Os dois funcionam juntos; para desligar o GoatCounter, troque o valor padrão `'leandro'` em `.github/workflows/radar.yml` por `''` (ou crie a variável `GOATCOUNTER_CODE` com outro código).

Só são contados acessos a partir da ativação: o GitHub Pages não guarda registro de visitas. A versão local (`iniciar.bat`) não envia nada.

Para gerar o site localmente sem coletar: `.venv\Scripts\python.exe gerar_site.py --sem-coleta` (resultado em `site/`).

## Estrutura

```
iniciar.bat              inicia tudo (cria o ambiente na 1ª vez)
run.py                   servidor web + agendador
gerar_site.py            coleta + site estático (GitHub Actions/Pages)
.github/workflows/       agendamento da coleta e publicação no GitHub Pages
verificar_fontes.py      teste rápido de todas as fontes
config/                  sources.json, categories.json, glossary.json
app/main.py              API (documentação em http://localhost:8000/docs)
app/db.py                SQLite, busca FTS5, consultas
app/scheduler.py         ciclo de coleta, histórico, falhas
app/collectors/          rss.py, html.py, search.py (Google/Bing Notícias)
app/processing/          classificação, status legal, duplicidade, resumo, leitura de página, IA opcional
web/                     interface (HTML, CSS e JavaScript, sem build); static-api.js atende a versão online; contador.js conta os acessos (contador próprio e GoatCounter)
data/radar.db            banco SQLite (criado na 1ª execução)
contador/                contador de acessos próprio (servidor Ubuntu), ver contador/LEIA-ME.md
tests/                   testes: .venv\Scripts\python.exe -m unittest discover tests
```

## Regras de qualidade aplicadas

- Título, data, imagem e link vêm somente da fonte. Quando a fonte não traz imagem, a interface mostra um bloco com a cor da categoria e o aviso “Sem imagem da fonte”.
- A data de publicação e a data de coleta ficam em campos separados. Sem data confirmada, aparece “Data não confirmada”.
- Itens sem título, sem link ou sem fonte identificável são descartados.
- Na área fiscal, cada item é marcado como publicação oficial ou notícia jornalística e recebe um estágio. Na dúvida, o estágio escolhido é o menos avançado. “Norma em vigor” só é atribuído com base em fonte oficial.
- **ACBr**: aba própria com as alterações publicadas no SVN oficial do Projeto ACBr (a mensagem de cada commit vira o título, ex.: “ACBrNFe.Classes: …”) e notícias que citam o ACBr, ACBrLib, ACBrMonitor e demais componentes. Os commits ficam só nessa aba, para não lotar as abas fiscais.
- **Notas técnicas / ERP**: notícias que exigem ajuste ou implementação em sistemas (notas técnicas de NF-e, NFC-e, NFS-e, CT-e, MDF-e; leiautes, schemas e regras de validação; Ajustes SINIEF e Atos COTEPE; guias e PVAs do SPED/EFD; IBS/CBS e cClassTrib nos documentos fiscais) recebem o selo “Ajuste em ERP” com os documentos afetados. Ficam reunidas na aba *Notas técnicas / ERP* (com filtro por documento) e podem ser filtradas em qualquer aba pela opção “Exige ajuste em ERP”. As regras estão em `app/processing/erp.py`; ao mudá-las, aumente `RULES_VERSION` para que as notícias já salvas sejam reavaliadas.
- Resumos, pontos e impactos são identificados como interpretação automática; colunas de opinião são sinalizadas.
- Uma fonte com falha não interrompe as outras.
