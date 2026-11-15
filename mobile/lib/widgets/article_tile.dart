import 'package:material_ui/material_ui.dart';

import '../favorites.dart';
import '../format.dart';
import '../models.dart';

/// Cartão da notícia na lista: categoria, título, fonte, data e resumo.
class ArticleTile extends StatelessWidget {
  final Article article;
  final RadarData? data;
  final Favorites favorites;
  final VoidCallback onTap;

  const ArticleTile({super.key, required this.article, required this.data, required this.favorites, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final a = article;
    final theme = Theme.of(context);
    final cat = data?.category(a.primaryCategory ?? (a.categories.isEmpty ? '' : a.categories.first));
    final color = cat?.color ?? theme.colorScheme.outline;
    final text = a.summary?.isNotEmpty == true ? a.summary! : (a.excerpt ?? '');

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(width: 4, color: color),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(12, 10, 4, 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(children: [
                        if (cat != null)
                          Flexible(
                            child: Text(cat.name.toUpperCase(),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: theme.textTheme.labelSmall?.copyWith(color: color, fontWeight: FontWeight.w700)),
                          ),
                        if (a.isOfficial) ...[
                          const SizedBox(width: 6),
                          Icon(Icons.verified, size: 14, color: theme.colorScheme.primary),
                          const SizedBox(width: 2),
                          Text('Oficial', style: theme.textTheme.labelSmall?.copyWith(color: theme.colorScheme.primary)),
                        ],
                        if (a.isUpdate) ...[
                          const SizedBox(width: 6),
                          Text('Atualização', style: theme.textTheme.labelSmall?.copyWith(color: theme.colorScheme.tertiary)),
                        ],
                      ]),
                      const SizedBox(height: 4),
                      Text(a.title, style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600)),
                      const SizedBox(height: 4),
                      Text('${a.source} · ${relativeDate(a)}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
                      if (text.isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Text(text, maxLines: 3, overflow: TextOverflow.ellipsis, style: theme.textTheme.bodyMedium),
                      ],
                    ],
                  ),
                ),
              ),
              ListenableBuilder(
                listenable: favorites,
                builder: (context, _) {
                  final fav = favorites.contains(a);
                  return IconButton(
                    tooltip: fav ? 'Remover dos favoritos' : 'Salvar nos favoritos',
                    icon: Icon(fav ? Icons.bookmark : Icons.bookmark_border),
                    color: fav ? theme.colorScheme.primary : null,
                    onPressed: () => favorites.toggle(a),
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
