import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:fast_gbk/fast_gbk.dart';

class GoldDataFetcher {
  // Config
  static const String _sinaUrl =
      "https://hq.sinajs.cn/list=hf_XAU,hf_SI,fx_susdcny,SGE_AUTD,SGE_AGTD";
  final Map<String, String> _headers = {
    "Referer": "https://finance.sina.com.cn/",
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
  };

  // State for seamless deduction
  double _lastPremiumGold = 9.5;
  double _lastPremiumSilver = 0.15;

  // Constants
  static const double _ozToG = 31.1034768;

  GoldDataFetcher();

  Future<Map<String, dynamic>> fetchAll() async {
    final Map<String, dynamic> result = {
      "gold": {"intl": 0.0, "intl_change": 0.0, "dom": 0.0, "dom_change": 0.0},
      "silver": {
        "intl": 0.0,
        "intl_change": 0.0,
        "dom": 0.0,
        "dom_change": 0.0
      },
      "crypto": <String, dynamic>{},
      "exchange_rate": 0.0,
      "market_status": {"gold": "open", "silver": "open"},
      "error": null
    };

    try {
      // 1. Fetch Sina Data
      try {
        final sinaResp = await http
            .get(Uri.parse(_sinaUrl), headers: _headers)
            .timeout(const Duration(seconds: 3));
        if (sinaResp.statusCode == 200) {
          // Decode GBK
          final String body = gbk.decode(sinaResp.bodyBytes);
          _parseSinaData(body, result);
        }
      } catch (e) {
        print("Sina Fetch Error: $e");
      }

      // 2. Fetch Crypto (Parallel)
      final cryptoMap = {
        "BTC": "BTCUSDT",
        "ETH": "ETHUSDT",
        "BNB": "BNBUSDT",
        "SOL": "SOLUSDT",
        "HYPE": "HYPEUSDT"
      };
      final List<Future<void>> cryptoTasks = [];

      cryptoMap.forEach((name, sym) {
        cryptoTasks.add(_fetchSingleCrypto(name, sym).then((res) {
          if (res != null) {
            (result["crypto"] as Map)[name] = res;
          }
        }));
      });

      await Future.wait(cryptoTasks);

      // 3. Logic: Seamless Deduction (Domestic)
      _calculateDomestic(result, "gold", _ozToG, 1.0); // Gold: 1g
      _calculateDomestic(result, "silver", _ozToG,
          1000.0); // Silver: SGE is kr/kg, so div 1000
    } catch (e) {
      result["error"] = e.toString();
    }

    return result;
  }

  void _parseSinaData(String html, Map<String, dynamic> data) {
    List<String>? parse(String key) {
      final RegExp regExp = RegExp('$key="([^"]+)"');
      final match = regExp.firstMatch(html);
      if (match != null) {
        return match.group(1)!.split(',');
      }
      return null;
    }

    // Exchange Rate
    final ex = parse("fx_susdcny");
    if (ex != null && ex.length > 1) {
      data["exchange_rate"] = double.tryParse(ex[1]) ?? 0.0;
    }

    // Intl Gold
    final xau = parse("hf_XAU");
    if (xau != null && xau.length > 1) {
      final current = double.tryParse(xau[0]) ?? 0.0;
      final prev = double.tryParse(xau[1]) ?? 0.0;
      data["gold"]["intl"] = current;
      if (prev > 0) {
        data["gold"]["intl_change"] = ((current - prev) / prev * 100);
      }
    }

    // Intl Silver
    final si = parse("hf_SI");
    if (si != null && si.length > 7) {
      final current = double.tryParse(si[0]) ?? 0.0;
      final prev = double.tryParse(si[1]) ?? (double.tryParse(si[7]) ?? 0.0);
      data["silver"]["intl"] = current;
      if (prev > 0) {
        data["silver"]["intl_change"] = ((current - prev) / prev * 100);
      }
    }

    // Domestic Raw Data (Stored in temp map for calculation)
    final auSpot = parse("SGE_AUTD");
    if (auSpot != null && auSpot.length > 4) {
      data["_au_last"] = double.tryParse(auSpot[3]) ?? 0.0;
      data["_au_prev"] = double.tryParse(auSpot[4]) ?? 0.0;
    }

    final agSpot = parse("SGE_AGTD");
    if (agSpot != null && agSpot.length > 4) {
      data["_ag_last"] = double.tryParse(agSpot[3]) ?? 0.0;
      data["_ag_prev"] = double.tryParse(agSpot[4]) ?? 0.0;
    }
  }

  void _calculateDomestic(Map<String, dynamic> data, String type, double ozToG,
      double scaleDivisor) {
    // scaleDivisor: Gold=1 (CNY/g), Silver=1000 (SGE gives CNY/kg, we want CNY/g)

    final double intlPrice = data[type]["intl"];
    final double exchangeRate = data["exchange_rate"];

    if (intlPrice <= 0 || exchangeRate <= 0) return;

    final double theoreticalDom =
        (intlPrice * exchangeRate) / ozToG; // Gold: /31.103...

    // Get Raw SGE Data
    double actualDom = 0.0;
    double yesterdayClose = 0.0;

    if (type == "gold") {
      actualDom = data["_au_last"] ?? 0.0;
      yesterdayClose = data["_au_prev"] ?? 0.0;
    } else {
      actualDom = (data["_ag_last"] ?? 0.0) / scaleDivisor;
      yesterdayClose = (data["_ag_prev"] ?? 0.0) / scaleDivisor;
    }

    // Determine if closed
    // Simple heuristic: if price is 0 or extremely low, or if we want to be smarter (time based? no, use price)
    // The Python logic used: `is_market_closed = len(spot) < 4 or actual_dom <= 0`
    bool isMarketClosed = actualDom <= 0;

    // Use Python logic: if actualDom > 0, it's open.
    // NOTE: SGE often returns 0 or closed price at night/weekends?
    // Actually standard SGE API returns last close when closed.
    // The Python script implies if `actual_dom > 0` it takes it.
    // But how do we know if it *stopped* updating? Python script only checks `actual_dom <= 0`.
    // Wait, Python also had: `if actual_dom > 0 and not is_market_closed: record premium`.
    // Let's stick to Python logic.

    if (actualDom > 0) {
      // Normal / Open
      // Update Premium
      double currentPremium = actualDom - theoreticalDom;
      if (type == "gold") {
        _lastPremiumGold = currentPremium;
      } else {
        _lastPremiumSilver = currentPremium;
      }

      data[type]["dom"] = actualDom;
      data["market_status"][type] = "open";

      if (yesterdayClose > 0) {
        data[type]["dom_change"] =
            ((actualDom - yesterdayClose) / yesterdayClose * 100);
      }
    } else {
      // Closed / Deduction
      double premium = (type == "gold") ? _lastPremiumGold : _lastPremiumSilver;
      double deducedPrice = theoreticalDom + premium;

      data[type]["dom"] = deducedPrice;
      data["market_status"][type] = "closed"; // "休市"

      // Use Intl change as Dom change
      data[type]["dom_change"] = data[type]["intl_change"];
    }
  }

  Future<Map<String, dynamic>?> _fetchSingleCrypto(
      String name, String sym) async {
    // 1. Try Spot
    var res = await _fetchOkx(sym.replaceAll("USDT", "-USDT"));
    if (res != null) return {"price": res["price"], "change": res["change"]};

    // 2. Try Swap (Contract)
    print("OKX Spot failed for $name, trying Swap...");
    res = await _fetchOkx(sym.replaceAll("USDT", "-USDT-SWAP"));
    if (res != null) return {"price": res["price"], "change": res["change"]};

    return null;
  }

  Future<Map<String, double>?> _fetchOkx(String instId) async {
    try {
      final url = "https://www.okx.com/api/v5/market/ticker?instId=$instId";
      // Increased timeout to 10s for proxy
      final resp = await http
          .get(Uri.parse(url), headers: _headers)
          .timeout(const Duration(seconds: 10));

      if (resp.statusCode != 200) {
        print("OKX Error [$instId]: ${resp.statusCode} - ${resp.body}");
        return null;
      }

      final json = jsonDecode(resp.body);

      if (json["code"] == "0" &&
          json["data"] != null &&
          (json["data"] as List).isNotEmpty) {
        final ticker = json["data"][0];
        final last = double.tryParse(ticker["last"]) ?? 0.0;
        final open24 = double.tryParse(ticker["open24h"]) ?? 0.0;
        double change = 0.0;
        if (open24 > 0) {
          change = (last - open24) / open24 * 100;
        }
        return {"price": last, "change": change};
      } else {
        print("OKX Data Error [$instId]: ${json}");
      }
    } catch (e) {
      print("OKX Exception [$instId]: $e");
    }
    return null;
  }
}
