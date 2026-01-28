import 'dart:async';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:intl/intl.dart';
import 'data_fetcher.dart';

import 'dart:io';
import 'package:flutter/foundation.dart';

void main() {
  print("DEBUG: Starting GoldApp with HttpOverrides...");
  HttpOverrides.global = MyHttpOverrides(); // Bypass SSL for proxy
  runApp(const GoldApp());
}

// Dev only: Accept any certificate and use explicit proxy
class MyHttpOverrides extends HttpOverrides {
  @override
  HttpClient createHttpClient(SecurityContext? context) {
    return super.createHttpClient(context)
      ..findProxy = (uri) {
        // Release 模式（真机正式版）：完全依赖系统代理（Clash 等分应用代理）
        if (kReleaseMode) {
          return "DIRECT";
        }

        // Debug 模式：仅对 OKX 使用模拟器代理 (10.0.2.2 是模拟器访问宿主机的特殊 IP)
        // 真机调试时，如需使用系统代理，请改为返回 "DIRECT"
        if (uri.host.contains('okx.com')) {
          return "PROXY 10.0.2.2:7897"; // 模拟器专用
        }

        return "DIRECT";
      }
      ..badCertificateCallback = (X509Certificate cert, String host, int port) {
        print("DEBUG: Allowing Bad Cert for $host");
        return true;
      };
  }
}

class GoldApp extends StatelessWidget {
  const GoldApp({super.key});

  @override
  Widget build(BuildContext context) {
    // CSS Ref: --bg-app: rgba(14, 16, 18, 0.95);
    const Color bgApp = Color(0xFF0E1012);

    return MaterialApp(
      title: 'Gold Monitor',
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: bgApp,
        // CSS Ref: --card-bg: rgba(255, 255, 255, 0.05);
        cardColor: const Color(0x0DFFFFFF),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFFFFD700),
          surface: Color(0x0DFFFFFF),
        ),
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final GoldDataFetcher _fetcher = GoldDataFetcher();
  Timer? _timer;
  Map<String, dynamic> _data = {};
  bool _isLoading = true;
  String _updateTime = "--:--:--";

  // Visibility Config
  Map<String, bool> _config = {
    "gold": true,
    "silver": true,
    "crypto": true,
    "BTC": true,
    "ETH": true,
    "BNB": true,
    "SOL": true,
    "HYPE": true
  };
  final List<String> _cryptoOrder = ['BTC', 'ETH', 'BNB', 'SOL', 'HYPE'];

  // CSS Colors
  static const Color colUp = Color(0xFF00EBA0);
  static const Color colUpBg = Color(0x2600EBA0); // alpha 0.15
  static const Color colDown = Color(0xFFFF4555);
  static const Color colDownBg = Color(0x26FF4555); // alpha 0.15
  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Color(0xFF8E9199);

  // Fonts
  // Note: 'SF Mono' is not default on Android, using monospace or Robot
  static const TextStyle fontNum =
      TextStyle(fontFamily: 'monospace', package: null);
  static const TextStyle fontUi = TextStyle(fontFamily: 'Roboto');

  @override
  void initState() {
    super.initState();
    _loadConfig();
    _fetchData();
    _timer =
        Timer.periodic(const Duration(seconds: 4), (timer) => _fetchData());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _loadConfig() async {
    final prefs = await SharedPreferences.getInstance();
    if (mounted) {
      setState(() {
        _config.forEach((key, val) {
          if (prefs.containsKey("show_$key")) {
            _config[key] = prefs.getBool("show_$key")!;
          }
        });
      });
    }
  }

  Future<void> _toggleConfig(String key) async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _config[key] = !(_config[key] ?? true);
    });
    prefs.setBool("show_$key", _config[key]!);
  }

  Future<void> _fetchData() async {
    final data = await _fetcher.fetchAll();
    if (mounted) {
      setState(() {
        _data = data;
        _isLoading = false;
        _updateTime = DateFormat('HH:mm:ss').format(DateTime.now());
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // App Container style from CSS
      // padding: 20px -> EdgeInsets.all(20)
      body: SafeArea(
        child: _isLoading && _data.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: _fetchData,
                child: ListView(
                  padding: const EdgeInsets.all(20),
                  children: [
                    _buildHeader(),
                    const SizedBox(height: 16),
                    if (_config['gold'] == true) _buildGoldCard(),
                    if (_config['silver'] == true) _buildSilverCard(),
                    if (_config['crypto'] == true) _buildCryptoCard(),
                    const SizedBox(height: 6), // Spacer for footer
                    _buildFooter(),
                  ],
                ),
              ),
      ),
    );
  }

  Widget _buildHeader() {
    final statusColor = colUp;
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        const Text("市场行情",
            style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w800,
                color: textPrimary,
                letterSpacing: 0.5)),
        // Status Dot
        Container(
          width: 6,
          height: 6,
          decoration: BoxDecoration(
              color: statusColor,
              shape: BoxShape.circle,
              boxShadow: [BoxShadow(color: statusColor, blurRadius: 6)]),
        )
      ],
    );
  }

  // Card Common Style
  Widget _buildCardBase({required Widget child}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: const Color(0x0DFFFFFF), // --card-bg
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
            color: const Color(0x14FFFFFF), width: 1), // --card-border
      ),
      child: child,
    );
  }

  Widget _buildGoldCard() {
    final gold = _data['gold'] ?? {};
    final status = _data['market_status']?['gold'] ?? 'open';
    return _buildCardBase(
        child: Column(
      children: [
        _buildCardHeader("黄金", "XAU", status),
        const SizedBox(height: 12),
        _buildRow("国际 (USD/oz)", gold['intl'], gold['intl_change']),
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 8),
          child: Divider(height: 1, color: Color(0x0DFFFFFF)), // --row-divider
        ),
        _buildRow("国内 (CNY/g)", gold['dom'], gold['dom_change']),
      ],
    ));
  }

  Widget _buildSilverCard() {
    final silver = _data['silver'] ?? {};
    final status = _data['market_status']?['silver'] ?? 'open';
    return _buildCardBase(
        child: Column(
      children: [
        _buildCardHeader("白银", "XAG", status),
        const SizedBox(height: 12),
        _buildRow("国际 (USD/oz)", silver['intl'], silver['intl_change'],
            isSilver: true),
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 8),
          child: Divider(height: 1, color: Color(0x0DFFFFFF)), // --row-divider
        ),
        _buildRow("国内 (CNY/g)", silver['dom'], silver['dom_change'],
            isSilver: true),
      ],
    ));
  }

  Widget _buildCardHeader(String label, String symbol, String status) {
    return Row(
      children: [
        Text(label,
            style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: Color(0xE6FFFFFF) // rgba 0.9
                )),
        const SizedBox(width: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
          decoration: BoxDecoration(
              color: const Color(0x1AFFFFFF), // rgba 0.1
              borderRadius: BorderRadius.circular(4)),
          child: Text(symbol,
              style: const TextStyle(
                  fontSize: 10, color: textSecondary, fontFamily: 'Roboto')),
        ),
        const Spacer(),
        if (status == 'closed')
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
                color: const Color(0x40FFAA00), // rgba 0.25 (approx)
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: const Color(0x66FFAA00))),
            child: const Text("休市",
                style: TextStyle(
                    fontSize: 9,
                    color: Color(0xFFFFAA00),
                    fontWeight: FontWeight.w600)),
          )
      ],
    );
  }

  Widget _buildCryptoCard() {
    final crypto = _data['crypto'] ?? {};
    return _buildCardBase(
        child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text("加密货币",
            style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: Color(0xE6FFFFFF))),
        const SizedBox(height: 12),
        Column(
          children: _cryptoOrder.where((s) => _config[s] == true).map((sym) {
            final info = crypto[sym];
            return Container(
              margin: const EdgeInsets.only(bottom: 6),
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
              decoration: BoxDecoration(
                  color: const Color(0x08FFFFFF), // rgba 0.03 approx
                  borderRadius: BorderRadius.circular(8)),
              child: Row(
                children: [
                  SizedBox(
                      width: 40,
                      child: Text(sym,
                          style: const TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: Color(0xB3FFFFFF) // 0.7
                              ))),
                  Expanded(
                      child: Text(
                          info == null ? "--" : formatPrice(info['price']),
                          textAlign: TextAlign.right,
                          style: fontNum.copyWith(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: textPrimary))),
                  const SizedBox(width: 10),
                  SizedBox(
                      width: 50,
                      child: _buildChangeTag(info?['change'], fontSize: 11))
                ],
              ),
            );
          }).toList(),
        ),
      ],
    ));
  }

  Widget _buildRow(String label, dynamic price, dynamic change,
      {bool isSilver = false}) {
    // CSS .big-price: 22px / .small-mod: 20px
    final double priceSize = isSilver ? 20 : 22;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label,
            style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: Color(0xB3FFFFFF) // 0.7
                )),
        Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Text(
              formatPrice(price, isSilver ? 3 : 2),
              style: fontNum.copyWith(
                  fontSize: priceSize,
                  fontWeight: FontWeight.w700,
                  color: textPrimary,
                  height: 1.0),
            ),
            const SizedBox(width: 8),
            _buildChangeTag(change),
          ],
        )
      ],
    );
  }

  Widget _buildChangeTag(dynamic change, {double fontSize = 12}) {
    if (change == null)
      return Container(
          width: 50,
          alignment: Alignment.center,
          child: const Text("--", style: TextStyle(color: textSecondary)));

    final val = (change as num).toDouble();
    final text = (val >= 0 ? "+" : "") + val.toStringAsFixed(2) + "%";
    final isUp = val >= 0;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
          color: isUp ? colUpBg : colDownBg,
          borderRadius: BorderRadius.circular(6)),
      constraints: const BoxConstraints(minWidth: 50),
      alignment: Alignment.center,
      child: Text(text,
          style: fontNum.copyWith(
              color: isUp ? colUp : colDown,
              fontSize: fontSize,
              fontWeight: FontWeight.w600)),
    );
  }

  Widget _buildFooter() {
    final rate = _data['exchange_rate'] ?? 0.0;
    // CSS .footer-info
    const footerStyle = TextStyle(
        fontSize: 10,
        color: Color(0xCCFFFFFF), // 0.8
        fontWeight: FontWeight.w500,
        letterSpacing: 0.5);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text("汇率 ${rate.toStringAsFixed(4)}", style: footerStyle),
          Text(_updateTime, style: footerStyle),
        ],
      ),
    );
  }

  String formatPrice(dynamic price, [int precision = 2]) {
    if (price == null) return "--";
    return (price as num).toStringAsFixed(precision);
  }
}
