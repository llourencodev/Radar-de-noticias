import 'package:url_launcher/url_launcher.dart';

import 'models.dart';

String _two(int n) => n.toString().padLeft(2, '0');

/// "15/11/2026 08:30" no horário do aparelho; só a data quando a fonte não informa a hora.
String formatDate(Article a) {
  final d = a.published;
  if (d == null) return 'sem data';
  if (a.dateOnly) return '${_two(d.day)}/${_two(d.month)}/${d.year}';
  final l = d.toLocal();
  return '${_two(l.day)}/${_two(l.month)}/${l.year} ${_two(l.hour)}:${_two(l.minute)}';
}

/// "há 5 min", "há 3 h", "ontem"... para a lista.
String relativeDate(Article a, {DateTime? now}) {
  final d = a.published;
  if (d == null) return 'sem data';
  final n = now ?? DateTime.now();
  if (a.dateOnly) {
    final today = DateTime(n.year, n.month, n.day);
    final day = DateTime(d.year, d.month, d.day);
    final diff = today.difference(day).inDays;
    if (diff == 0) return 'hoje';
    if (diff == 1) return 'ontem';
    return formatDate(a);
  }
  final diff = n.difference(d.toLocal());
  if (diff.inMinutes < 1) return 'agora';
  if (diff.inMinutes < 60) return 'há ${diff.inMinutes} min';
  if (diff.inHours < 24) return 'há ${diff.inHours} h';
  if (diff.inDays == 1) return 'ontem';
  if (diff.inDays < 7) return 'há ${diff.inDays} dias';
  return formatDate(a);
}

String formatGenerated(DateTime? d) {
  if (d == null) return '';
  final l = d.toLocal();
  return '${_two(l.day)}/${_two(l.month)} às ${_two(l.hour)}:${_two(l.minute)}';
}

/// Abre a notícia original no navegador. Só aceita http/https.
Future<bool> openArticle(String url) async {
  final uri = Uri.tryParse(url);
  if (uri == null || !(uri.scheme == 'http' || uri.scheme == 'https')) return false;
  return launchUrl(uri, mode: LaunchMode.externalApplication);
}
