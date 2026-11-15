# Radar de Notícias — app Android (Flutter)

App para celular que mostra as notícias do Radar. Não tem servidor próprio: lê o mesmo
`data/radar.json` que o site publica no GitHub Pages a cada coleta, então nada muda no backend.

## O que o app faz

O app reproduz o site no celular, com as mesmas cores (tema claro e escuro), o mesmo menu e as mesmas telas:

- **Painel de inteligência**: números da coleta, Mais relevantes, Oficiais em destaque, Notas técnicas/ERP,
  Últimas fiscais, Novidades de IA e Programação.
- **Menu lateral** com as categorias e a contagem de cada uma, Notas técnicas / ERP e Todas as notícias
  (as categorias vêm do próprio `radar.json`, então uma categoria nova no site aparece sozinha no app).
- **Cartões com a imagem da notícia**, os mesmos selos (categoria, publicação oficial, estágio da norma,
  ajuste em ERP, atualização...) e o quadro "sem imagem" do site quando a fonte não tem foto.
- **Os mesmos filtros**: período, categoria, fonte, relevância, somente oficiais, estágio da norma,
  documento (ERP) e ordenação, além da busca sem acento.
- **Detalhes da notícia** como a janela do site: resumo, pontos principais, impactos, normas citadas,
  termos técnicos e "Mesma notícia e atualizações".
- **Favoritos** salvos só no aparelho (a notícia inteira, para não sumir depois de 90 dias).
- **Funciona sem internet** com a última coleta baixada. Ao abrir (ou voltar para o app) ele confere
  `data/status.json` e só baixa tudo de novo se houver coleta mais nova. Puxe a tela para baixo para atualizar.

## Instalar no celular sem compilar

Cada PR ou push em `main` que mexe em `mobile/` roda o workflow **App Android (Flutter)**,
que testa o app e gera o APK. Em **Actions → execução → Artifacts**, baixe `radar-noticias-apk`,
descompacte e abra o `app-release.apk` no celular (é preciso permitir "instalar apps desconhecidos").

O APK é assinado com a chave de depuração do Flutter: serve para testar. Para publicar na Play Store,
será preciso criar uma chave própria (ver "Publicar" abaixo).

## Testar no PC (Windows), passo a passo

O jeito mais prático é o **VS Code** com o emulador do **Android Studio**. (O Visual Studio “grande”
não abre projetos Flutter; ele serve para .NET/MAUI.)

1. Instale o [Android Studio](https://developer.android.com/studio). Na primeira abertura, deixe ele baixar o
   *Android SDK*. Depois, em **More Actions → Virtual Device Manager**, crie um emulador (ex.: Pixel 8, Android 15).
2. Instale o Flutter: no PowerShell, `winget install --id=Google.Flutter -e` (ou baixe o zip em docs.flutter.dev e
   coloque a pasta `flutter\bin` no PATH). Feche e abra o terminal e rode `flutter doctor --android-licenses`
   (responda `y`) e `flutter doctor` até tudo ficar verde no Android.
3. Instale o [VS Code](https://code.visualstudio.com/) e a extensão **Flutter** (o VS Code sugere ao abrir a pasta).
4. No VS Code: **File → Open Folder… → `mobile`**. Na barra de baixo, escolha o emulador (ou o celular ligado
   no USB com “Depuração USB” ativa) e aperte **F5**.

Com o app rodando pelo VS Code, qualquer erro aparece completo na aba **Debug Console**, e salvar um arquivo
atualiza o app na hora (*hot reload*).

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
| `lib/theme.dart` | Cores do `web/styles.css` (claro e escuro) |
| `lib/widgets/radar_widgets.dart` | Cartão, item de lista, selos e imagem, como no site |
| `lib/screens/` | Menu e busca, Painel, listas com filtros, Favoritos e detalhes da notícia |
| `test/radar_test.dart` | Testes dos filtros, favoritos e da tela principal |

Identificador do app: `dev.llourenco.radar_noticias` (não pode mudar depois de publicar na Play Store).

## Próximos passos possíveis

- Notificações (push) de notícias novas via Firebase Cloud Messaging.
- Ícone e tela de abertura próprios.
- Chave de assinatura e publicação na Play Store.
