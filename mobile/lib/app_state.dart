/// Estado do app: dados do Radar, carregamento, tema e favoritos.
library;

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'favorites.dart';
import 'models.dart';
import 'radar_api.dart';

class AppState extends ChangeNotifier {
  final RadarApi api;
  final Favorites favorites;

  RadarData? data;
  bool loading = false;
  String? error;

  /// '' (segue o sistema), 'light' ou 'dark' — como o botão de tema do site.
  String theme = '';

  AppState({required this.api, required this.favorites});

  static const _prefTheme = 'radar-theme';

  Future<void> loadPrefs() async {
    try {
      final p = await SharedPreferences.getInstance();
      theme = p.getString(_prefTheme) ?? '';
    } catch (_) {}
  }

  Future<void> setTheme(String t) async {
    theme = t;
    notifyListeners();
    try {
      final p = await SharedPreferences.getInstance();
      await p.setString(_prefTheme, t);
    } catch (_) {}
  }

  /// Abre com a cópia salva no aparelho e depois confere se há coleta nova.
  Future<void> start() async {
    final cached = await api.cached();
    if (cached != null) {
      data = cached;
      notifyListeners();
    }
    await refresh(quiet: cached != null);
  }

  /// Baixa os dados se houver coleta mais nova. Devolve uma mensagem para mostrar ao usuário.
  Future<String?> refresh({bool quiet = false, bool force = false}) async {
    if (loading) return null;
    loading = true;
    if (!quiet) error = null;
    notifyListeners();
    String? message;
    try {
      var changed = force || data == null;
      if (!changed) {
        final remote = await api.remoteGeneratedAt();
        changed = remote != null && remote != data!.generatedAt;
      }
      if (changed) {
        data = await api.fetch();
        error = null;
        message = 'Notícias atualizadas com a coleta mais recente.';
      } else {
        message = 'Você já está vendo a coleta mais recente. A coleta roda sozinha a cada hora.';
      }
    } catch (e) {
      if (data == null) {
        error = 'Não foi possível carregar as notícias.\n$e';
      } else {
        message = quiet ? null : 'Sem conexão com o Radar. Mostrando a última cópia salva.';
      }
    } finally {
      loading = false;
      notifyListeners();
    }
    return message;
  }

  Future<void> changeBaseUrl(String url) async {
    await api.setBaseUrl(url);
    data = null;
    notifyListeners();
    await refresh();
  }
}
