import 'package:material_ui/material_ui.dart';

import 'favorites.dart';
import 'radar_api.dart';
import 'screens/home_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final api = RadarApi();
  final favorites = Favorites();
  await Future.wait([api.loadSettings(), favorites.load()]);
  runApp(RadarApp(api: api, favorites: favorites));
}

class RadarApp extends StatelessWidget {
  final RadarApi api;
  final Favorites favorites;

  const RadarApp({super.key, required this.api, required this.favorites});

  @override
  Widget build(BuildContext context) {
    const seed = Color(0xFF0F766E);
    return MaterialApp(
      title: 'Radar de Notícias',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: seed, useMaterial3: true, brightness: Brightness.light),
      darkTheme: ThemeData(colorSchemeSeed: seed, useMaterial3: true, brightness: Brightness.dark),
      home: HomeScreen(api: api, favorites: favorites),
    );
  }
}
