# Radar de Notícias — app Android (Flutter)

App para celular que mostra as notícias do Radar. Não tem servidor próprio: lê o mesmo
`data/radar.json` que o site publica no GitHub Pages a cada coleta, então nada muda no backend.

## O que o app faz

- **Lista por categoria**: Fiscal, Reforma Tributária, ACBr, IA, Programação etc., com a contagem de cada uma
  (as categorias vêm do próprio `radar.json`, então uma categoria nova no site aparece sozinha no app).
- **Filtros como no site**: período (última hora, 24 horas, hoje, 7/30/90 dias, 1 ano, tudo),
  "Somente oficiais" (em Fiscal e Reforma considera o documento oficial, como o site) e busca sem acento.
- **Detalhes da notícia**: resumo, pontos principais, trecho da fonte, impacto no ERP e
  "Mesma notícia e atualizações" (outras fontes do mesmo assunto).
- **Abrir a notícia original** no navegador e copiar o link.
- **Favoritos** salvos só no aparelho. A notícia inteira fica guardada, então continua lá mesmo
  depois de sair da janela de 90 dias do site.
- **Funciona sem internet** com a última coleta baixada. Ao abrir (ou voltar para o app) ele confere
  `data/status.json` e só baixa tudo de novo se houver coleta mais nova. Puxe a lista para baixo para atualizar.

## Instalar no celular sem compilar

Cada PR ou push em `main` que mexe em `mobile/` roda o workflow **App Android (Flutter)**,
que testa o app e gera o APK. Em **Actions → execução → Artifacts**, baixe `radar-noticias-apk`,
descompacte e abra o `app-release.apk` no celular (é preciso permitir "instalar apps desconhecidos").

O APK é assinado com a chave de depuração do Flutter: serve para testar. Para publicar na Play Store,
será preciso criar uma chave própria (ver "Publicar" abaixo).

## Rodar e compilar no computador

Requisitos: [Flutter](https://docs.flutter.dev/get-started/install) 3.50 ou mais novo e o Android Studio (SDK do Android).

```bash
cd mobile
flutter pub get
flutter run                      # com o celular conectado (depuração USB) ou um emulador
flutter test                     # testes
flutter build apk --release      # gera build/app/outputs/flutter-apk/app-release.apk
```

### Endereço do site

Por padrão o app lê `https://llourencodev.github.io/Radar-de-noticias/`. Para usar outro endereço:

- no app: menu **⋮ → Endereço do Radar**; ou
- na compilação: `flutter build apk --dart-define=RADAR_URL=https://seu-endereco/`.

## Estrutura

| Arquivo | Função |
|---|---|
| `lib/models.dart` | Notícia, categoria e leitura do `radar.json` |
| `lib/radar_api.dart` | Download, cópia local e checagem de coleta nova |
| `lib/filters.dart` | Categoria, período, oficiais e busca (mesmas regras do `web/app.js`) |
| `lib/favorites.dart` | Favoritos no aparelho |
| `lib/screens/` | Tela principal (Notícias / Favoritos) e detalhes da notícia |
| `test/radar_test.dart` | Testes dos filtros, favoritos e da tela principal |

Identificador do app: `dev.llourenco.radar_noticias` (não pode mudar depois de publicar na Play Store).

## Próximos passos possíveis

- Notificações (push) de notícias novas via Firebase Cloud Messaging.
- Ícone e tela de abertura próprios.
- Chave de assinatura e publicação na Play Store.
