/// Cores e tipografia copiadas de web/styles.css (tema claro e escuro do site).
library;

import 'package:material_ui/material_ui.dart';

@immutable
class RadarColors extends ThemeExtension<RadarColors> {
  final Color bg, surface, surface2, border, text, text2, text3, accent, accentInk, accentSoft;
  final Color sideBg, sideText, sideMuted, sideActive, ok, warn, bad, official, officialSoft;

  const RadarColors({
    required this.bg,
    required this.surface,
    required this.surface2,
    required this.border,
    required this.text,
    required this.text2,
    required this.text3,
    required this.accent,
    required this.accentInk,
    required this.accentSoft,
    required this.sideBg,
    required this.sideText,
    required this.sideMuted,
    required this.sideActive,
    required this.ok,
    required this.warn,
    required this.bad,
    required this.official,
    required this.officialSoft,
  });

  static const light = RadarColors(
    bg: Color(0xFFF4F6F9),
    surface: Color(0xFFFFFFFF),
    surface2: Color(0xFFF8FAFC),
    border: Color(0xFFE2E8F0),
    text: Color(0xFF0F172A),
    text2: Color(0xFF475569),
    text3: Color(0xFF64748B),
    accent: Color(0xFF0B5CAD),
    accentInk: Color(0xFFFFFFFF),
    accentSoft: Color(0xFFE0EDFB),
    sideBg: Color(0xFF0B1220),
    sideText: Color(0xFFCBD5E1),
    sideMuted: Color(0xFF64748B),
    sideActive: Color(0xFF16233B),
    ok: Color(0xFF15803D),
    warn: Color(0xFFB45309),
    bad: Color(0xFFB91C1C),
    official: Color(0xFF0F766E),
    officialSoft: Color(0xFFCCFBF1),
  );

  static const dark = RadarColors(
    bg: Color(0xFF0B1018),
    surface: Color(0xFF121A26),
    surface2: Color(0xFF0F1620),
    border: Color(0xFF233041),
    text: Color(0xFFE5EDF6),
    text2: Color(0xFFA9B6C6),
    text3: Color(0xFF8392A5),
    accent: Color(0xFF4EA3F5),
    accentInk: Color(0xFF06121F),
    accentSoft: Color(0xFF13283F),
    sideBg: Color(0xFF070B12),
    sideText: Color(0xFFCBD5E1),
    sideMuted: Color(0xFF64748B),
    sideActive: Color(0xFF132037),
    ok: Color(0xFF22C55E),
    warn: Color(0xFFF59E0B),
    bad: Color(0xFFF87171),
    official: Color(0xFF2DD4BF),
    officialSoft: Color(0xFF0B2E2B),
  );

  bool get isDark => bg == dark.bg;

  @override
  RadarColors copyWith() => this;

  @override
  RadarColors lerp(ThemeExtension<RadarColors>? other, double t) => t < .5 ? this : (other as RadarColors? ?? this);
}

extension RadarTheme on BuildContext {
  RadarColors get rc => Theme.of(this).extension<RadarColors>()!;
}

const radarBlue = Color(0xFF38BDF8); // símbolo do Radar
const erpColor = Color(0xFFC2410C);
const allColor = Color(0xFF0B5CAD);

ThemeData buildTheme(RadarColors c) {
  final brightness = c.isDark ? Brightness.dark : Brightness.light;
  final scheme = ColorScheme.fromSeed(
    seedColor: c.accent,
    brightness: brightness,
    primary: c.accent,
    onPrimary: c.accentInk,
    surface: c.surface,
    onSurface: c.text,
    outline: c.border,
  );
  return ThemeData(
    useMaterial3: true,
    fontFamily: const String.fromEnvironment('RADAR_FONT', defaultValue: 'Roboto'),
    brightness: brightness,
    colorScheme: scheme,
    scaffoldBackgroundColor: c.bg,
    extensions: [c],
    dividerColor: c.border,
    appBarTheme: AppBarTheme(
      backgroundColor: c.bg,
      foregroundColor: c.text,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
      shape: Border(bottom: BorderSide(color: c.border)),
    ),
    cardTheme: CardThemeData(
      color: c.surface,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: BorderSide(color: c.border)),
    ),
    snackBarTheme: const SnackBarThemeData(behavior: SnackBarBehavior.floating),
  );
}
