# Radar Inteligente de Notícias

Central de notícias com coleta real e atualização automática, organizada em abas: Fiscal e Tributário, Reforma Tributária, Inteligência Artificial, Programação, Tecnologia, Mercado de TI e Todas as notícias.

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

Opções úteis: `filter: "keywords"` aceita só itens cujo título tenha palavras-chave das abas (para fontes generalistas); `order: "last"` serve para listas em que o mais recente fica no fim; `date_from_text: true` lê a data no texto do ato normativo; `days` e `lang` (`pt` ou `en`) servem para as buscas.

Para conferir todas as fontes sem gravar nada: `.venv\Scripts\python.exe verificar_fontes.py`.

As palavras-chave de cada aba ficam em `config/categories.json` e o glossário de termos técnicos fica em `config/glossary.json`.

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
web/                     interface (HTML, CSS e JavaScript, sem build); static-api.js atende a versão online
data/radar.db            banco SQLite (criado na 1ª execução)
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
