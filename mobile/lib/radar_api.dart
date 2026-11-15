/// Leitura dos dados publicados pelo Radar no GitHub Pages.
///
/// O app não tem servidor próprio: baixa `data/radar.json` (o mesmo arquivo que o site usa),
/// guarda uma cópia no aparelho para abrir rápido e funcionar sem internet, e só baixa de novo
/// quando `data/status.json` indica uma coleta mais nova.
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'models.dart';

/// Endereço padrão do site. Pode ser trocado na compilação
/// (`--dart-define=RADAR_URL=https://...`) ou na tela de configurações do app.
const String defaultBaseUrl = String.fromEnvironment(
  'RADAR_URL',
  defaultValue: 'https://llourencodev.github.io/Radar-de-noticias/',
);

class RadarApi {
  static const _prefUrl = 'radar_base_url';
  static const _cacheName = 'radar.json';

  final http.Client _client;
  String baseUrl;

  RadarApi({http.Client? client, this.baseUrl = defaultBaseUrl}) : _client = client ?? http.Client();

  static String normalizeUrl(String url) {
    var u = url.trim();
    if (u.isEmpty) return defaultBaseUrl;
    if (!u.startsWith('http://') && !u.startsWith('https://')) u = 'https://$u';
    if (u.endsWith('/index.html')) u = u.substring(0, u.length - 'index.html'.length);
    return u.endsWith('/') ? u : '$u/';
  }

  Future<void> loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    baseUrl = normalizeUrl(prefs.getString(_prefUrl) ?? defaultBaseUrl);
  }

  Future<void> setBaseUrl(String url) async {
    baseUrl = normalizeUrl(url);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_prefUrl, baseUrl);
    await _deleteCache();
  }

  Uri _uri(String path) =>
      Uri.parse('$baseUrl$path').replace(queryParameters: {'t': '${DateTime.now().millisecondsSinceEpoch}'});

  Future<String> _get(String path) async {
    final r = await _client.get(_uri(path), headers: {'Cache-Control': 'no-cache'}).timeout(const Duration(seconds: 60));
    if (r.statusCode == 404) {
      throw RadarException('O endereço $baseUrl não tem $path (erro 404). '
          'Confira o endereço no menu ⋮ > Endereço do Radar (maiúsculas e minúsculas contam).');
    }
    if (r.statusCode != 200) {
      throw RadarException('Não foi possível ler $path (erro ${r.statusCode}).');
    }
    return utf8.decode(r.bodyBytes);
  }

  /// Data da coleta mais recente publicada (arquivo pequeno, para checar novidades).
  Future<DateTime?> remoteGeneratedAt() async {
    final j = jsonDecode(await _get('data/status.json')) as Map<String, dynamic>;
    return DateTime.tryParse((j['generated_at'] as String?) ?? '');
  }

  /// Baixa e interpreta o radar.json completo (a interpretação roda fora da tela).
  Future<RadarData> fetch() async {
    final body = await _get('data/radar.json');
    final data = await compute(_parse, body);
    await _writeCache(body);
    return data;
  }

  /// Última cópia salva no aparelho, se houver.
  Future<RadarData?> cached() async {
    try {
      final f = await _cacheFile();
      if (!await f.exists()) return null;
      return await compute(_parse, await f.readAsString());
    } catch (_) {
      return null;
    }
  }

  Future<File> _cacheFile() async => File('${(await getApplicationSupportDirectory()).path}/$_cacheName');

  Future<void> _writeCache(String body) async {
    try {
      await (await _cacheFile()).writeAsString(body, flush: true);
    } catch (_) {/* sem cache: o app continua funcionando online */}
  }

  Future<void> _deleteCache() async {
    try {
      final f = await _cacheFile();
      if (await f.exists()) await f.delete();
    } catch (_) {}
  }
}

RadarData _parse(String body) => RadarData.fromJson(jsonDecode(body) as Map<String, dynamic>);

class RadarException implements Exception {
  final String message;
  RadarException(this.message);
  @override
  String toString() => message;
}
