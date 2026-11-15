/// Filtros e busca das listas, com as mesmas regras do site (web/app.js e web/static-api.js).
library;

import 'dart:math' as math;

import 'models.dart';

/// Períodos pela data de publicação: (valor, rótulo, dica). Iguais aos do site.
const periods = <(String, String, String)>[
  ('1h', 'Última hora', 'publicadas nos últimos 60 minutos'),
  ('24h', '24 horas', 'publicadas nas últimas 24 horas'),
  ('1', 'Hoje', 'publicadas hoje (desde 00:00)'),
  ('7', '7 dias', 'publicadas nos últimos 7 dias'),
  ('30', '30 dias', 'publicadas nos últimos 30 dias'),
  ('90', '90 dias', 'publicadas nos últimos 90 dias'),
  ('365', '1 ano', 'publicadas nos últimos 12 meses'),
  ('', 'Tudo', 'qualquer data'),
];

/// Estágios das normas (mesmos rótulos do site).
const stageLabels = <String, String>{
  'nao_determinado': 'Estágio não determinado',
  'projeto_de_lei': 'Projeto de lei',
  'consulta_publica': 'Consulta pública',
  'norma_aprovada': 'Norma aprovada',
  'norma_publicada': 'Norma publicada',
  'norma_em_vigor': 'Norma em vigor',
};

const erpDocs = [
  'NF-e', 'NFC-e', 'NFS-e', 'CT-e', 'MDF-e', 'NF3e/NFCom', 'BP-e/GNRE', 'SPED/EFD', 'EFD-Reinf', 'eSocial',
  'DCTFWeb', 'IBS/CBS', 'Documentos fiscais',
];

const searchExamples = [
  'Nova Nota Técnica da NF-e', 'Mudanças no IBS e CBS', 'Atualização do C#', 'Novo modelo da Anthropic',
  'Alterações no ICMS de Minas Gerais',
];

String periodLabel(String value) => periods.firstWhere((p) => p.$1 == value, orElse: () => periods[7]).$2;

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

/// Palavras curtas e comuns que não ajudam na busca.
const _stop = {
  'de', 'da', 'do', 'das', 'dos', 'e', 'a', 'o', 'as', 'os', 'em', 'no', 'na', 'nos', 'nas', 'um', 'uma', 'para',
  'por', 'com', 'que', 'se', 'ao', 'aos', 'the', 'of', 'and', 'to', 'in', 'novo', 'nova', 'mudancas', 'alteracoes',
};

/// Palavras da busca. Como no site (normalize.py/_fts_term), palavras longas viram prefixo:
/// "tributária" encontra "tributário", "tributação"...
List<String> queryWords(String q) => fold(q)
    .split(RegExp(r'[^a-z0-9#+]+'))
    .where((w) => w.isNotEmpty && !_stop.contains(w) && (w.length > 1 || RegExp(r'\d').hasMatch(w)))
    .map((w) => w.length >= 6 && RegExp(r'^[a-z]+$').hasMatch(w) ? w.substring(0, math.max(4, w.length - 3)) : w)
    .toSet()
    .toList();

/// Lista "todas", "erp" ou o slug de uma categoria.
class Filters {
  final String view;
  final String category; // só na lista "todas"
  final String period;
  final bool onlyOfficial;
  final String query;
  final String source;
  final String minRelevance; // '', '40', '60'
  final String legalStage;
  final bool erp;
  final String erpDoc;
  final String sort; // auto | recent | relevance

  const Filters({
    this.view = 'todas',
    this.category = '',
    this.period = '',
    this.onlyOfficial = false,
    this.query = '',
    this.source = '',
    this.minRelevance = '',
    this.legalStage = '',
    this.erp = false,
    this.erpDoc = '',
    this.sort = 'auto',
  });

  bool get isErp => view == 'erp';
  bool get isAll => view == 'todas' || isErp;

  /// Em Fiscal, Reforma e ERP o site filtra por documento oficial e mostra o estágio da norma.
  bool get fiscal => view == 'fiscal' || view == 'reforma' || isErp;

  Filters copyWith({
    String? view,
    String? category,
    String? period,
    bool? onlyOfficial,
    String? query,
    String? source,
    String? minRelevance,
    String? legalStage,
    bool? erp,
    String? erpDoc,
    String? sort,
  }) =>
      Filters(
        view: view ?? this.view,
        category: category ?? this.category,
        period: period ?? this.period,
        onlyOfficial: onlyOfficial ?? this.onlyOfficial,
        query: query ?? this.query,
        source: source ?? this.source,
        minRelevance: minRelevance ?? this.minRelevance,
        legalStage: legalStage ?? this.legalStage,
        erp: erp ?? this.erp,
        erpDoc: erpDoc ?? this.erpDoc,
        sort: sort ?? this.sort,
      );

  List<Article> apply(List<Article> source, {DateTime? now}) {
    Iterable<Article> it = source;
    final cat = isAll ? category : view;
    if (cat.isNotEmpty && cat != 'todas') it = it.where((a) => a.categories.contains(cat));
    if (this.source.isNotEmpty) {
      final s = this.source.toLowerCase();
      it = it.where((a) => (a.outlet ?? '').toLowerCase().contains(s));
    }
    final from = periodStart(period, now: now);
    if (from != null) {
      // só com a data (sem hora): entram nos períodos em dias se forem do primeiro dia em diante
      final byHours = period.endsWith('h');
      final firstDay = byHours ? null : localDate(DateTime.parse(from).toLocal());
      it = it.where((a) {
        final p = a.publishedAt;
        if (p == null || p.isEmpty) return false;
        if (p.length == 10) return firstDay != null && p.compareTo(firstDay) >= 0;
        return p.compareTo(from) >= 0;
      });
    }
    final minRel = double.tryParse(minRelevance);
    if (minRel != null) it = it.where((a) => a.relevance >= minRel);
    if (onlyOfficial) it = it.where((a) => fiscal ? a.docType == 'oficial' : a.official);
    if (legalStage.isNotEmpty) it = it.where((a) => a.legalStage == legalStage);
    if (isErp || erp) it = it.where((a) => a.erpImpact);
    if (erpDoc.isNotEmpty) it = it.where((a) => a.erpDocs.contains(erpDoc));

    final words = queryWords(query);
    if (words.isEmpty) {
      final items = it.toList();
      if (sort == 'relevance') {
        items.sort((a, b) {
          final c = b.relevance.compareTo(a.relevance);
          return c != 0 ? c : (b.publishedAt ?? '').compareTo(a.publishedAt ?? '');
        });
      } else {
        items.sort(byPublishedDesc);
      }
      return items;
    }
    // busca: todas as palavras precisam aparecer; ordena por pertinência como o site (título pesa mais)
    final scored = <(Article, double)>[];
    for (final a in it) {
      final fields = [(fold(a.title), 10.0), (fold(a.excerpt), 3.0), (fold(a.summary), 3.0), (fold(a.outlet), 1.0)];
      var ok = true;
      var score = 0.0;
      for (final w in words) {
        var hit = false;
        for (final (text, weight) in fields) {
          final n = _count(text, w);
          if (n > 0) {
            hit = true;
            score += weight * (n * 2.2) / (n + 1.2);
          }
        }
        if (!hit) {
          ok = false;
          break;
        }
      }
      if (ok) scored.add((a, score));
    }
    if (sort == 'recent') {
      scored.sort((x, y) => byPublishedDesc(x.$1, y.$1));
    } else if (sort == 'relevance') {
      scored.sort((x, y) => y.$1.relevance.compareTo(x.$1.relevance));
    } else {
      scored.sort((x, y) {
        final c = y.$2.compareTo(x.$2);
        return c != 0 ? c : byPublishedDesc(x.$1, y.$1);
      });
    }
    return scored.map((s) => s.$1).toList();
  }

  static int _count(String text, String word) {
    if (text.isEmpty) return 0;
    var n = 0;
    var i = text.indexOf(word);
    while (i >= 0) {
      final startOk = i == 0 || !RegExp(r'[a-z0-9]').hasMatch(text[i - 1]);
      if (startOk) n++;
      i = text.indexOf(word, i + math.max(1, word.length));
    }
    return n;
  }
}
