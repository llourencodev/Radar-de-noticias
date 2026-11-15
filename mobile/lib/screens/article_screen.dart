import 'package:material_ui/material_ui.dart';
import 'package:flutter/services.dart';

import '../favorites.dart';
import '../format.dart';
import '../models.dart';

/// Detalhes da notícia: resumo, pontos principais, impacto no ERP e outras fontes do mesmo assunto.
class ArticleScreen extends StatelessWidget {
  final Article article;
  final RadarData? data;
  final Favorites favorites;

  const ArticleScreen({super.key, required this.article, required this.data, required this.favorites});

  @override
  Widget build(BuildContext context) {
    final a = article;
    final theme = Theme.of(context);
    final related = data?.related(a) ?? const <Article>[];
    final cats = a.categories.map((s) => data?.category(s)).whereType<Category>().toList();
    final stage = a.legalStage != null && a.legalStage != 'nao_determinado' ? data?.stages[a.legalStage] : null;

    return Scaffold(
      appBar: AppBar(
        title: Text(a.source, maxLines: 1, overflow: TextOverflow.ellipsis),
        actions: [
          IconButton(
            tooltip: 'Copiar link',
            icon: const Icon(Icons.link),
            onPressed: () async {
              await Clipboard.setData(ClipboardData(text: a.url));
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Link copiado')));
              }
            },
          ),
          ListenableBuilder(
            listenable: favorites,
            builder: (context, _) {
              final fav = favorites.contains(a);
              return IconButton(
                tooltip: fav ? 'Remover dos favoritos' : 'Salvar nos favoritos',
                icon: Icon(fav ? Icons.bookmark : Icons.bookmark_border),
                onPressed: () => favorites.toggle(a),
              );
            },
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
        children: [
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final c in cats)
              Chip(
                label: Text(c.name),
                labelStyle: TextStyle(color: c.color, fontWeight: FontWeight.w600),
                side: BorderSide(color: c.color.withValues(alpha: 0.5)),
                visualDensity: VisualDensity.compact,
              ),
            if (a.isOfficial)
              const Chip(avatar: Icon(Icons.verified, size: 16), label: Text('Publicação oficial'), visualDensity: VisualDensity.compact),
            if (stage != null) Chip(label: Text(stage), visualDensity: VisualDensity.compact),
          ]),
          const SizedBox(height: 12),
          Text(a.title, style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          Text('${a.source} · ${formatDate(a)}', style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
          if (a.imageUrl?.startsWith('https://') == true) ...[
            const SizedBox(height: 16),
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Image.network(a.imageUrl!,
                  fit: BoxFit.cover,
                  height: 200,
                  width: double.infinity,
                  errorBuilder: (_, _, _) => const SizedBox.shrink()),
            ),
          ],
          if (a.summary?.isNotEmpty == true) ...[
            _section(context, 'Resumo'),
            Text(a.summary!, style: theme.textTheme.bodyLarge),
          ],
          if (a.keyPoints.isNotEmpty) ...[
            _section(context, 'Pontos principais'),
            for (final p in a.keyPoints)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('•  '),
                  Expanded(child: Text(p, style: theme.textTheme.bodyMedium)),
                ]),
              ),
          ],
          if (a.excerpt?.isNotEmpty == true && a.excerpt != a.summary) ...[
            _section(context, 'Trecho da fonte'),
            Text(a.excerpt!, style: theme.textTheme.bodyMedium),
          ],
          if (a.erpImpact) ...[
            _section(context, 'Impacto no ERP'),
            if (a.erpDocs.isNotEmpty)
              Wrap(spacing: 6, children: [for (final d in a.erpDocs) Chip(label: Text(d), visualDensity: VisualDensity.compact)]),
            if (a.erpReason?.isNotEmpty == true) Text(a.erpReason!, style: theme.textTheme.bodyMedium),
          ],
          if (related.isNotEmpty) ...[
            _section(context, 'Mesma notícia e atualizações'),
            for (final r in related)
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(r.title, maxLines: 2, overflow: TextOverflow.ellipsis),
                subtitle: Text('${r.source} · ${formatDate(r)}${r.isUpdate ? ' · atualização' : ''}'),
                trailing: const Icon(Icons.open_in_new, size: 18),
                onTap: () => _open(context, r.url),
              ),
          ],
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _open(context, a.url),
        icon: const Icon(Icons.open_in_new),
        label: const Text('Abrir notícia'),
      ),
    );
  }

  static Widget _section(BuildContext context, String title) => Padding(
        padding: const EdgeInsets.only(top: 20, bottom: 8),
        child: Text(title, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
      );

  static Future<void> _open(BuildContext context, String url) async {
    final ok = await openArticle(url).catchError((_) => false);
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Não foi possível abrir o link')));
    }
  }
}
