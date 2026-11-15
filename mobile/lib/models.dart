/// Modelos dos dados publicados pelo Radar em `data/radar.json`
/// (gerado por app/static_site.py a cada coleta no GitHub Actions).
library;

import 'package:material_ui/material_ui.dart';

class Category {
  final String slug;
  final String name;
  final Color color;

  /// Nome do ícone no site (receipt, scale, acbr-logo...).
  final String icon;

  const Category({required this.slug, required this.name, required this.color, this.icon = 'layers'});

  factory Category.fromJson(Map<String, dynamic> j) => Category(
        slug: j['slug'] as String,
        name: (j['name'] as String?) ?? j['slug'] as String,
        color: parseHexColor(j['color'] as String?) ?? const Color(0xFF64748B),
        icon: (j['icon'] as String?) ?? 'layers',
      );
}

Color? parseHexColor(String? hex) {
  if (hex == null) return null;
  final h = hex.replaceFirst('#', '');
  if (h.length != 6) return null;
  final v = int.tryParse(h, radix: 16);
  return v == null ? null : Color(0xFF000000 | v);
}

class Term {
  final String term;
  final String explanation;
  const Term(this.term, this.explanation);
}

class Article {
  final int id;
  final String title;
  final String url;
  final String? outlet;
  final String? sourceName;
  final String? imageUrl;

  /// ISO 8601 em UTC ("2026-11-15T10:00:00Z") ou só a data ("2026-11-15").
  final String? publishedAt;
  final String? datePrecision;
  final bool dateConfirmed;
  final String? collectedAt;
  final String? excerpt;
  final String? summary;
  final String? summaryLang;
  final String? provider;
  final List<String> keyPoints;
  final List<String> impacts;
  final List<String> legalRefs;
  final List<Term> terms;
  final List<String> categories;
  final String? primaryCategory;
  final double relevance;
  final bool official;
  final String? docType;
  final String? legalStage;
  final String? stageNote;
  final bool legislative;
  final String? nature;
  final String? validationStatus;
  final bool viaAggregator;
  final bool isDuplicate;
  final bool isUpdate;
  final int? groupId;
  final int groupSources;
  final bool erpImpact;
  final List<String> erpDocs;
  final String? erpReason;

  /// JSON original, guardado nos favoritos para a notícia continuar disponível
  /// mesmo depois de sair da janela de 90 dias do site.
  final Map<String, dynamic> raw;

  Article({
    required this.id,
    required this.title,
    required this.url,
    this.outlet,
    this.sourceName,
    this.imageUrl,
    this.publishedAt,
    this.datePrecision,
    this.dateConfirmed = true,
    this.collectedAt,
    this.excerpt,
    this.summary,
    this.summaryLang,
    this.provider,
    this.keyPoints = const [],
    this.impacts = const [],
    this.legalRefs = const [],
    this.terms = const [],
    this.categories = const [],
    this.primaryCategory,
    this.relevance = 0,
    this.official = false,
    this.docType,
    this.legalStage,
    this.stageNote,
    this.legislative = false,
    this.nature,
    this.validationStatus,
    this.viaAggregator = false,
    this.isDuplicate = false,
    this.isUpdate = false,
    this.groupId,
    this.groupSources = 0,
    this.erpImpact = false,
    this.erpDocs = const [],
    this.erpReason,
    this.raw = const {},
  });

  static bool _bool(Object? v) => v == true || v == 1 || v == '1' || v == 'true';

  static List<String> _strings(Object? v) =>
      v is List ? v.map((e) => e.toString()).where((s) => s.isNotEmpty).toList() : const [];

  static String? _str(Object? v) => v is String && v.isNotEmpty ? v : null;

  factory Article.fromJson(Map<String, dynamic> j) => Article(
        id: (j['id'] as num).toInt(),
        title: (j['title'] as String?) ?? '(sem título)',
        url: (j['url'] as String?) ?? '',
        outlet: _str(j['outlet']),
        sourceName: _str(j['source_name']),
        imageUrl: _str(j['image_url']),
        publishedAt: _str(j['published_at']),
        datePrecision: _str(j['date_precision']),
        // arquivos antigos (favoritos) não têm o campo: considera confirmada
        dateConfirmed: j.containsKey('date_confirmed') ? _bool(j['date_confirmed']) : true,
        collectedAt: _str(j['collected_at']),
        excerpt: _str(j['excerpt']),
        summary: _str(j['summary']),
        summaryLang: _str(j['summary_lang']),
        provider: _str(j['provider']),
        keyPoints: _strings(j['key_points']),
        impacts: _strings(j['impacts']),
        legalRefs: _strings(j['legal_refs']),
        terms: (j['terms'] is List ? j['terms'] as List : const [])
            .whereType<Map>()
            .map((t) => Term('${t['term'] ?? ''}', '${t['explanation'] ?? ''}'))
            .where((t) => t.term.isNotEmpty)
            .toList(),
        categories: _strings(j['categories']),
        primaryCategory: _str(j['primary_category']),
        relevance: (j['relevance'] as num?)?.toDouble() ?? 0,
        official: _bool(j['official']),
        docType: _str(j['doc_type']),
        legalStage: _str(j['legal_stage']),
        stageNote: _str(j['stage_note']),
        legislative: _bool(j['legislative']),
        nature: _str(j['nature']),
        validationStatus: _str(j['validation_status']),
        viaAggregator: _bool(j['via_aggregator']),
        isDuplicate: _bool(j['is_duplicate']),
        isUpdate: _bool(j['is_update']),
        groupId: (j['group_id'] as num?)?.toInt(),
        groupSources: (j['group_sources'] as num?)?.toInt() ?? 0,
        erpImpact: _bool(j['erp_impact']),
        erpDocs: _strings(j['erp_docs']),
        erpReason: _str(j['erp_reason']),
        raw: j,
      );

  /// Data de publicação (UTC). Nulo quando a fonte não informa.
  DateTime? get published {
    final p = publishedAt;
    if (p == null || p.isEmpty) return null;
    return DateTime.tryParse(p.length == 10 ? '${p}T00:00:00Z' : p);
  }

  bool get dateOnly => (publishedAt?.length ?? 0) == 10 || datePrecision == 'date';

  /// Fonte exibida: o veículo, ou o nome da fonte cadastrada.
  String get source => outlet ?? sourceName ?? '';

  bool get isOfficial => docType == 'oficial' || (official && docType == null);

  /// Categorias para exibir (como no site: a principal quando não há lista).
  List<String> get shownCategories =>
      categories.isNotEmpty ? categories : [?primaryCategory];

  bool get aiSummary => provider != null && provider != 'regras';
}

class RadarStatus {
  final String health; // ok | parcial | falhas
  final DateTime? lastFinished;
  final int lastNewItems;
  final int intervalMin;

  const RadarStatus({this.health = 'ok', this.lastFinished, this.lastNewItems = 0, this.intervalMin = 60});

  factory RadarStatus.fromJson(Map<String, dynamic> j) {
    final last = (j['last_finished'] as Map?)?.cast<String, dynamic>();
    return RadarStatus(
      health: (j['health'] as String?) ?? 'ok',
      lastFinished: DateTime.tryParse((last?['finished_at'] as String?) ?? ''),
      lastNewItems: (last?['new_items'] as num?)?.toInt() ?? 0,
      intervalMin: (j['interval_min'] as num?)?.toInt() ?? 60,
    );
  }
}

class Outlet {
  final String name;
  final int count;
  const Outlet(this.name, this.count);
}

class RadarData {
  final DateTime? generatedAt;
  final List<Category> categories;
  final Map<String, String> stages;
  final List<Outlet> outlets;
  final RadarStatus status;
  final int sourcesTotal;
  final int sourcesFailing;

  /// Todas as notícias, inclusive as repetidas (usadas em "mesma notícia").
  final List<Article> all;

  /// Só as notícias principais (sem duplicadas), da mais nova para a mais antiga.
  final List<Article> list;

  RadarData({
    required this.generatedAt,
    required this.categories,
    required this.stages,
    required this.all,
    required this.list,
    this.outlets = const [],
    this.status = const RadarStatus(),
    this.sourcesTotal = 0,
    this.sourcesFailing = 0,
  });

  factory RadarData.fromJson(Map<String, dynamic> j) {
    final meta = (j['meta'] as Map?)?.cast<String, dynamic>() ?? const {};
    final all = ((j['articles'] as List?) ?? const [])
        .whereType<Map>()
        .map((e) => Article.fromJson(e.cast<String, dynamic>()))
        .toList();
    final list = all.where((a) => !a.isDuplicate).toList()..sort(byPublishedDesc);
    final status = (j['status'] as Map?)?.cast<String, dynamic>() ?? const {};
    return RadarData(
      generatedAt: DateTime.tryParse((j['generated_at'] as String?) ?? ''),
      categories: ((meta['categories'] as List?) ?? const [])
          .whereType<Map>()
          .map((e) => Category.fromJson(e.cast<String, dynamic>()))
          .toList(),
      stages: ((meta['stages'] as Map?) ?? const {}).map((k, v) => MapEntry(k.toString(), v.toString())),
      outlets: ((meta['outlets'] as List?) ?? const [])
          .whereType<Map>()
          .map((o) => Outlet('${o['outlet'] ?? ''}', (o['n'] as num?)?.toInt() ?? 0))
          .where((o) => o.name.isNotEmpty)
          .toList(),
      status: RadarStatus.fromJson({...status, 'interval_min': status['interval_min'] ?? meta['interval_min']}),
      sourcesTotal: (meta['sources_total'] as num?)?.toInt() ?? 0,
      sourcesFailing: (meta['sources_failing'] as num?)?.toInt() ?? 0,
      all: all,
      list: list,
    );
  }

  Category? category(String? slug) {
    for (final c in categories) {
      if (c.slug == slug) return c;
    }
    return null;
  }

  /// Outras publicações sobre o mesmo assunto (mesmo grupo de duplicidade).
  List<Article> related(Article a) {
    if (a.groupId == null) return const [];
    return all.where((x) => x.groupId == a.groupId && x.id != a.id).toList()..sort(byPublishedDesc);
  }

  Map<String, int> get countByCategory {
    final m = <String, int>{};
    for (final a in list) {
      for (final c in a.categories) {
        m[c] = (m[c] ?? 0) + 1;
      }
    }
    return m;
  }
}

/// Mesma ordem do site: sem data por último; depois mais recente primeiro.
int byPublishedDesc(Article a, Article b) {
  final pa = a.publishedAt ?? '', pb = b.publishedAt ?? '';
  if (pa.isEmpty != pb.isEmpty) return pa.isEmpty ? 1 : -1;
  final c = pb.compareTo(pa);
  return c != 0 ? c : b.id.compareTo(a.id);
}
