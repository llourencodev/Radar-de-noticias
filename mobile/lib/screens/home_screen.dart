import 'package:material_ui/material_ui.dart';

import '../favorites.dart';
import '../filters.dart';
import '../format.dart';
import '../models.dart';
import '../radar_api.dart';
import '../widgets/article_tile.dart';
import 'article_screen.dart';

class HomeScreen extends StatefulWidget {
  final RadarApi api;
  final Favorites favorites;

  const HomeScreen({super.key, required this.api, required this.favorites});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with WidgetsBindingObserver {
  RadarData? _data;
  bool _loading = true;
  String? _error;
  int _tab = 0;
  Filters _filters = const Filters();
  bool _searching = false;
  final _search = TextEditingController();
  final _scroll = ScrollController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _start();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _search.dispose();
    _scroll.dispose();
    super.dispose();
  }

  // ao voltar para o app, confere se o GitHub publicou uma coleta nova
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && !_loading) _refresh(quiet: true);
  }

  Future<void> _start() async {
    final cached = await widget.api.cached();
    if (!mounted) return;
    if (cached != null) setState(() => _data = cached);
    await _refresh(quiet: cached != null);
  }

  /// Baixa os dados se houver coleta mais nova. [quiet]: erros não substituem a lista já exibida.
  Future<void> _refresh({bool quiet = false, bool force = false}) async {
    setState(() {
      _loading = true;
      if (!quiet) _error = null;
    });
    try {
      var changed = force || _data == null;
      if (!changed) {
        final remote = await widget.api.remoteGeneratedAt();
        changed = remote != null && remote != _data!.generatedAt;
      }
      if (changed) {
        final data = await widget.api.fetch();
        if (!mounted) return;
        setState(() {
          _data = data;
          _error = null;
        });
      }
    } catch (e) {
      if (!mounted) return;
      if (_data == null) {
        setState(() => _error = 'Não foi possível carregar as notícias.\n$e');
      } else if (!quiet) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Sem conexão com o Radar. Mostrando a última cópia salva.')));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _setFilters(Filters f) {
    setState(() => _filters = f);
    if (_scroll.hasClients) _scroll.jumpTo(0);
  }

  void _openArticle(Article a) {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => ArticleScreen(article: a, data: _data, favorites: widget.favorites),
    ));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: _tab == 0 ? _newsAppBar() : AppBar(title: const Text('Favoritos')),
      body: _tab == 0 ? _newsBody() : _favoritesBody(),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: [
          const NavigationDestination(icon: Icon(Icons.newspaper_outlined), selectedIcon: Icon(Icons.newspaper), label: 'Notícias'),
          NavigationDestination(
            icon: ListenableBuilder(
              listenable: widget.favorites,
              builder: (_, _) => Badge(
                isLabelVisible: widget.favorites.length > 0,
                label: Text('${widget.favorites.length}'),
                child: const Icon(Icons.bookmark_border),
              ),
            ),
            selectedIcon: const Icon(Icons.bookmark),
            label: 'Favoritos',
          ),
        ],
      ),
    );
  }

  // ------------------------------------------------------------------ Notícias

  PreferredSizeWidget _newsAppBar() {
    if (_searching) {
      return AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
            _search.clear();
            setState(() => _searching = false);
            _setFilters(_filters.copyWith(query: ''));
          },
        ),
        title: TextField(
          controller: _search,
          autofocus: true,
          textInputAction: TextInputAction.search,
          decoration: const InputDecoration(hintText: 'Buscar notícias', border: InputBorder.none),
          onChanged: (q) => _setFilters(_filters.copyWith(query: q)),
        ),
        actions: [
          if (_search.text.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.close),
              onPressed: () {
                _search.clear();
                _setFilters(_filters.copyWith(query: ''));
              },
            ),
        ],
      );
    }
    final gen = _data?.generatedAt;
    return AppBar(
      title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Radar de Notícias'),
        if (gen != null)
          Text('Coleta de ${formatGenerated(gen)}', style: Theme.of(context).textTheme.bodySmall),
      ]),
      actions: [
        IconButton(tooltip: 'Buscar', icon: const Icon(Icons.search), onPressed: () => setState(() => _searching = true)),
        PopupMenuButton<String>(
          onSelected: (v) {
            if (v == 'refresh') _refresh(force: true);
            if (v == 'settings') _settings();
          },
          itemBuilder: (_) => const [
            PopupMenuItem(value: 'refresh', child: Text('Baixar notícias de novo')),
            PopupMenuItem(value: 'settings', child: Text('Endereço do Radar')),
          ],
        ),
      ],
      bottom: _loading ? const PreferredSize(preferredSize: Size.fromHeight(2), child: LinearProgressIndicator(minHeight: 2)) : null,
    );
  }

  Widget _newsBody() {
    final data = _data;
    if (data == null) {
      if (_error != null) return _message(Icons.cloud_off, _error!, action: ('Tentar de novo', () => _refresh()));
      return const Center(child: CircularProgressIndicator());
    }
    final items = _filters.apply(data.list);
    return Column(children: [
      _categoryBar(data),
      _filterBar(),
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 4),
        child: Align(
          alignment: Alignment.centerLeft,
          child: Text('${items.length} notícia${items.length == 1 ? '' : 's'}',
              style: Theme.of(context).textTheme.bodySmall),
        ),
      ),
      Expanded(
        child: RefreshIndicator(
          onRefresh: () => _refresh(),
          child: items.isEmpty
              ? ListView(children: [
                  const SizedBox(height: 80),
                  _message(Icons.search_off, 'Nenhuma notícia encontrada.\nTente outros termos ou amplie o período.'),
                ])
              : ListView.builder(
                  controller: _scroll,
                  padding: const EdgeInsets.only(bottom: 16),
                  itemCount: items.length,
                  itemBuilder: (_, i) => ArticleTile(
                    article: items[i],
                    data: data,
                    favorites: widget.favorites,
                    onTap: () => _openArticle(items[i]),
                  ),
                ),
        ),
      ),
    ]);
  }

  Widget _categoryBar(RadarData data) {
    final counts = <String, int>{};
    for (final a in data.list) {
      for (final c in a.categories) {
        counts[c] = (counts[c] ?? 0) + 1;
      }
    }
    final chips = <Widget>[
      _catChip('todas', 'Todas', null, data.list.length),
      for (final c in data.categories) _catChip(c.slug, c.name, c.color, counts[c.slug] ?? 0),
    ];
    return SizedBox(
      height: 52,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        itemCount: chips.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (_, i) => chips[i],
      ),
    );
  }

  Widget _catChip(String slug, String name, Color? color, int count) {
    final selected = _filters.category == slug;
    return ChoiceChip(
      label: Text('$name ($count)'),
      selected: selected,
      selectedColor: color?.withValues(alpha: 0.18),
      side: color != null && selected ? BorderSide(color: color) : null,
      onSelected: (_) => _setFilters(_filters.copyWith(category: slug)),
    );
  }

  Widget _filterBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 4),
      child: Row(children: [
        PopupMenuButton<String>(
          tooltip: 'Período de publicação',
          initialValue: _filters.period,
          onSelected: (v) => _setFilters(_filters.copyWith(period: v)),
          itemBuilder: (_) => [for (final p in periods) PopupMenuItem(value: p.$1, child: Text(p.$2))],
          child: Chip(
            avatar: const Icon(Icons.schedule, size: 18),
            label: Text(_filters.period.isEmpty ? 'Período: tudo' : periodLabel(_filters.period)),
            deleteIcon: const Icon(Icons.arrow_drop_down),
            onDeleted: null,
          ),
        ),
        const SizedBox(width: 8),
        FilterChip(
          label: const Text('Somente oficiais'),
          selected: _filters.onlyOfficial,
          onSelected: (v) => _setFilters(_filters.copyWith(onlyOfficial: v)),
        ),
      ]),
    );
  }

  Future<void> _settings() async {
    final ctrl = TextEditingController(text: widget.api.baseUrl);
    final url = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Endereço do Radar'),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Endereço do site publicado no GitHub Pages. O app lê as notícias de data/radar.json.'),
          const SizedBox(height: 12),
          TextField(controller: ctrl, keyboardType: TextInputType.url, decoration: const InputDecoration(border: OutlineInputBorder())),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, defaultBaseUrl), child: const Text('Padrão')),
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(ctx, ctrl.text), child: const Text('Salvar')),
        ],
      ),
    );
    ctrl.dispose();
    if (url == null || !mounted) return;
    await widget.api.setBaseUrl(url);
    setState(() => _data = null);
    await _refresh();
  }

  // ------------------------------------------------------------------ Favoritos

  Widget _favoritesBody() {
    return ListenableBuilder(
      listenable: widget.favorites,
      builder: (context, _) {
        final items = widget.favorites.items;
        if (items.isEmpty) {
          return _message(Icons.bookmark_border, 'Nenhum favorito ainda.\nToque no marcador de uma notícia para salvá-la aqui.');
        }
        return ListView.builder(
          padding: const EdgeInsets.symmetric(vertical: 8),
          itemCount: items.length,
          itemBuilder: (_, i) => ArticleTile(
            article: items[i],
            data: _data,
            favorites: widget.favorites,
            onTap: () => _openArticle(items[i]),
          ),
        );
      },
    );
  }

  Widget _message(IconData icon, String text, {(String, VoidCallback)? action}) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, size: 48, color: theme.colorScheme.outline),
          const SizedBox(height: 12),
          Text(text, textAlign: TextAlign.center, style: theme.textTheme.bodyLarge),
          if (action != null) ...[
            const SizedBox(height: 16),
            FilledButton(onPressed: action.$2, child: Text(action.$1)),
          ],
        ]),
      ),
    );
  }
}
