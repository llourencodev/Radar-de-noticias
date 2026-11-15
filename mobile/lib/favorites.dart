/// Favoritos salvos só no aparelho. Guardamos a notícia inteira para ela continuar
/// aparecendo mesmo depois de sair da janela de 90 dias publicada no site.
library;

import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'models.dart';

class Favorites extends ChangeNotifier {
  static const _key = 'radar_favorites_v1';

  final Map<int, Article> _items = {};
  final Map<int, DateTime> _savedAt = {};

  bool contains(Article a) => _items.containsKey(a.id);

  /// Mais recentes primeiro (pela hora em que foram salvas).
  List<Article> get items {
    final list = _items.values.toList();
    list.sort((a, b) => _savedAt[b.id]!.compareTo(_savedAt[a.id]!));
    return list;
  }

  int get length => _items.length;

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null) return;
    try {
      for (final e in (jsonDecode(raw) as List).whereType<Map>()) {
        final a = Article.fromJson((e['article'] as Map).cast<String, dynamic>());
        _items[a.id] = a;
        _savedAt[a.id] = DateTime.tryParse((e['saved_at'] as String?) ?? '') ?? DateTime.now();
      }
    } catch (_) {/* arquivo corrompido: começa vazio */}
    notifyListeners();
  }

  Future<void> toggle(Article a) async {
    if (_items.remove(a.id) != null) {
      _savedAt.remove(a.id);
    } else {
      _items[a.id] = a;
      _savedAt[a.id] = DateTime.now();
    }
    notifyListeners();
    await _save();
  }

  Future<void> _save() async {
    final prefs = await SharedPreferences.getInstance();
    final data = _items.values
        .map((a) => {'saved_at': _savedAt[a.id]!.toIso8601String(), 'article': a.raw})
        .toList();
    await prefs.setString(_key, jsonEncode(data));
  }
}
