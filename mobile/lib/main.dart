import 'package:material_ui/material_ui.dart';

import 'app_state.dart';
import 'favorites.dart';
import 'radar_api.dart';
import 'screens/home_screen.dart';
import 'theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final state = AppState(api: RadarApi(), favorites: Favorites());
  await Future.wait([state.api.loadSettings(), state.favorites.load(), state.loadPrefs()]);
  runApp(RadarApp(state: state));
}

class RadarApp extends StatelessWidget {
  final AppState state;

  const RadarApp({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: state,
      builder: (context, _) => MaterialApp(
        title: 'Radar de Notícias',
        debugShowCheckedModeBanner: false,
        theme: buildTheme(RadarColors.light),
        darkTheme: buildTheme(RadarColors.dark),
        themeMode: switch (state.theme) { 'light' => ThemeMode.light, 'dark' => ThemeMode.dark, _ => ThemeMode.system },
        home: HomeScreen(state: state),
      ),
    );
  }
}
