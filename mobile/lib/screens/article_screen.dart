import 'package:flutter/services.dart';
import 'package:material_ui/material_ui.dart';

import '../app_state.dart';
import '../format.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/radar_widgets.dart';

/// Detalhes da notícia (a janela que o site abre em "Detalhes e impactos").
class ArticleScreen extends StatelessWidget {
  final Article article;
  final AppState state;
  const ArticleScreen({super.key, required this.article, required this.state});

  @override
  Widget build(BuildContext context) {
    final a = article;
    final data = state.data;
    final rc = context.rc;
    final related = data?.related(a) ?? const <Article>[];
    final aiTag = a.aiSummary ? 'IA (${a.provider})' : 'regras automáticas';
    final providerLabel = a.aiSummary
        ? 'Resumo gerado por IA (${a.provider})'
        : a.summaryLang == 'en'
            ? 'Trecho original (inglês)'
            : 'Resumo automático com trechos da fonte';

    Widget h4(String title, [String? tag]) => Padding(
          padding: const EdgeInsets.only(top: 20, bottom: 8),
          child: Wrap(crossAxisAlignment: WrapCrossAlignment.center, spacing: 8, runSpacing: 4, children: [
            Text(title, style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: rc.text)),
            if (tag != null)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 1),
                decoration: BoxDecoration(color: rc.surface2, borderRadius: BorderRadius.circular(6), border: Border.all(color: rc.border)),
                child: Text(tag, style: TextStyle(fontSize: 11, color: rc.text3)),
              ),
          ]),
        );
    Widget bullets(List<String> items) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (final p in items)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('•  ', style: TextStyle(color: rc.text2)),
                  Expanded(child: Text(p, style: TextStyle(fontSize: 14.5, height: 1.45, color: rc.text))),
                ]),
              ),
          ],
        );
    Widget notice(String text, {bool erp = false}) => Container(
          margin: const EdgeInsets.only(top: 12),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: erp ? (rc.isDark ? const Color(0x2EC2410C) : const Color(0xFFFFF7ED)) : rc.accentSoft,
            borderRadius: BorderRadius.circular(10),
            border: Border(left: BorderSide(color: erp ? erpColor : rc.accent, width: 3)),
          ),
          child: Text(text, style: TextStyle(fontSize: 13.5, height: 1.45, color: rc.text)),
        );
    final hint = TextStyle(fontSize: 13, color: rc.text3, height: 1.45);

    return Scaffold(
      backgroundColor: rc.surface,
      body: CustomScrollView(slivers: [
        SliverAppBar(
          pinned: true,
          expandedHeight: MediaQuery.sizeOf(context).width * 9 / 16,
          backgroundColor: rc.surface,
          foregroundColor: rc.text,
          leading: Padding(
            padding: const EdgeInsets.all(6),
            child: IconButton.filledTonal(
              tooltip: 'Fechar',
              icon: const Icon(Icons.close),
              onPressed: () => Navigator.of(context).pop(),
            ),
          ),
          actions: [
            Padding(
              padding: const EdgeInsets.all(6),
              child: IconButton.filledTonal(
                tooltip: 'Copiar link',
                icon: const Icon(Icons.link),
                onPressed: () async {
                  await Clipboard.setData(ClipboardData(text: a.url));
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Link copiado')));
                  }
                },
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(6),
              child: ListenableBuilder(
                listenable: state.favorites,
                builder: (context, _) {
                  final fav = state.favorites.contains(a);
                  return IconButton.filledTonal(
                    tooltip: fav ? 'Remover dos favoritos' : 'Salvar nos favoritos',
                    icon: Icon(fav ? Icons.bookmark : Icons.bookmark_border),
                    onPressed: () => state.favorites.toggle(a),
                  );
                },
              ),
            ),
          ],
          flexibleSpace: FlexibleSpaceBar(background: ArticleImage(article: a, data: data)),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(20, 18, 20, 40),
          sliver: SliverList.list(children: [
            Badges(a: a, data: data, full: true),
            const SizedBox(height: 12),
            Text(a.title, style: TextStyle(fontSize: 23, height: 1.25, fontWeight: FontWeight.w700, color: rc.text)),
            const SizedBox(height: 8),
            ArticleMeta(a),
            if (a.collectedAt != null)
              Text('coletada em ${fmtDateTime(DateTime.parse(a.collectedAt!))}', style: hint),
            if (a.stageNote != null) notice(a.stageNote!),
            if (a.erpImpact)
              notice(
                  'Pode exigir ajuste em sistemas/ERP${a.erpDocs.isNotEmpty ? ' (${a.erpDocs.join(', ')})' : ''}: '
                  '${a.erpReason ?? 'mudança técnica'}. Confira na publicação oficial a versão, os prazos de homologação e de produção.',
                  erp: true),
            if (a.legalStage != null && a.legalStage != 'norma_em_vigor' && a.legislative)
              notice('Classificação automática. Confirme a situação da norma na publicação oficial antes de aplicar.'),
            if (a.summary != null) ...[
              h4('Resumo', providerLabel),
              Text(a.summary!, style: TextStyle(fontSize: 15, height: 1.5, color: rc.text)),
            ],
            if (a.summaryLang == 'en' && !a.aiSummary)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text('Texto da fonte em inglês. A tradução e o resumo em português ficam disponíveis ao ligar a IA.',
                    style: hint),
              ),
            if (a.keyPoints.isNotEmpty) ...[
              h4('Principais pontos', a.aiSummary ? 'IA' : 'frases da fonte'),
              bullets(a.keyPoints),
            ],
            if (a.impacts.isNotEmpty) ...[
              h4('Possíveis impactos para empresas e ERP', 'interpretação · $aiTag'),
              bullets(a.impacts),
            ],
            if (a.legalRefs.isNotEmpty) ...[
              h4('Normas citadas', 'extraídas do texto'),
              bullets(a.legalRefs),
            ],
            if (a.terms.isNotEmpty) ...[
              h4('Termos técnicos'),
              for (final t in a.terms)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text.rich(TextSpan(children: [
                    TextSpan(text: '${t.term}: ', style: const TextStyle(fontWeight: FontWeight.w700)),
                    TextSpan(text: t.explanation),
                  ]), style: TextStyle(fontSize: 14, height: 1.45, color: rc.text)),
                ),
            ],
            if (related.isNotEmpty) ...[
              h4('Mesma notícia e atualizações'),
              for (final r in related)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: InkWell(
                    onTap: () => openOriginal(context, r.url),
                    child: Text.rich(TextSpan(children: [
                      if (r.isUpdate) const TextSpan(text: 'Atualização: ', style: TextStyle(fontWeight: FontWeight.w700)),
                      TextSpan(text: r.title, style: TextStyle(color: rc.accent, decoration: TextDecoration.underline)),
                      TextSpan(text: ' — ${r.source}, ${r.publishedAt != null ? formatDate(r) : 'data não confirmada'}'),
                    ]), style: TextStyle(fontSize: 14, height: 1.45, color: rc.text)),
                  ),
                ),
            ],
            h4('Natureza do conteúdo'),
            Text(
              '${a.nature == 'opiniao' ? 'Opinião/coluna: reflete a visão do autor.' : 'Fato relatado pela fonte.'} '
              'Resumo, pontos e impactos são interpretações automáticas e não substituem a leitura do original.',
              style: hint,
            ),
            const SizedBox(height: 18),
            Align(
              alignment: Alignment.centerLeft,
              child: FilledButton.icon(
                onPressed: () => openOriginal(context, a.url),
                iconAlignment: IconAlignment.end,
                icon: const Icon(Icons.open_in_new, size: 18),
                label: const Text('Abrir publicação original'),
                style: FilledButton.styleFrom(
                  backgroundColor: rc.accent,
                  foregroundColor: rc.accentInk,
                  padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
              ),
            ),
            const SizedBox(height: 10),
            Text(
              'Fonte: ${a.sourceName ?? a.source}${a.validationStatus != null ? ' · status: ${a.validationStatus}' : ''}'
              '${a.viaAggregator ? ' · link original não confirmado (abre pelo Google Notícias)' : ''}',
              style: hint,
            ),
          ]),
        ),
      ]),
    );
  }
}
