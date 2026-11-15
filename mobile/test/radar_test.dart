import 'dart:convert';

import 'dart:ui' show Size;

import 'package:flutter/widgets.dart' show Scrollable;

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:radar_noticias/app_state.dart';
import 'package:radar_noticias/favorites.dart';
import 'package:radar_noticias/filters.dart';
import 'package:radar_noticias/main.dart';
import 'package:radar_noticias/models.dart';
import 'package:radar_noticias/radar_api.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Amostra no mesmo formato de data/radar.json (app/static_site.py).
Map<String, dynamic> sample() => {
      'generated_at': '2026-11-15T09:07:00Z',
      'meta': {
        'categories': [
          {'slug': 'fiscal', 'name': 'Fiscal e Tributário', 'color': '#0f766e', 'icon': 'receipt'},
          {'slug': 'reforma', 'name': 'Reforma Tributária', 'color': '#b45309', 'icon': 'scale'},
          {'slug': 'ia', 'name': 'Inteligência Artificial', 'color': '#7c3aed', 'icon': 'sparkles'},
        ],
        'stages': {'norma_publicada': 'Norma publicada'},
      },
      'status': {},
      'articles': [
        {
          'id': 1, 'title': 'Receita publica nova Instrução Normativa do IBS', 'url': 'https://gov.br/a',
          'outlet': 'Receita Federal', 'image_url': 'https://gov.br/img.jpg', 'date_confirmed': 1, 'published_at': '2026-11-15T08:00:00Z', 'date_precision': 'datetime',
          'categories': ['fiscal', 'reforma'], 'primary_category': 'reforma', 'official': 1, 'doc_type': 'oficial',
          'summary': 'A Receita Federal publicou a Instrução Normativa que regulamenta a fase de testes do IBS e da CBS em 2026, com novas regras de destaque nos documentos fiscais.', 'key_points': ['Ponto 1'], 'legal_stage': 'norma_publicada', 'erp_impact': 1, 'erp_docs': ['NF-e', 'IBS/CBS'], 'erp_reason': 'novos campos no leiaute', 'relevance': 80, 'is_duplicate': 0, 'group_id': 10,
        },
        {
          'id': 2, 'title': 'Mesma IN repercutida', 'url': 'https://jornal.com/b', 'outlet': 'Jornal',
          'published_at': '2026-11-15T09:00:00Z', 'categories': ['fiscal'], 'official': 0, 'is_duplicate': 1, 'group_id': 10,
        },
        {
          'id': 3, 'title': 'Novo modelo de IA lançado', 'url': 'https://tech.com/c', 'outlet': 'Tech',
          'published_at': '2026-11-01T12:00:00Z', 'categories': ['ia'], 'primary_category': 'ia', 'official': 0, 'is_duplicate': 0,
        },
        {
          'id': 4, 'title': 'Comunicado sem hora', 'url': 'https://gov.br/d', 'outlet': 'SEFAZ',
          'published_at': '2026-11-14', 'date_precision': 'date', 'categories': ['fiscal'], 'official': 1, 'is_duplicate': 0,
        },
      ],
    };

void main() {
  final data = RadarData.fromJson(sample());
  final now = DateTime.utc(2026, 11, 15, 12);

  test('lê o radar.json e separa as duplicadas', () {
    expect(data.all.length, 4);
    expect(data.list.map((a) => a.id), [1, 4, 3]);
    expect(data.categories.first.name, 'Fiscal e Tributário');
    expect(data.related(data.list.first).single.id, 2);
    expect(data.list.first.isOfficial, isTrue);
  });

  test('filtra por categoria, período, oficiais e busca sem acento', () {
    expect(const Filters(category: 'ia').apply(data.list, now: now).map((a) => a.id), [3]);
    expect(const Filters(period: '7').apply(data.list, now: now).map((a) => a.id), [1, 4]);
    expect(const Filters(period: '24h').apply(data.list, now: now).map((a) => a.id), [1]);
    expect(const Filters(onlyOfficial: true).apply(data.list, now: now).map((a) => a.id), [1, 4]);
    // em Fiscal/Reforma, "Somente oficiais" usa o tipo de documento, como no site
    expect(const Filters(view: 'fiscal', onlyOfficial: true).apply(data.list, now: now).map((a) => a.id), [1]);
    expect(const Filters(query: 'normativas').apply(data.list, now: now).map((a) => a.id), [1]);
    expect(const Filters(query: 'modelo ia').apply(data.list, now: now).map((a) => a.id), [3]);
  });

  test('sem rede: tenta de novo e explica o erro', () async {
    var calls = 0;
    final api = RadarApi(client: MockClient((req) async {
      calls++;
      throw http.ClientException('SocketException: Failed host lookup');
    }));
    await expectLater(api.remoteGeneratedAt(), throwsA(isA<RadarException>()
        .having((e) => e.message, 'mensagem', contains('Sem conexão com llourencodev.github.io'))));
    expect(calls, 2);
  });

  test('normaliza o endereço do site', () {
    expect(RadarApi.normalizeUrl('usuario.github.io/radar'), 'https://usuario.github.io/radar/');
    expect(RadarApi.normalizeUrl('https://x.io/r/index.html'), 'https://x.io/r/');
  });

  test('favoritos sobrevivem a reiniciar o app', () async {
    SharedPreferences.setMockInitialValues({});
    final f = Favorites();
    await f.toggle(data.list.last);
    final again = Favorites();
    await again.load();
    expect(again.items.single.title, 'Novo modelo de IA lançado');
    await again.toggle(again.items.single);
    expect(again.length, 0);
  });

  testWidgets('painel, menu lateral, categoria e favoritos como no site', (tester) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.6;
    addTearDown(tester.view.reset);
    final client = MockClient((req) async {
      final body = req.url.path.endsWith('status.json') ? {'generated_at': '2026-11-15T09:07:00Z'} : sample();
      return http.Response.bytes(utf8.encode(jsonEncode(body)), 200, headers: {'content-type': 'application/json'});
    });
    final favorites = Favorites();
    await tester.runAsync(() async {
      await tester.pumpWidget(RadarApp(state: AppState(api: RadarApi(client: client), favorites: favorites)));
      // espera a leitura (feita fora da tela) terminar
      for (var i = 0; i < 50 && find.text('Painel de inteligência').evaluate().isEmpty; i++) {
        await Future<void>.delayed(const Duration(milliseconds: 50));
        await tester.pump();
      }
    });
    expect(find.text('Painel de inteligência'), findsOneWidget);
    expect(find.text('Notícias coletadas'), findsOneWidget);

    // menu lateral: categoria Fiscal
    await tester.tap(find.byTooltip('Abrir menu'));
    await tester.pumpAndSettle();
    expect(find.text('Notas técnicas / ERP'), findsOneWidget);
    await tester.tap(find.text('Fiscal e Tributário').last);
    await tester.pumpAndSettle();
    expect(find.textContaining('2 notícia(s)'), findsOneWidget);
    expect(find.text('Novo modelo de IA lançado'), findsNothing);

    await tester.ensureVisible(find.byTooltip('Salvar nos favoritos').first);
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Salvar nos favoritos').first);
    await tester.pump();
    expect(favorites.length, 1);

    // detalhes da notícia
    await tester.ensureVisible(find.text('Detalhes e impactos').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Detalhes e impactos').first);
    await tester.pumpAndSettle();
    expect(find.text('Resumo'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Abrir publicação original'), 300, scrollable: find.byType(Scrollable).last);
    expect(find.text('Abrir publicação original'), findsOneWidget);
  });
}
