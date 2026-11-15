/// Filtros da lista, com as mesmas regras do site (web/app.js e web/static-api.js).
library;

import 'models.dart';

/// Períodos pela data de publicação: [valor, rótulo]. Iguais aos do site.
const periods = <(String, String)>[
  ('1h', 'Última hora'),
  ('24h', '24 horas'),
  ('1', 'Hoje'),
  ('7', '7 dias'),
  ('30', '30 dias'),
  ('90', '90 dias'),
  ('365', '1 ano'),
  ('', 'Tudo'),
];

String periodLabel(String value) =>
    periods.firstWhere((p) => p.$1 == value, orElse: () => ('', 'Tudo')).$2;

/// Início do período em UTC, no formato salvo pelo Radar ("2026-11-15T03:00:00Z").
/// "Hoje" e "N dias" começam à meia-noite do horário do aparelho, como no site.
String? periodStart(String period, {DateTime? now}) {
  final n = now ?? DateTime.now();
  final h = RegExp(r'^(\d+)h$').firstMatch(period);
  if (h != null) return isoZ(n.subtract(Duration(hours: int.parse(h.group(1)!))));
  final days = int.tryParse(period);
  if (days == null || days == 0) return null;
  final start = DateTime(n.year, n.month, n.day).subtract(Duration(days: days - 1));
  return isoZ(start);
}

String localDate(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

String isoZ(DateTime d) => '${d.toUtc().toIso8601String().split('.').first.replaceAll('Z', '')}Z';

/// Minúsculas e sem acentos, para a busca encontrar "tributaria" em "Tributária".
String fold(String? s) {
  if (s == null || s.isEmpty) return '';
  const from = 'áàâãäåéèêëíìîïóòôõöúùûüçñ';
  const to = 'aaaaaaeeeeiiiiooooouuuucn';
  final b = StringBuffer();
  for (final ch in s.toLowerCase().split('')) {
    final i = from.indexOf(ch);
    b.write(i >= 0 ? to[i] : ch);
  }
  return b.toString();
}

class Filters {
  final String category; // 'todas' ou o slug da categoria
  final String period; // valor de [periods]
  final bool onlyOfficial;
  final String query;

  const Filters({this.category = 'todas', this.period = '', this.onlyOfficial = false, this.query = ''});

  Filters copyWith({String? category, String? period, bool? onlyOfficial, String? query}) => Filters(
        category: category ?? this.category,
        period: period ?? this.period,
        onlyOfficial: onlyOfficial ?? this.onlyOfficial,
        query: query ?? this.query,
      );

  bool get isDefault => period.isEmpty && !onlyOfficial && query.trim().isEmpty;

  List<Article> apply(List<Article> source, {DateTime? now}) {
    Iterable<Article> it = source;
    if (category != 'todas') it = it.where((a) => a.categories.contains(category));
    final from = periodStart(period, now: now);
    if (from != null) {
      // notícias só com a data (sem hora): entram nos períodos em dias ("Hoje", "7 dias"...)
      // se forem do primeiro dia em diante, no calendário do aparelho; nos de horas, não entram.
      final byHours = period.endsWith('h');
      final firstDay = byHours ? null : localDate(DateTime.parse(from).toLocal());
      it = it.where((a) {
        final p = a.publishedAt;
        if (p == null || p.isEmpty) return false;
        if (p.length == 10) return firstDay != null && p.compareTo(firstDay) >= 0;
        return p.compareTo(from) >= 0;
      });
    }
    // Na Reforma e no Fiscal o site filtra por documento oficial; nas demais, por fonte oficial.
    if (onlyOfficial) {
      final byDoc = category == 'fiscal' || category == 'reforma';
      it = it.where((a) => byDoc ? a.docType == 'oficial' : a.official);
    }
    final words = fold(query).split(RegExp(r'\s+')).where((w) => w.length > 1).toList();
    if (words.isNotEmpty) {
      it = it.where((a) {
        final text = fold('${a.title} ${a.excerpt ?? ''} ${a.summary ?? ''} ${a.source}');
        return words.every(text.contains);
      });
    }
    return it.toList();
  }
}
