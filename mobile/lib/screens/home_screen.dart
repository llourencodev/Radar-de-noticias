import 'package:material_ui/material_ui.dart';

import '../app_state.dart';
import '../format.dart';
import '../models.dart';
import '../radar_api.dart';
import '../theme.dart';
import '../widgets/radar_widgets.dart';
import 'article_screen.dart';
import 'dashboard_view.dart';
import 'list_view.dart';

/// Página atual, como as rotas do site (#/, #/c/fiscal, #/erp, #/todas) + Favoritos do app.
class Route2 {
  final String path; // dashboard | c/<slug> | erp | todas | favoritos
  final String query;
  final Map<String, String> params;
  const Route2(this.path, {this.query = '', this.params = const {}});

  static const dashboard = Route2('dashboard');
}

/// Estrutura do site: menu lateral escuro (no celular abre pelo ☰), barra de busca no topo e o conteúdo.
class HomeScreen extends StatefulWidget {
  final AppState state;
  const HomeScreen({super.key, required this.state});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with WidgetsBindingObserver {
  final _scaffold = GlobalKey<ScaffoldState>();
  final _search = TextEditingController();
  Route2 _route = Route2.dashboard;
  final _history = <Route2>[];

  AppState get s => widget.state;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    s.start();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _search.dispose();
    super.dispose();
  }

  // ao voltar para o app, confere se o GitHub publicou uma coleta nova (como o site faz a cada 5 min)
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      s.refresh(quiet: true);
    }
  }

  void go(Route2 r) {
    if (_scaffold.currentState?.isDrawerOpen ?? false) Navigator.of(context).pop();
    setState(() {
      if (r.path != _route.path || r.query != _route.query) _history.add(_route);
      _route = r;
      _search.text = r.query;
    });
  }

  void _back() {
    setState(() {
      _route = _history.isNotEmpty ? _history.removeLast() : Route2.dashboard;
      _search.text = _route.query;
    });
  }

  void openArticle(Article a) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => ArticleScreen(article: a, state: s)));
  }

  void _submitSearch(String q) {
    final base = _route.path.startsWith('c/') ? _route.path : 'todas';
    go(Route2(base, query: q.trim()));
  }

  Future<void> _refresh() async {
    final msg = await s.refresh(force: false);
    if (msg != null && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: s,
      builder: (context, _) {
        final rc = context.rc;
        return PopScope(
          canPop: _route.path == 'dashboard' && _history.isEmpty,
          onPopInvokedWithResult: (didPop, _) {
            if (!didPop) _back();
          },
          child: Scaffold(
            key: _scaffold,
            drawer: _Sidebar(state: s, route: _route, onGo: go),
            appBar: AppBar(
              titleSpacing: 0,
              toolbarHeight: 64,
              leading: IconButton(
                tooltip: 'Abrir menu',
                icon: const Icon(Icons.menu),
                onPressed: () => _scaffold.currentState?.openDrawer(),
              ),
              title: _SearchBox(controller: _search, onSubmit: _submitSearch),
              actions: [
                IconButton(
                  tooltip: 'Atualizar agora',
                  onPressed: s.loading ? null : _refresh,
                  icon: s.loading
                      ? SizedBox(
                          width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: rc.accent))
                      : Icon(Icons.refresh, color: rc.accent),
                ),
                PopupMenuButton<String>(
                  onSelected: (v) {
                    if (v == 'theme') {
                      final dark = rc.isDark;
                      s.setTheme(dark ? 'light' : 'dark');
                    }
                    if (v == 'url') _settings();
                  },
                  itemBuilder: (_) => [
                    PopupMenuItem(value: 'theme', child: Text(rc.isDark ? 'Tema claro' : 'Tema escuro')),
                    const PopupMenuItem(value: 'url', child: Text('Endereço do Radar')),
                  ],
                ),
              ],
            ),
            body: _body(),
          ),
        );
      },
    );
  }

  Widget _body() {
    final data = s.data;
    if (data == null) {
      if (s.error != null) {
        return _Message(icon: Icons.cloud_off, text: s.error!, action: ('Tentar de novo', () => s.refresh()));
      }
      return const Center(child: CircularProgressIndicator());
    }
    final r = _route;
    final Widget page;
    if (r.path == 'dashboard') {
      page = DashboardView(state: s, onGo: go, onOpen: openArticle);
    } else if (r.path == 'favoritos') {
      page = FavoritesView(state: s, onOpen: openArticle);
    } else {
      final view = r.path.startsWith('c/') ? r.path.substring(2) : r.path;
      page = NewsListView(
        key: ValueKey('${r.path}|${r.query}|${r.params}'),
        state: s,
        view: view,
        query: r.query,
        params: r.params,
        onOpen: openArticle,
        onSearch: (q) => go(Route2('todas', query: q)),
      );
    }
    return RefreshIndicator(onRefresh: _refresh, child: page);
  }

  Future<void> _settings() async {
    final ctrl = TextEditingController(text: s.api.baseUrl);
    final url = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Endereço do Radar'),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Endereço do site publicado no GitHub Pages. O app lê as notícias de data/radar.json.'),
          const SizedBox(height: 12),
          TextField(
              controller: ctrl,
              keyboardType: TextInputType.url,
              decoration: const InputDecoration(border: OutlineInputBorder())),
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
    await s.changeBaseUrl(url);
  }
}

class _SearchBox extends StatelessWidget {
  final TextEditingController controller;
  final ValueChanged<String> onSubmit;
  const _SearchBox({required this.controller, required this.onSubmit});

  @override
  Widget build(BuildContext context) {
    final rc = context.rc;
    return Container(
      height: 42,
      decoration: BoxDecoration(
        color: rc.surface,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: rc.border),
        boxShadow: const [BoxShadow(color: Color(0x0F0F172A), blurRadius: 16, offset: Offset(0, 4))],
      ),
      padding: const EdgeInsets.only(left: 14, right: 4),
      child: Row(children: [
        Icon(Icons.search, size: 18, color: rc.text3),
        const SizedBox(width: 8),
        Expanded(
          child: TextField(
            controller: controller,
            textInputAction: TextInputAction.search,
            onSubmitted: onSubmit,
            style: TextStyle(fontSize: 15, color: rc.text),
            decoration: InputDecoration(
              isCollapsed: true,
              border: InputBorder.none,
              hintText: 'Pesquisar notícias, normas, tecnologias...',
              hintStyle: TextStyle(color: rc.text3, fontSize: 14),
            ),
          ),
        ),
        ValueListenableBuilder(
          valueListenable: controller,
          builder: (context, v, _) => v.text.isEmpty
              ? const SizedBox.shrink()
              : IconButton(
                  visualDensity: VisualDensity.compact,
                  icon: Icon(Icons.close, size: 18, color: rc.text3),
                  onPressed: () {
                    controller.clear();
                    onSubmit('');
                  },
                ),
        ),
      ]),
    );
  }
}

/// Menu lateral escuro do site: marca, Painel, Categorias com contagem, Destaques.
class _Sidebar extends StatelessWidget {
  final AppState state;
  final Route2 route;
  final ValueChanged<Route2> onGo;
  const _Sidebar({required this.state, required this.route, required this.onGo});

  @override
  Widget build(BuildContext context) {
    final rc = context.rc;
    final data = state.data;
    final counts = data?.countByCategory ?? const <String, int>{};
    final erpTotal = data?.list.where((a) => a.erpImpact).length;
    Widget label(String t) => Padding(
          padding: const EdgeInsets.fromLTRB(12, 14, 12, 6),
          child: Text(t.toUpperCase(), style: TextStyle(fontSize: 11, letterSpacing: .9, color: rc.sideMuted)),
        );
    Widget item(String path, String text, IconData icon, {Color? color, int? count, Widget? leading}) {
      final active = route.path == path && route.query.isEmpty;
      return Container(
        margin: const EdgeInsets.symmetric(vertical: 1),
        decoration: BoxDecoration(
          color: active ? rc.sideActive : null,
          borderRadius: BorderRadius.circular(8),
          border: active ? Border(left: BorderSide(color: color ?? radarBlue, width: 3)) : null,
        ),
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap: () => onGo(Route2(path)),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Row(children: [
              leading ?? Icon(icon, size: 18, color: color ?? const Color(0xFF94A3B8)),
              const SizedBox(width: 10),
              Expanded(
                child: Text(text,
                    style: TextStyle(fontSize: 14, color: active ? Colors.white : rc.sideText),
                    overflow: TextOverflow.ellipsis),
              ),
              if (count != null) Text('$count', style: TextStyle(fontSize: 12, color: rc.sideMuted)),
            ]),
          ),
        ),
      );
    }

    return Drawer(
      backgroundColor: rc.sideBg,
      width: 284,
      shape: const RoundedRectangleBorder(),
      child: SafeArea(
        child: ListView(padding: const EdgeInsets.fromLTRB(12, 18, 12, 12), children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(10, 4, 10, 18),
            child: Row(children: [
              const RadarMark(size: 34),
              const SizedBox(width: 10),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text.rich(const TextSpan(children: [
                    TextSpan(text: 'Radar', style: TextStyle(fontWeight: FontWeight.w700)),
                    TextSpan(text: ' Inteligente'),
                  ]), style: const TextStyle(color: Colors.white, fontSize: 17)),
                  Text('de Notícias', style: TextStyle(fontSize: 12, color: rc.sideMuted)),
                ]),
              ),
            ]),
          ),
          item('dashboard', 'Painel', Icons.home_outlined),
          label('Categorias'),
          for (final c in data?.categories ?? const <Category>[])
            item('c/${c.slug}', c.name, categoryIcon(c.icon),
                color: c.color,
                count: counts[c.slug] ?? 0,
                leading: categoryLogos[c.icon] != null
                    ? SizedBox(width: 18, height: 18, child: Image.asset(categoryLogos[c.icon]!))
                    : null),
          label('Destaques'),
          item('erp', 'Notas técnicas / ERP', Icons.build_outlined, color: erpColor, count: erpTotal),
          item('todas', 'Todas as notícias', Icons.layers_outlined, count: data?.list.length),
          label('No celular'),
          ListenableBuilder(
            listenable: state.favorites,
            builder: (context, _) =>
                item('favoritos', 'Favoritos', Icons.bookmark_border, color: radarBlue, count: state.favorites.length),
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.only(top: 12),
            decoration: const BoxDecoration(border: Border(top: BorderSide(color: Color(0xFF1E293B)))),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                if (data?.generatedAt != null)
                  Text('Coleta de ${fmtDateTime(data!.generatedAt!)}', style: TextStyle(fontSize: 12, color: rc.sideMuted)),
                const SizedBox(height: 8),
                Text('Developed by', style: TextStyle(fontSize: 11, color: rc.sideMuted)),
                Text('Leandro Lourenço', style: TextStyle(fontSize: 13, color: rc.sideText, fontWeight: FontWeight.w600)),
              ]),
            ),
          ),
        ]),
      ),
    );
  }
}

class _Message extends StatelessWidget {
  final IconData icon;
  final String text;
  final (String, VoidCallback)? action;
  const _Message({required this.icon, required this.text, this.action});

  @override
  Widget build(BuildContext context) {
    final rc = context.rc;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, size: 48, color: rc.text3),
          const SizedBox(height: 12),
          Text(text, textAlign: TextAlign.center, style: TextStyle(fontSize: 15, color: rc.text2)),
          if (action != null) ...[
            const SizedBox(height: 16),
            FilledButton(onPressed: action!.$2, child: Text(action!.$1)),
          ],
        ]),
      ),
    );
  }
}
