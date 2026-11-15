import 'package:material_ui/material_ui.dart';

import '../app_state.dart';
import '../filters.dart';
import '../format.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/radar_widgets.dart';

const _texts = {
  'reforma':
      'Publicações oficiais têm prioridade. O estágio de cada norma é classificado de forma conservadora: uma proposta nunca aparece como norma vigente.',
  'erp':
      'Notas técnicas, leiautes, schemas, regras de validação, Ajustes SINIEF/Atos COTEPE e mudanças (inclusive IBS/CBS) que exigem ajuste ou implementação em ERPs e emissores de documentos fiscais. Classificação automática: confirme sempre na publicação oficial.',
  'fiscal':
      'Separação entre publicação oficial e notícia jornalística, e estágio de cada norma (projeto, consulta, aprovada, publicada, em vigor).',
};

/// Lista de uma categoria, de "Todas as notícias" ou de "Notas técnicas / ERP", com os filtros do site.
class NewsListView extends StatefulWidget {
  final AppState state;
  final String view; // slug da categoria, 'todas' ou 'erp'
  final String query;
  final Map<String, String> params;
  final ValueChanged<Article> onOpen;
  final ValueChanged<String> onSearch;
  const NewsListView({
    super.key,
    required this.state,
    required this.view,
    required this.query,
    required this.onOpen,
    required this.onSearch,
    this.params = const {},
  });

  @override
  State<NewsListView> createState() => _NewsListViewState();
}

class _NewsListViewState extends State<NewsListView> {
  late Filters f;
  int shown = 30;

  @override
  void initState() {
    super.initState();
    final p = widget.params;
    f = Filters(
      view: widget.view,
      query: widget.query,
      sort: p['sort'] ?? (widget.query.isEmpty ? 'recent' : 'auto'),
      onlyOfficial: p['official'] == '1',
    );
  }

  void set(Filters nf) => setState(() {
        f = nf;
        shown = 30;
      });

  @override
  Widget build(BuildContext context) {
    final data = widget.state.data!;
    final rc = context.rc;
    final Category c = f.isErp
        ? const Category(slug: 'erp', name: 'Notas técnicas e ajustes em ERP', color: erpColor)
        : f.view == 'todas'
            ? const Category(slug: 'todas', name: 'Todas as notícias', color: allColor)
            : catOf(data, f.view);
    final items = f.apply(data.list);
    final visible = items.take(shown).toList();
    final q = f.query;
    final per = periods.firstWhere((p) => p.$1 == f.period, orElse: () => periods[7]);
    final info = '${thousands(items.length)} notícia(s)${q.isNotEmpty ? ' para “$q”' : ''}'
        '${f.period.isNotEmpty ? ' · ${per.$3}' : ''}'
        ' · ordenadas por ${f.sort == 'relevance' ? 'relevância' : f.sort == 'recent' || q.isEmpty ? 'data de publicação' : 'pertinência à busca'}';

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 32),
      children: [
        PageHead(
          eyebrow: f.isErp ? 'Impacto em sistemas' : f.isAll ? 'Visão geral' : 'Categoria',
          eyebrowColor: c.color,
          title: c.name,
          text: _texts[f.view],
        ),
        if (f.view == 'todas') ...[
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final e in searchExamples)
              ActionChip(
                label: Text(e),
                onPressed: () => widget.onSearch(e),
                backgroundColor: rc.surface,
                side: BorderSide(color: rc.border),
                shape: const StadiumBorder(),
                labelStyle: TextStyle(fontSize: 13, color: rc.text2),
              ),
          ]),
          const SizedBox(height: 14),
        ],
        _FiltersPanel(f: f, data: data, onChanged: set),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Text(info, style: TextStyle(fontSize: 13, color: rc.text3)),
        ),
        if (items.isEmpty)
          EmptyBox('Nenhuma notícia encontrada${q.isNotEmpty ? ' para “$q”' : ''}. Tente outros termos ou amplie o período.')
        else
          CardGrid(children: [
            for (final a in visible)
              NewsCard(a: a, data: data, favorites: widget.state.favorites, onOpen: () => widget.onOpen(a)),
          ]),
        if (shown < items.length)
          Center(
            child: OutlinedButton(
              onPressed: () => setState(() => shown += 30),
              style: OutlinedButton.styleFrom(foregroundColor: rc.text, side: BorderSide(color: rc.border)),
              child: const Text('Carregar mais'),
            ),
          ),
      ],
    );
  }
}

/// Barra de filtros (.filters do site): períodos e seletores.
class _FiltersPanel extends StatelessWidget {
  final Filters f;
  final RadarData data;
  final ValueChanged<Filters> onChanged;
  const _FiltersPanel({required this.f, required this.data, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    final rc = context.rc;
    final outlets = data.outlets;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: rc.surface,
        border: Border.all(color: rc.border),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Container(
          padding: const EdgeInsets.only(bottom: 10),
          margin: const EdgeInsets.only(bottom: 10),
          decoration: BoxDecoration(border: Border(bottom: BorderSide(color: rc.border))),
          child: Wrap(spacing: 6, runSpacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: [
            Padding(
              padding: const EdgeInsets.only(right: 4),
              child: Text('PERÍODO',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, letterSpacing: .5, color: rc.text3)),
            ),
            for (final p in periods) _PeriodPill(label: p.$2, on: f.period == p.$1, onTap: () => onChanged(f.copyWith(period: p.$1))),
          ]),
        ),
        Wrap(spacing: 8, runSpacing: 8, crossAxisAlignment: WrapCrossAlignment.center, children: [
          if (f.isAll)
            _Select(
              value: f.category,
              options: [('', 'Todas as categorias'), for (final c in data.categories) (c.slug, c.name)],
              onChanged: (v) => onChanged(f.copyWith(category: v)),
            ),
          _Select(
            value: f.source,
            options: [('', 'Todas as fontes'), for (final o in outlets) (o.name, '${o.name} (${o.count})')],
            onChanged: (v) => onChanged(f.copyWith(source: v)),
          ),
          _Select(
            value: f.minRelevance,
            options: const [('', 'Qualquer relevância'), ('40', 'Relevância média ou alta'), ('60', 'Somente alta relevância')],
            onChanged: (v) => onChanged(f.copyWith(minRelevance: v)),
          ),
          _Check(label: 'Somente oficiais', value: f.onlyOfficial, onChanged: (v) => onChanged(f.copyWith(onlyOfficial: v))),
          if (f.fiscal)
            _Select(
              value: f.legalStage,
              options: [('', 'Qualquer estágio'), for (final e in stageLabels.entries) (e.key, e.value)],
              onChanged: (v) => onChanged(f.copyWith(legalStage: v)),
            ),
          if (f.isErp)
            _Select(
              value: f.erpDoc,
              options: [('', 'Qualquer documento'), for (final d in erpDocs) (d, d)],
              onChanged: (v) => onChanged(f.copyWith(erpDoc: v)),
            )
          else
            _Check(label: 'Exige ajuste em ERP', value: f.erp, onChanged: (v) => onChanged(f.copyWith(erp: v))),
          _Select(
            value: f.sort,
            options: [
              if (f.query.isNotEmpty) ('auto', 'Mais pertinentes à busca'),
              ('recent', 'Mais recentes'),
              ('relevance', 'Mais relevantes'),
            ],
            onChanged: (v) => onChanged(f.copyWith(sort: v)),
          ),
        ]),
      ]),
    );
  }
}

class _PeriodPill extends StatelessWidget {
  final String label;
  final bool on;
  final VoidCallback onTap;
  const _PeriodPill({required this.label, required this.on, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final rc = context.rc;
    return InkWell(
      borderRadius: BorderRadius.circular(999),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
        decoration: BoxDecoration(
          color: on ? rc.accent : rc.surface2,
          border: Border.all(color: on ? rc.accent : rc.border),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(label, style: TextStyle(fontSize: 13, color: on ? rc.accentInk : rc.text2)),
      ),
    );
  }
}

class _Select extends StatelessWidget {
  final String value;
  final List<(String, String)> options;
  final ValueChanged<String> onChanged;
  const _Select({required this.value, required this.options, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    final rc = context.rc;
    final current = options.any((o) => o.$1 == value) ? value : options.first.$1;
    return Container(
      height: 38,
      padding: const EdgeInsets.only(left: 12, right: 6),
      decoration: BoxDecoration(
        color: rc.surface,
        border: Border.all(color: rc.border),
        borderRadius: BorderRadius.circular(8),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: current,
          isDense: true,
          style: Theme.of(context).textTheme.bodyMedium!.copyWith(fontSize: 13.5, color: rc.text),
          dropdownColor: rc.surface,
          icon: Icon(Icons.expand_more, size: 18, color: rc.text3),
          items: [
            for (final o in options)
              DropdownMenuItem(
                value: o.$1,
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 220),
                  child: Text(o.$2, overflow: TextOverflow.ellipsis),
                ),
              ),
          ],
          onChanged: (v) => onChanged(v ?? ''),
        ),
      ),
    );
  }
}

class _Check extends StatelessWidget {
  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;
  const _Check({required this.label, required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    final rc = context.rc;
    return InkWell(
      onTap: () => onChanged(!value),
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 2),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          SizedBox(
            width: 22,
            height: 22,
            child: Checkbox(value: value, onChanged: (v) => onChanged(v ?? false), activeColor: rc.accent),
          ),
          const SizedBox(width: 6),
          Text(label, style: TextStyle(fontSize: 13.5, color: rc.text)),
        ]),
      ),
    );
  }
}

/// Favoritos salvos no celular (não existe no site).
class FavoritesView extends StatelessWidget {
  final AppState state;
  final ValueChanged<Article> onOpen;
  const FavoritesView({super.key, required this.state, required this.onOpen});

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: state.favorites,
        builder: (context, _) {
          final items = state.favorites.items;
          return ListView(padding: const EdgeInsets.fromLTRB(16, 20, 16, 32), children: [
            const PageHead(eyebrow: 'No celular', eyebrowColor: radarBlue, title: 'Favoritos'),
            if (items.isEmpty)
              const EmptyBox('Nenhum favorito ainda. Toque no marcador de uma notícia para salvá-la aqui.')
            else
              CardGrid(children: [
                for (final a in items)
                  NewsCard(a: a, data: state.data, favorites: state.favorites, onOpen: () => onOpen(a)),
              ]),
          ]);
        },
      );
}
