/// Modelos dos dados publicados pelo Radar em `data/radar.json`
/// (gerado por app/static_site.py a cada coleta no GitHub Actions).
library;

import 'package:material_ui/material_ui.dart';

class Category {
  final String slug;
  final String name;
  final Color color;

  const Category({required this.slug, required this.name, required this.color});

  factory Category.fromJson(Map<String, dynamic> j) => Category(
        slug: j['slug'] as String,
        name: (j['name'] as String?) ?? j['slug'] as String,
        color: parseHexColor(j['color'] as String?) ?? Colors.blueGrey,
      );
}

Color? parseHexColor(String? hex) {
  if (hex == null) return null;
  final h = hex.replaceFirst('#', '');
  if (h.length != 6) return null;
  final v = int.tryParse(h, radix: 16);
  return v == null ? null : Color(0xFF000000 | v);
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
  final String? excerpt;
  final String? summary;
  final List<String> keyPoints;
  final List<String> categories;
  final String? primaryCategory;
  final double relevance;
  final bool official;
  final String? docType;
  final String? legalStage;
  final bool isDuplicate;
  final bool isUpdate;
  final int? groupId;
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
    this.excerpt,
    this.summary,
    this.keyPoints = const [],
    this.categories = const [],
    this.primaryCategory,
    this.relevance = 0,
    this.official = false,
    this.docType,
    this.legalStage,
    this.isDuplicate = false,
    this.isUpdate = false,
    this.groupId,
    this.erpImpact = false,
    this.erpDocs = const [],
    this.erpReason,
    this.raw = const {},
  });

  static bool _bool(Object? v) => v == true || v == 1 || v == '1' || v == 'true';

  static List<String> _strings(Object? v) =>
      v is List ? v.map((e) => e.toString()).where((s) => s.isNotEmpty).toList() : const [];

  factory Article.fromJson(Map<String, dynamic> j) => Article(
        id: (j['id'] as num).toInt(),
        title: (j['title'] as String?) ?? '(sem título)',
        url: (j['url'] as String?) ?? '',
        outlet: j['outlet'] as String?,
        sourceName: j['source_name'] as String?,
        imageUrl: j['image_url'] as String?,
        publishedAt: j['published_at'] as String?,
        datePrecision: j['date_precision'] as String?,
        excerpt: j['excerpt'] as String?,
        summary: j['summary'] as String?,
        keyPoints: _strings(j['key_points']),
        categories: _strings(j['categories']),
        primaryCategory: j['primary_category'] as String?,
        relevance: (j['relevance'] as num?)?.toDouble() ?? 0,
        official: _bool(j['official']),
        docType: j['doc_type'] as String?,
        legalStage: j['legal_stage'] as String?,
        isDuplicate: _bool(j['is_duplicate']),
        isUpdate: _bool(j['is_update']),
        groupId: (j['group_id'] as num?)?.toInt(),
        erpImpact: _bool(j['erp_impact']),
        erpDocs: _strings(j['erp_docs']),
        erpReason: j['erp_reason'] as String?,
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
  String get source => (outlet?.isNotEmpty ?? false) ? outlet! : (sourceName ?? '');

  bool get isOfficial => docType == 'oficial' || (official && docType == null);
}

class RadarData {
  final DateTime? generatedAt;
  final List<Category> categories;
  final Map<String, String> stages;

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
  });

  factory RadarData.fromJson(Map<String, dynamic> j) {
    final meta = (j['meta'] as Map?)?.cast<String, dynamic>() ?? const {};
    final all = ((j['articles'] as List?) ?? const [])
        .whereType<Map>()
        .map((e) => Article.fromJson(e.cast<String, dynamic>()))
        .toList();
    final list = all.where((a) => !a.isDuplicate).toList()..sort(byPublishedDesc);
    return RadarData(
      generatedAt: DateTime.tryParse((j['generated_at'] as String?) ?? ''),
      categories: ((meta['categories'] as List?) ?? const [])
          .whereType<Map>()
          .map((e) => Category.fromJson(e.cast<String, dynamic>()))
          .toList(),
      stages: ((meta['stages'] as Map?) ?? const {}).map((k, v) => MapEntry(k.toString(), v.toString())),
      all: all,
      list: list,
    );
  }

  Category? category(String slug) {
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
}

/// Mesma ordem do site: sem data por último; depois mais recente primeiro.
int byPublishedDesc(Article a, Article b) {
  final pa = a.publishedAt ?? '', pb = b.publishedAt ?? '';
  if (pa.isEmpty != pb.isEmpty) return pa.isEmpty ? 1 : -1;
  final c = pb.compareTo(pa);
  return c != 0 ? c : b.id.compareTo(a.id);
}
