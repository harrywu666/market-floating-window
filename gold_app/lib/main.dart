import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:intl/intl.dart';
import 'data_fetcher.dart';

import 'dart:io';
import 'package:flutter/foundation.dart';

void main() {
  print("DEBUG: Starting GoldApp with HttpOverrides...");
  HttpOverrides.global = MyHttpOverrides();
  runApp(const GoldApp());
}

class MyHttpOverrides extends HttpOverrides {
  @override
  HttpClient createHttpClient(SecurityContext? context) {
    return super.createHttpClient(context)
      ..findProxy = (uri) {
        if (kReleaseMode) {
          return "DIRECT";
        }
        if (uri.host.contains('okx.com')) {
          return "PROXY 10.0.2.2:7897";
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
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: Color(0xFF0A0B0D),
        systemNavigationBarIconBrightness: Brightness.light,
      ),
    );

    return MaterialApp(
      title: 'Gold Monitor',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0A0B0D),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFFFFD700),
          surface: Color(0xFF1A1D21),
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

class _HomePageState extends State<HomePage> with TickerProviderStateMixin {
  final GoldDataFetcher _fetcher = GoldDataFetcher();
  Timer? _timer;
  Map<String, dynamic> _data = {};
  bool _isLoading = true;
  String _updateTime = "--:--:--";

  late AnimationController _pulseController;

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

  // Modern Color Palette
  static const Color colUp = Color(0xFF00D084);
  static const Color colUpBg = Color(0x1A00D084);
  static const Color colDown = Color(0xFFFF4757);
  static const Color colDownBg = Color(0x1AFF4757);
  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Color(0xFF8B92A8);
  static const Color cardBg = Color(0xFF1A1D21);

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    )..repeat();

    _loadConfig();
    _fetchData();
    _timer = Timer.periodic(const Duration(seconds: 4), (timer) => _fetchData());
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pulseController.dispose();
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
      backgroundColor: const Color(0xFF0A0B0D),
      body: SafeArea(
        child: _isLoading && _data.isEmpty
            ? const Center(
                child: CircularProgressIndicator(
                  color: Color(0xFFFFD700),
                ),
              )
            : RefreshIndicator(
                onRefresh: _fetchData,
                color: const Color(0xFFFFD700),
                backgroundColor: cardBg,
                child: SingleChildScrollView(
                  physics: const BouncingScrollPhysics(),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildHeader(),
                        const SizedBox(height: 16),
                        if (_config['gold'] == true) _buildGoldCard(),
                        if (_config['silver'] == true) _buildSilverCard(),
                        if (_config['crypto'] == true) ...[
                          const SizedBox(height: 12),
                          _buildCryptoSection(),
                        ],
                        const SizedBox(height: 8),
                        _buildFooter(),
                      ],
                    ),
                  ),
                ),
              ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        const Text(
          "市场行情",
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w800,
            color: textPrimary,
            letterSpacing: -0.5,
          ),
        ),
        AnimatedBuilder(
          animation: _pulseController,
          builder: (context, child) {
            return Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: colUp,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: colUp.withOpacity(0.4 + 0.3 * _pulseController.value),
                    blurRadius: 6 + 3 * _pulseController.value,
                    spreadRadius: 1.5 * _pulseController.value,
                  ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }

  Widget _buildGoldCard() {
    final gold = _data['gold'] ?? {};
    final status = _data['market_status']?['gold'] ?? 'open';
    return _buildMetalCard(
      label: "黄金",
      symbol: "XAU",
      status: status,
      intlPrice: gold['intl'],
      intlChange: gold['intl_change'],
      domPrice: gold['dom'],
      domChange: gold['dom_change'],
      intlUnit: "USD/oz",
      domUnit: "CNY/g",
    );
  }

  Widget _buildSilverCard() {
    final silver = _data['silver'] ?? {};
    final status = _data['market_status']?['silver'] ?? 'open';
    return _buildMetalCard(
      label: "白银",
      symbol: "XAG",
      status: status,
      intlPrice: silver['intl'],
      intlChange: silver['intl_change'],
      domPrice: silver['dom'],
      domChange: silver['dom_change'],
      intlUnit: "USD/oz",
      domUnit: "CNY/g",
    );
  }

  Widget _buildMetalCard({
    required String label,
    required String symbol,
    required String status,
    dynamic intlPrice,
    dynamic intlChange,
    dynamic domPrice,
    dynamic domChange,
    required String intlUnit,
    required String domUnit,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.white.withOpacity(0.06),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Text(
                label,
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: textPrimary,
                ),
              ),
              const SizedBox(width: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  symbol,
                  style: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: textSecondary,
                  ),
                ),
              ),
              const Spacer(),
              if (status == 'closed')
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0x26FFAA00),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: const Color(0x40FFAA00),
                      width: 1,
                    ),
                  ),
                  child: const Text(
                    "休市",
                    style: TextStyle(
                      fontSize: 9,
                      color: Color(0xFFFFAA00),
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          // International Price
          _buildPriceRow(
            unit: intlUnit,
            price: intlPrice,
            change: intlChange,
            isLarge: true,
          ),
          const SizedBox(height: 10),
          // Domestic Price
          _buildPriceRow(
            unit: domUnit,
            price: domPrice,
            change: domChange,
            isLarge: false,
          ),
        ],
      ),
    );
  }

  Widget _buildPriceRow({
    required String unit,
    dynamic price,
    dynamic change,
    required bool isLarge,
  }) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Text(
          unit,
          style: const TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w500,
            color: textSecondary,
          ),
        ),
        Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Text(
              formatPrice(price, isLarge ? 2 : 3),
              style: TextStyle(
                fontFamily: 'monospace',
                fontSize: isLarge ? 26 : 20,
                fontWeight: FontWeight.w700,
                color: textPrimary,
                letterSpacing: -0.5,
                height: 1,
              ),
            ),
            const SizedBox(width: 8),
            _buildChangeBadge(change, isSmall: !isLarge),
          ],
        ),
      ],
    );
  }

  Widget _buildChangeBadge(dynamic change, {bool isSmall = false}) {
    if (change == null) {
      return Container(
        padding: EdgeInsets.symmetric(horizontal: isSmall ? 6 : 8, vertical: isSmall ? 2 : 3),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(
          "--",
          style: TextStyle(
            fontSize: isSmall ? 10 : 11,
            fontWeight: FontWeight.w600,
            color: textSecondary,
          ),
        ),
      );
    }

    final val = (change as num).toDouble();
    final text = (val >= 0 ? "+" : "") + val.toStringAsFixed(2) + "%";
    final isUp = val >= 0;

    return Container(
      padding: EdgeInsets.symmetric(horizontal: isSmall ? 6 : 8, vertical: isSmall ? 2 : 3),
      decoration: BoxDecoration(
        color: isUp ? colUpBg : colDownBg,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontFamily: 'monospace',
          color: isUp ? colUp : colDown,
          fontSize: isSmall ? 10 : 11,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  Widget _buildCryptoSection() {
    final crypto = _data['crypto'] ?? {};
    
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.white.withOpacity(0.06),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            "加密货币",
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w700,
              color: textPrimary,
            ),
          ),
          const SizedBox(height: 10),
          ..._cryptoOrder.where((s) => _config[s] == true).map((sym) {
            final info = crypto[sym];
            return _buildCryptoItem(sym, info);
          }).toList(),
        ],
      ),
    );
  }

  Widget _buildCryptoItem(String symbol, dynamic info) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            symbol,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: textPrimary,
            ),
          ),
          Row(
            children: [
              Text(
                info == null ? "--" : formatPrice(info['price']),
                style: const TextStyle(
                  fontFamily: 'monospace',
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: textPrimary,
                ),
              ),
              const SizedBox(width: 8),
              _buildChangeBadge(info?['change'], isSmall: true),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildFooter() {
    final rate = _data['exchange_rate'] ?? 0.0;
    
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          "USD/CNY ${rate.toStringAsFixed(4)}",
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w500,
            color: textSecondary.withOpacity(0.8),
          ),
        ),
        Text(
          _updateTime,
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w500,
            color: textSecondary.withOpacity(0.8),
          ),
        ),
      ],
    );
  }

  String formatPrice(dynamic price, [int precision = 2]) {
    if (price == null) return "--";
    return (price as num).toStringAsFixed(precision);
  }
}
