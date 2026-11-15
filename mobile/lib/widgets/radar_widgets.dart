/// Componentes visuais do site (web/app.js + styles.css) em Flutter:
/// imagem da notícia, selos (badges), cartão, item de lista e cabeçalhos.
library;

import 'package:material_ui/material_ui.dart';

import '../favorites.dart';
import '../filters.dart';
import '../format.dart';
import '../models.dart';
import '../theme.dart';

/// Ícones das categorias (mesmos nomes do site).
IconData categoryIcon(String name) => switch (name) {
      'home' => Icons.home_outlined,
      'receipt' => Icons.receipt_long_outlined,
      'scale' => Icons.balance_outlined,
      'sparkles' => Icons.auto_awesome_outlined,
      'code' => Icons.code,
      'cpu' => Icons.memory_outlined,
      'briefcase' => Icons.work_outline,
      'radio' => Icons.sensors,
      'wrench' => Icons.build_outlined,
      'box' => Icons.inventory_2_outlined,
      _ => Icons.layers_outlined,
    };

/// Logotipos de categoria que o site usa no lugar da imagem (ex.: ACBr).
const categoryLogos = {'acbr-logo': 'assets/acbr-logo.png'};

Category catOf(RadarData? data, String? slug) =>
    data?.category(slug) ?? Category(slug: slug ?? '', name: slug ?? '', color: const Color(0xFF64748B));

Color mix(Color c, Color base, double amount) => Color.lerp(base, c, amount)!;

/// Símbolo do Radar (o mesmo SVG da marca do site).
class RadarMark extends StatelessWidget {
  final double size;
  final Color color;
  const RadarMark({super.key, this.size = 34, this.color = radarBlue});

  @override
  Widget build(BuildContext context) => CustomPaint(size: Size.square(size), painter: _RadarPainter(color));
}

class _RadarPainter extends CustomPainter {
  final Color color;
  _RadarPainter(this.color);

  @override
  void paint(Canvas canvas, Size size) {
    final k = size.width / 32;
    final c = Offset(16 * k, 16 * k);
    final stroke = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawCircle(c, 14 * k, stroke..strokeWidth = 1.5 * k..color = color.withValues(alpha: .35));
    canvas.drawCircle(c, 9 * k, stroke..strokeWidth = 2 * k..color = color);
    canvas.drawLine(c, Offset(26 * k, 9 * k), stroke..strokeWidth = 2.5 * k);
    canvas.drawCircle(c, 2.5 * k, Paint()..color = color);
  }

  @override
  bool shouldRepaint(_RadarPainter old) => old.color != color;
}

/// Imagem da notícia ou o quadro "sem imagem" do site (ícone da categoria + fonte).
class ArticleImage extends StatelessWidget {
  final Article article;
  final RadarData? data;
  final bool mini;
  const ArticleImage({super.key, required this.article, required this.data, this.mini = false});

  @override
  Widget build(BuildContext context) {
    final url = article.imageUrl;
    if (url == null || !(url.startsWith('https://') || url.startsWith('http://'))) return _noImage(context);
    return Image.network(
      url,
      fit: BoxFit.cover,
      width: double.infinity,
      height: double.infinity,
      gaplessPlayback: true,
      loadingBuilder: (context, child, progress) =>
          progress == null ? child : Container(color: context.rc.surface2),
      errorBuilder: (context, _, _) => _unavailable(context),
    );
  }

  Widget _noImage(BuildContext context) {
    final rc = context.rc;
    final c = catOf(data, article.primaryCategory ?? (article.categories.isEmpty ? null : article.categories.first));
    final logo = categoryLogos[c.icon];
    if (logo != null) {
      return Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
              begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [Color(0xFF1F2937), Color(0xFF0F172A)]),
        ),
        alignment: Alignment.center,
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          FractionallySizedBox(widthFactor: mini ? .7 : .3, child: Image.asset(logo, fit: BoxFit.contain)),
          if (!mini) ...[
            const SizedBox(height: 8),
            Text(article.source,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Color(0xFFE2E8F0), fontSize: 13, fontWeight: FontWeight.w600)),
          ],
        ]),
      );
    }
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [mix(c.color, rc.surface2, .16), mix(c.color, rc.surface2, .04)],
        ),
      ),
      padding: EdgeInsets.all(mini ? 8 : 16),
      alignment: mini ? Alignment.center : Alignment.bottomLeft,
      child: mini
          ? Icon(categoryIcon(c.icon), color: c.color, size: 22)
          : Column(mainAxisAlignment: MainAxisAlignment.end, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Icon(categoryIcon(c.icon), color: c.color, size: 30),
              const SizedBox(height: 6),
              Text(article.source, style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15, color: rc.text)),
              Text('Sem imagem da fonte', style: TextStyle(fontSize: 11.5, color: rc.text3)),
            ]),
    );
  }

  Widget _unavailable(BuildContext context) {
    final rc = context.rc;
    return Container(
      color: rc.surface2,
      padding: const EdgeInsets.all(12),
      alignment: Alignment.center,
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.layers_outlined, color: rc.text3, size: mini ? 22 : 30),
        if (!mini) Text('Imagem da fonte indisponível', style: TextStyle(fontSize: 11.5, color: rc.text3)),
      ]),
    );
  }
}

/// Selo arredondado (classe .badge do site).
class Badge2 extends StatelessWidget {
  final String text;
  final Color fg;
  final Color bg;
  final Color? border;
  const Badge2(this.text, {super.key, required this.fg, required this.bg, this.border});

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: border ?? Colors.transparent),
        ),
        child: Text(text, style: TextStyle(color: fg, fontSize: 11.5, fontWeight: FontWeight.w600, height: 1.4)),
      );
}

/// Os mesmos selos de web/app.js `badges(a, full)`.
class Badges extends StatelessWidget {
  final Article a;
  final RadarData? data;
  final bool full;
  const Badges({super.key, required this.a, required this.data, this.full = false});

  @override
  Widget build(BuildContext context) {
    final rc = context.rc;
    final dark = rc.isDark;
    final out = <Widget>[];
    final cats = a.shownCategories;
    for (var i = 0; i < cats.length; i++) {
      if (!full && i > 1) break;
      final c = catOf(data, cats[i]);
      out.add(Badge2(c.name,
          fg: c.color, bg: c.color.withValues(alpha: .09), border: c.color.withValues(alpha: .35)));
    }
    if (a.erpImpact) {
      out.add(Badge2('Ajuste em ERP${a.erpDocs.isNotEmpty ? ' · ${a.erpDocs.join(', ')}' : ''}',
          fg: dark ? const Color(0xFFFDBA74) : const Color(0xFF9A3412),
          bg: dark ? const Color(0x2EC2410C) : const Color(0xFFFFF1E6),
          border: dark ? const Color(0x59FDBA74) : const Color(0xFFFDBA74)));
    }
    if (a.isOfficial) {
      out.add(Badge2('Publicação oficial', fg: rc.official, bg: rc.officialSoft));
    } else if (a.docType == 'jornalistica') {
      out.add(Badge2('Notícia jornalística', fg: rc.text2, bg: Colors.transparent, border: rc.border));
    }
    if (a.legalStage != null) {
      final (fg, bg) = switch (a.legalStage) {
        'norma_em_vigor' => (const Color(0xFF14532D), const Color(0xFFDCFCE7)),
        'norma_publicada' => (const Color(0xFF1E3A8A), const Color(0xFFDBEAFE)),
        'projeto_de_lei' || 'consulta_publica' => (const Color(0xFF713F12), const Color(0xFFFEF9C3)),
        'nao_determinado' => (rc.text3, rc.surface2),
        _ => (const Color(0xFF7C2D12), const Color(0xFFFFEDD5)),
      };
      out.add(Badge2(stageLabels[a.legalStage] ?? a.legalStage!, fg: fg, bg: dark ? bg.withValues(alpha: .85) : bg));
    }
    if (a.isUpdate) out.add(const Badge2('Atualização', fg: Color(0xFF6D28D9), bg: Color(0xFFEDE9FE)));
    if (a.nature == 'opiniao') out.add(const Badge2('Opinião', fg: Color(0xFF9D174D), bg: Color(0xFFFCE7F3)));
    if (a.viaAggregator) out.add(Badge2('via Google Notícias', fg: rc.warn, bg: Colors.transparent, border: rc.border));
    if (a.groupSources > 1) {
      out.add(Badge2('${a.groupSources} fontes', fg: rc.text2, bg: Colors.transparent, border: rc.border));
    }
    return Wrap(spacing: 6, runSpacing: 6, children: out);
  }
}

/// Fonte + data, como `.meta` do site.
class ArticleMeta extends StatelessWidget {
  final Article a;
  const ArticleMeta(this.a, {super.key});

  @override
  Widget build(BuildContext context) {
    final rc = context.rc;
    final style = TextStyle(fontSize: 13, color: rc.text3);
    return Text.rich(
      TextSpan(style: style, children: [
        TextSpan(text: a.source, style: TextStyle(fontWeight: FontWeight.w600, color: rc.text2)),
        const TextSpan(text: '  '),
        if (!a.dateConfirmed || a.published == null)
          TextSpan(text: 'Data não confirmada', style: TextStyle(color: rc.warn))
        else
          TextSpan(text: pubDateText(a)),
      ]),
      maxLines: 2,
      overflow: TextOverflow.ellipsis,
    );
  }
}

/// Cartão de notícia (.card do site): imagem 16:9, selos, título, fonte/data, resumo e rodapé.
class NewsCard extends StatelessWidget {
  final Article a;
  final RadarData? data;
  final Favorites favorites;
  final VoidCallback onOpen;
  final bool lead;
  const NewsCard(
      {super.key, required this.a, required this.data, required this.favorites, required this.onOpen, this.lead = false});

  @override
  Widget build(BuildContext context) {
    final rc = context.rc;
    final c = catOf(data, a.primaryCategory);
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onOpen,
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Stack(children: [
            AspectRatio(aspectRatio: 16 / 9, child: ArticleImage(article: a, data: data)),
            Positioned(left: 0, right: 0, bottom: 0, child: Container(height: 3, color: c.color)),
          ]),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Badges(a: a, data: data),
              const SizedBox(height: 8),
              Text(a.title,
                  style: TextStyle(
                      fontSize: lead ? 21 : 16.5, height: 1.3, fontWeight: FontWeight.w700, color: rc.text)),
              const SizedBox(height: 8),
              ArticleMeta(a),
              if (a.summary != null) ...[
                const SizedBox(height: 8),
                Text(a.summary!,
                    maxLines: lead ? 6 : 4,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 14, height: 1.45, color: rc.text2)),
              ],
            ]),
          ),
          Container(
            decoration: BoxDecoration(border: Border(top: BorderSide(color: rc.border))),
            padding: const EdgeInsets.only(left: 16, right: 4),
            child: Row(children: [
              Expanded(
                child: InkWell(
                  onTap: onOpen,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    child: Text('Detalhes e impactos',
                        maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 13, color: rc.text2)),
                  ),
                ),
              ),
              FavoriteButton(a: a, favorites: favorites),
              InkWell(
                onTap: () => openOriginal(context, a.url),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Text('Abrir original',
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: rc.accent)),
                    const SizedBox(width: 4),
                    Icon(Icons.open_in_new, size: 15, color: rc.accent),
                  ]),
                ),
              ),
            ]),
          ),
        ]),
      ),
    );
  }
}

/// Item compacto (.list-item do site): miniatura 4:3 à esquerda.
class NewsListItem extends StatelessWidget {
  final Article a;
  final RadarData? data;
  final VoidCallback onOpen;
  final bool last;
  const NewsListItem({super.key, required this.a, required this.data, required this.onOpen, this.last = false});

  @override
  Widget build(BuildContext context) {
    final rc = context.rc;
    return InkWell(
      onTap: onOpen,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(border: last ? null : Border(bottom: BorderSide(color: rc.border))),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: SizedBox(width: 96, height: 72, child: ArticleImage(article: a, data: data, mini: true)),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(a.title,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 14.5, height: 1.3, fontWeight: FontWeight.w700, color: rc.text)),
              const SizedBox(height: 4),
              ArticleMeta(a),
              const SizedBox(height: 6),
              Badges(a: a, data: data),
            ]),
          ),
        ]),
      ),
    );
  }
}

class FavoriteButton extends StatelessWidget {
  final Article a;
  final Favorites favorites;
  const FavoriteButton({super.key, required this.a, required this.favorites});

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: favorites,
        builder: (context, _) {
          final fav = favorites.contains(a);
          return IconButton(
            tooltip: fav ? 'Remover dos favoritos' : 'Salvar nos favoritos',
            icon: Icon(fav ? Icons.bookmark : Icons.bookmark_border, size: 20),
            color: fav ? context.rc.accent : context.rc.text3,
            onPressed: () => favorites.toggle(a),
          );
        },
      );
}

/// Título de seção com linha grossa embaixo e "Ver tudo →" (.section-head do site).
class SectionHead extends StatelessWidget {
  final String title;
  final VoidCallback? onMore;
  const SectionHead(this.title, {super.key, this.onMore});

  @override
  Widget build(BuildContext context) {
    final rc = context.rc;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.only(bottom: 6),
      decoration: BoxDecoration(border: Border(bottom: BorderSide(color: rc.text, width: 2))),
      child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
        Expanded(
          child: Text(title.toUpperCase(),
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, letterSpacing: .6, color: rc.text)),
        ),
        if (onMore != null)
          InkWell(
            onTap: onMore,
            child: Padding(
              padding: const EdgeInsets.only(left: 8, top: 4),
              child: Text('Ver tudo →', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: rc.accent)),
            ),
          ),
      ]),
    );
  }
}

/// Cabeçalho de página (.page-head: sobretítulo, título e texto).
class PageHead extends StatelessWidget {
  final String eyebrow;
  final Color? eyebrowColor;
  final String title;
  final String? text;
  const PageHead({super.key, required this.eyebrow, required this.title, this.eyebrowColor, this.text});

  @override
  Widget build(BuildContext context) {
    final rc = context.rc;
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(eyebrow.toUpperCase(),
            style: TextStyle(
                fontSize: 12, letterSpacing: 1, fontWeight: FontWeight.w600, color: eyebrowColor ?? rc.text3)),
        const SizedBox(height: 2),
        Text(title, style: TextStyle(fontSize: 26, fontWeight: FontWeight.w700, letterSpacing: -.2, color: rc.text)),
        if (text != null) ...[
          const SizedBox(height: 4),
          Text(text!, style: TextStyle(color: rc.text2, fontSize: 14.5, height: 1.45)),
        ],
      ]),
    );
  }
}

/// Grade de cartões que se ajusta à largura (1 coluna no celular, mais no tablet).
class CardGrid extends StatelessWidget {
  final List<Widget> children;
  const CardGrid({super.key, required this.children});

  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, box) {
        final cols = (box.maxWidth / 340).floor().clamp(1, 4);
        if (cols == 1) {
          return Column(children: [
            for (final c in children) Padding(padding: const EdgeInsets.only(bottom: 16), child: c),
          ]);
        }
        final w = (box.maxWidth - 16 * (cols - 1)) / cols;
        return Wrap(spacing: 16, runSpacing: 16, children: [for (final c in children) SizedBox(width: w, child: c)]);
      });
}

class EmptyBox extends StatelessWidget {
  final String text;
  const EmptyBox(this.text, {super.key});

  @override
  Widget build(BuildContext context) {
    final rc = context.rc;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: rc.border),
        color: rc.surface,
      ),
      child: Text(text, textAlign: TextAlign.center, style: TextStyle(color: rc.text2)),
    );
  }
}
