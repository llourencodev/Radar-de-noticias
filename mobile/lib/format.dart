import 'package:material_ui/material_ui.dart';
import 'package:url_launcher/url_launcher.dart';

import 'models.dart';

String _two(int n) => n.toString().padLeft(2, '0');

/// "15/11/2026 08:30" no horário do aparelho.
String fmtDateTime(DateTime d) {
  final l = d.toLocal();
  return '${_two(l.day)}/${_two(l.month)}/${l.year} ${_two(l.hour)}:${_two(l.minute)}';
}

/// Data como no site: só o dia quando a fonte não informa a hora.
String formatDate(Article a) {
  final p = a.publishedAt;
  final d = a.published;
  if (p == null || d == null) return 'data não confirmada';
  if (a.dateOnly) {
    final parts = p.substring(0, 10).split('-');
    return '${parts[2]}/${parts[1]}/${parts[0]}';
  }
  return fmtDateTime(d);
}

/// "15/11/2026 08:30 · há 3 h" (igual a pubDate() do site).
String pubDateText(Article a, {DateTime? now}) {
  final d = a.published;
  if (d == null) return 'Data não confirmada';
  if (a.dateOnly) return formatDate(a);
  return '${fmtDateTime(d)} · ${relative(d, now: now)}';
}

String relative(DateTime d, {DateTime? now}) {
  final s = (now ?? DateTime.now()).difference(d).inSeconds;
  if (s < 60) return 'agora';
  if (s < 3600) return 'há ${s ~/ 60} min';
  if (s < 86400) return 'há ${s ~/ 3600} h';
  final days = s ~/ 86400;
  return days == 1 ? 'ontem' : 'há $days dias';
}

const _weekdays = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo'];
const _months = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro',
  'dezembro',
];

/// "domingo, 15 de novembro de 2026" (sobretítulo do painel).
String fullDate(DateTime d) => '${_weekdays[d.weekday - 1]}, ${d.day} de ${_months[d.month - 1]} de ${d.year}';

String thousands(int n) {
  final s = n.toString();
  final b = StringBuffer();
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) b.write('.');
    b.write(s[i]);
  }
  return b.toString();
}

/// Abre a notícia original no navegador. Só aceita http/https.
Future<bool> openArticle(String url) async {
  final uri = Uri.tryParse(url);
  if (uri == null || !(uri.scheme == 'http' || uri.scheme == 'https')) return false;
  return launchUrl(uri, mode: LaunchMode.externalApplication);
}

Future<void> openOriginal(BuildContext context, String url) async {
  final ok = await openArticle(url).catchError((_) => false);
  if (!ok && context.mounted) {
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Não foi possível abrir o link')));
  }
}
