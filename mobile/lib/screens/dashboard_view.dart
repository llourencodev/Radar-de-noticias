import 'package:material_ui/material_ui.dart';

import '../app_state.dart';
import '../filters.dart';
import '../format.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/radar_widgets.dart';
import 'home_screen.dart';

/// "Painel de inteligência" do site: números, Mais relevantes, Oficiais, ERP, Fiscais, IA e Programação.
class DashboardView extends StatelessWidget {
  final AppState state;
  final ValueChanged<Route2> onGo;
  final ValueChanged<Article> onOpen;
  const DashboardView({super.key, required this.state, required this.onGo, required this.onOpen});

  @override
  Widget build(BuildContext context) {
    final data = state.data!;
    final d = Dashboard.from(data);
    final rc = context.rc;
    final st = data.status;
    const healthTxt = {'ok': 'Coleta normal', 'parcial': 'Algumas fontes com falha', 'falhas': 'Muitas fontes com falha'};
    final healthColor = switch (st.health) { 'ok' => rc.ok, 'parcial' => rc.warn, _ => rc.bad };

    Widget grid(List<Article> items, {bool lead = false}) => items.isEmpty
        ? const EmptyBox('Nenhuma notícia ainda. A primeira coleta pode levar alguns minutos.')
        : CardGrid(children: [
            for (var i = 0; i < items.length; i++)
              NewsCard(
                  a: items[i],
                  data: data,
                  favorites: state.favorites,
                  lead: lead && i == 0,
                  onOpen: () => onOpen(items[i])),
          ]);
    Widget list(List<Article> items) => items.isEmpty
        ? const EmptyBox('Nenhuma notícia ainda.')
        : Card(
            child: Column(children: [
              for (var i = 0; i < items.length; i++)
                NewsListItem(a: items[i], data: data, last: i == items.length - 1, onOpen: () => onOpen(items[i])),
            ]),
          );
    Widget section(String title, Widget body, Route2? more) => Padding(
          padding: const EdgeInsets.only(bottom: 26),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            SectionHead(title, onMore: more == null ? null : () => onGo(more)),
            body,
          ]),
        );

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 32),
      children: [
        PageHead(
          eyebrow: fullDate(DateTime.now()),
          title: 'Painel de inteligência',
          text: 'Notícias reais coletadas de fontes oficiais, imprensa e buscadores, organizadas por assunto.',
        ),
        _Kpis(children: [
          _Kpi('Notícias coletadas', thousands(d.total), 'sem contar duplicadas'),
          _Kpi('Publicadas hoje', thousands(d.today), 'pela data de publicação da fonte'),
          _Kpi(
            'Última atualização',
            st.lastFinished != null ? fmtDateTime(st.lastFinished!) : (data.generatedAt != null ? fmtDateTime(data.generatedAt!) : '—'),
            st.lastFinished != null ? '${st.lastNewItems} novas · a cada ${st.intervalMin} min' : 'a cada ${st.intervalMin} min',
            small: true,
          ),
          _Kpi(
            'Situação da coleta',
            healthTxt[st.health] ?? st.health,
            '${data.sourcesTotal} fontes ativas · ${data.sourcesFailing} com falha',
            small: true,
            dot: healthColor,
          ),
        ]),
        const SizedBox(height: 26),
        section('Mais relevantes', grid(d.top, lead: true), const Route2('todas', params: {'sort': 'relevance'})),
        section('Oficiais em destaque', grid(d.official), const Route2('todas', params: {'official': '1'})),
        if (d.erp.isNotEmpty) section('Notas técnicas e ajustes em ERP', grid(d.erp), const Route2('erp')),
        section('Últimas fiscais', list(d.fiscal), const Route2('c/fiscal')),
        section('Novidades de IA', list(d.ia), const Route2('c/ia')),
        section('Programação', list(d.programacao), const Route2('c/programacao')),
      ],
    );
  }
}

/// Mesmos cálculos de dashboard() em web/static-api.js.
class Dashboard {
  final int total, today;
  final List<Article> top, official, erp, fiscal, ia, programacao;
  Dashboard(this.total, this.today, this.top, this.official, this.erp, this.fiscal, this.ia, this.programacao);

  factory Dashboard.from(RadarData data, {DateTime? now}) {
    final n = now ?? DateTime.now();
    final list = data.list;
    final startIso = isoZ(DateTime(n.year, n.month, n.day));
    final todayDate = localDate(n);
    String ago(int days) => isoZ(n.subtract(Duration(days: days)));
    List<Article> take(Iterable<Article> it, int k) => it.take(k).toList();
    final recent = list; // já ordenada da mais nova para a mais antiga

    final top = list.where((a) => a.publishedAt != null && a.publishedAt!.compareTo(ago(3)) >= 0).toList()
      ..sort((a, b) {
        final c = b.relevance.compareTo(a.relevance);
        return c != 0 ? c : (b.publishedAt ?? '').compareTo(a.publishedAt ?? '');
      });
    return Dashboard(
      list.length,
      list
          .where((a) =>
              a.dateConfirmed && a.publishedAt != null && (a.publishedAt!.compareTo(startIso) >= 0 || a.publishedAt == todayDate))
          .length,
      take(top, 6),
      take(recent.where((a) => a.official && a.publishedAt != null && a.publishedAt!.compareTo(ago(7)) >= 0), 6),
      take(recent.where((a) => a.erpImpact), 6),
      take(recent.where((a) => a.categories.any((c) => c == 'fiscal' || c == 'reforma')), 6),
      take(recent.where((a) => a.categories.contains('ia')), 6),
      take(recent.where((a) => a.categories.contains('programacao')), 6),
    );
  }
}

class _Kpis extends StatelessWidget {
  final List<Widget> children;
  const _Kpis({required this.children});

  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, box) {
        final cols = box.maxWidth >= 720 ? 4 : 2;
        final w = (box.maxWidth - 12 * (cols - 1)) / cols;
        return Wrap(spacing: 12, runSpacing: 12, children: [for (final c in children) SizedBox(width: w, child: c)]);
      });
}

class _Kpi extends StatelessWidget {
  final String label, value, sub;
  final bool small;
  final Color? dot;
  const _Kpi(this.label, this.value, this.sub, {this.small = false, this.dot});

  @override
  Widget build(BuildContext context) {
    final rc = context.rc;
    return Container(
      constraints: const BoxConstraints(minHeight: 112),
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
      decoration: BoxDecoration(
        color: rc.surface,
        border: Border.all(color: rc.border),
        borderRadius: BorderRadius.circular(12),
        boxShadow: const [BoxShadow(color: Color(0x0D0F172A), blurRadius: 16, offset: Offset(0, 4))],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label, style: TextStyle(fontSize: 13, color: rc.text2)),
        const SizedBox(height: 4),
        Row(children: [
          if (dot != null) ...[
            Container(width: 10, height: 10, decoration: BoxDecoration(color: dot, shape: BoxShape.circle)),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Text(value,
                style: TextStyle(
                    fontSize: small ? 17 : 28, fontWeight: FontWeight.w700, letterSpacing: -.3, color: rc.text, height: 1.2)),
          ),
        ]),
        const SizedBox(height: 2),
        Text(sub, style: TextStyle(fontSize: 12, color: rc.text3)),
      ]),
    );
  }
}
