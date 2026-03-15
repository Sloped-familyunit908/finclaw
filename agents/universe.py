"""
FinClaw — Extended Stock Universe + Cross-Market Sector Linkage
================================================================
1. Expanded universe: US 50+, A-shares 60+, HK 25+
2. Sector linkage: when NVDA moves, which A-shares follow?
3. Cross-market correlation: US tech → A-share tech → HK tech
"""

# ═══ EXPANDED US UNIVERSE (50+ stocks) ═══
US_EXTENDED = {
    # AI / Semis (core)
    "NVDA": "NVIDIA", "AVGO": "Broadcom", "AMD": "AMD", "ANET": "Arista",
    "MRVL": "Marvell", "QCOM": "Qualcomm", "MU": "Micron",
    "LRCX": "Lam Research", "KLAC": "KLA Corp", "ASML": "ASML",
    "TSM": "TSMC",
    # Big Tech
    "AAPL": "Apple", "MSFT": "Microsoft", "GOOG": "Alphabet",
    "AMZN": "Amazon", "META": "Meta", "TSLA": "Tesla",
    "NFLX": "Netflix", "CRM": "Salesforce", "ORCL": "Oracle",
    # Growth / Innovation
    "PLTR": "Palantir", "COIN": "Coinbase", "SHOP": "Shopify",
    "DKNG": "DraftKings", "RBLX": "Roblox", "UBER": "Uber",
    "DASH": "DoorDash", "ABNB": "Airbnb", "SQ": "Block",
    # Healthcare
    "LLY": "Eli Lilly", "UNH": "UnitedHealth", "ABBV": "AbbVie",
    "MRK": "Merck", "ISRG": "Intuitive Surgical", "DXCM": "DexCom",
    "MRNA": "Moderna",
    # Consumer
    "COST": "Costco", "WMT": "Walmart", "KO": "Coca-Cola",
    "PG": "P&G", "PEP": "PepsiCo", "MCD": "McDonald's", "SBUX": "Starbucks",
    # Energy
    "XOM": "ExxonMobil", "CVX": "Chevron", "OXY": "Occidental",
    # Finance
    "JPM": "JPMorgan", "GS": "Goldman", "V": "Visa",
    "MA": "Mastercard", "BAC": "Bank of America",
    # Industrial
    "CAT": "Caterpillar", "DE": "John Deere", "GE": "GE Aerospace",
    "LMT": "Lockheed", "RTX": "RTX (Raytheon)", "BA": "Boeing",
    # Cybersecurity
    "CRWD": "CrowdStrike", "PANW": "Palo Alto", "FTNT": "Fortinet", "ZS": "Zscaler",
}

# ═══ EXPANDED A-SHARES (60+ stocks) ═══
A_SHARES_EXTENDED = {
    # AI / 算力 / 芯片
    "688256.SS": "Cambricon", "603019.SS": "Zhongke Shuguang",
    "688012.SS": "SMIC", "002230.SZ": "iFLYTEK",
    "002371.SZ": "Naura Tech", "688008.SS": "Anji Micro",
    "300474.SZ": "Kingdee", "688111.SS": "Montage Tech",
    "002049.SZ": "Unigroup Guoxin", "688036.SS": "Transmit Tech",
    "300496.SZ": "AMEC (Etch)", "688981.SS": "CXMT Memory",
    # 新能源 / 电池 / 光伏
    "300750.SZ": "CATL", "002594.SZ": "BYD",
    "300274.SZ": "Sungrow Power", "002812.SZ": "Yunnan Energy",
    "601012.SS": "LONGi Green", "300014.SZ": "EVE Energy",
    "688599.SS": "Trina Solar", "601615.SS": "Ming Yang Wind",
    # 有色 / 资源 / 黄金
    "601899.SS": "Zijin Mining", "603993.SS": "Luoyang Moly",
    "600362.SS": "Jiangxi Copper", "002466.SZ": "Tianqi Lithium",
    "600547.SS": "Shandong Gold", "600489.SS": "Zhongjin Gold",
    "601600.SS": "Aluminum Corp", "600219.SS": "Nanjing Steel",
    # 军工 / 航天
    "600893.SS": "AVIC Shenyang", "000768.SZ": "AVICOPTER",
    "600760.SS": "AVIC Optronics", "600879.SS": "Hanwei Electronics",
    # 白酒 / 消费
    "600519.SS": "Moutai", "000858.SZ": "Wuliangye",
    "000568.SZ": "Luzhou Laojiao", "600809.SS": "Shanxi Fenjiu",
    "002304.SZ": "Yanghe", "000596.SZ": "Gujing Gong",
    # 金融 / 券商
    "601318.SS": "Ping An", "600036.SS": "CMB",
    "601688.SS": "Huatai Sec", "600030.SS": "CITIC Sec",
    "601066.SS": "CNOOC", "601166.SS": "Industrial Bank",
    # 医药 / 创新药
    "300760.SZ": "Mindray", "300347.SZ": "Tigermed",
    "603259.SS": "WuXi AppTec", "688180.SS": "Junshi Bio",
    "300122.SZ": "Zhifei Bio",
    # 科技 / 消费电子
    "002415.SZ": "Hikvision", "300059.SZ": "East Money",
    "000333.SZ": "Midea Group", "300124.SZ": "Inovance Tech",
    "601633.SS": "Great Wall Motor", "000651.SZ": "Gree Electric",
    "002714.SZ": "Muyuan Foods", "603986.SS": "GigaDevice",
    # 电力 / 基建
    "600900.SS": "CYPC Hydro", "601985.SS": "CRPC Nuclear",
    "600025.SS": "Huaneng Hydro", "601669.SS": "CSCEC",
    # 机器人 / 新兴
    "300124.SZ": "Inovance", "688169.SS": "Roborock",
    "002747.SZ": "Estun Robotics", "688396.SS": "Huada Gene",
}

# ═══ EXPANDED HK (25+ stocks) ═══
HK_EXTENDED = {
    "0700.HK": "Tencent", "9988.HK": "Alibaba",
    "3690.HK": "Meituan", "1211.HK": "BYD HK",
    "9618.HK": "JD.com", "1810.HK": "Xiaomi",
    "2318.HK": "Ping An HK", "0941.HK": "China Mobile",
    "0388.HK": "HKEX", "0005.HK": "HSBC",
    "1024.HK": "Kuaishou", "9888.HK": "Baidu",
    "2020.HK": "ANTA Sports", "0241.HK": "Alibaba Health",
    "1347.HK": "Hua Hong Semi", "6060.HK": "ZhongAn Online",
    "0981.HK": "SMIC HK", "2015.HK": "Li Auto",
    "9866.HK": "NIO", "1797.HK": "East Buy",
    "6618.HK": "JD Health", "0669.HK": "Techtronic",
    "1177.HK": "Sino Biopharm", "2382.HK": "Sunny Optical",
    "0175.HK": "Geely Auto",
}


# ═══ SECTOR LINKAGE MAP ═══
# When one sector moves in one market, which sectors in other markets follow?
SECTOR_LINKAGE = {
    # US AI chips → A-share AI chips → HK semis
    "us_ai_chips": {
        "us": ["NVDA", "AVGO", "AMD", "ANET", "MRVL", "TSM", "ASML"],
        "china": ["688256.SS", "603019.SS", "688012.SS", "002371.SZ", "688008.SS", "300496.SZ"],
        "hk": ["1347.HK", "0981.HK"],
        "correlation": 0.75,
        "lag_days": 1,
        "description": "US AI chip rally → A-share chip substitution plays follow next day",
    },
    # US tech giants → HK tech
    "us_tech_to_hk": {
        "us": ["AAPL", "MSFT", "GOOG", "AMZN", "META"],
        "hk": ["0700.HK", "9988.HK", "3690.HK", "9618.HK", "1810.HK", "9888.HK"],
        "correlation": 0.65,
        "lag_days": 0,
        "description": "US tech sentiment directly impacts HK tech (same trading day overlap)",
    },
    # Gold price → A-share/HK gold miners
    "gold_mining": {
        "us": ["GLD", "NEM", "GOLD"],
        "china": ["600547.SS", "600489.SS"],
        "hk": [],
        "correlation": 0.85,
        "lag_days": 0,
        "description": "Gold price moves → mining stocks follow immediately",
    },
    # EV supply chain (cross-market)
    "ev_chain": {
        "us": ["TSLA"],
        "china": ["002594.SZ", "300750.SZ", "002812.SZ", "300014.SZ"],
        "hk": ["1211.HK", "2015.HK", "9866.HK", "0175.HK"],
        "correlation": 0.55,
        "lag_days": 1,
        "description": "Tesla sentiment → BYD/CATL/NIO/Li Auto follow",
    },
    # US energy → A-share energy
    "energy": {
        "us": ["XOM", "CVX", "OXY"],
        "china": ["601066.SS", "601857.SS"],
        "hk": [],
        "correlation": 0.70,
        "lag_days": 0,
        "description": "Oil price / US energy → CNOOC follows",
    },
    # Consumer / luxury → A-share baijiu
    "consumer_luxury": {
        "us": ["LVMH", "KO", "SBUX", "MCD"],
        "china": ["600519.SS", "000858.SZ", "000568.SZ", "600809.SS"],
        "hk": ["2020.HK"],
        "correlation": 0.30,
        "lag_days": 2,
        "description": "Global luxury/consumer sentiment → baijiu sector (weak correlation)",
    },
    # Cybersecurity (US-only but A-share catching up)
    "cybersecurity": {
        "us": ["CRWD", "PANW", "FTNT", "ZS"],
        "china": ["002415.SZ", "688561.SS"],
        "correlation": 0.40,
        "lag_days": 1,
        "description": "US cyber events → A-share security stocks react",
    },
    # Pharma / biotech
    "pharma": {
        "us": ["LLY", "ABBV", "MRK", "MRNA"],
        "china": ["300760.SZ", "300347.SZ", "603259.SS", "688180.SS", "300122.SZ"],
        "hk": ["1177.HK", "6618.HK"],
        "correlation": 0.35,
        "lag_days": 1,
        "description": "US pharma innovation → CXO/biotech A-shares follow",
    },
    # Robotics / automation
    "robotics": {
        "us": ["ISRG", "TSLA"],
        "china": ["300124.SZ", "002747.SZ", "688169.SS"],
        "hk": ["2382.HK"],
        "correlation": 0.45,
        "lag_days": 1,
        "description": "Tesla robot/ISRG → A-share robotics concept stocks",
    },
}


def get_linked_stocks(ticker: str) -> list[dict]:
    """Given a ticker, find cross-market linked stocks."""
    results = []
    for sector_name, linkage in SECTOR_LINKAGE.items():
        all_tickers = []
        for market_tickers in [linkage.get("us", []), linkage.get("china", []), linkage.get("hk", [])]:
            all_tickers.extend(market_tickers)

        if ticker in all_tickers:
            # Found! Return all linked stocks except the input
            linked = [t for t in all_tickers if t != ticker]
            results.append({
                "sector": sector_name,
                "description": linkage["description"],
                "correlation": linkage["correlation"],
                "lag_days": linkage["lag_days"],
                "linked_tickers": linked,
            })

    return results


def get_sector_analysis(sector_name: str) -> dict:
    """Get detailed analysis for a sector linkage."""
    if sector_name not in SECTOR_LINKAGE:
        return {"error": f"Unknown sector: {sector_name}"}

    linkage = SECTOR_LINKAGE[sector_name]
    return {
        "sector": sector_name,
        "description": linkage["description"],
        "correlation": linkage["correlation"],
        "lag_days": linkage["lag_days"],
        "us_stocks": linkage.get("us", []),
        "china_stocks": linkage.get("china", []),
        "hk_stocks": linkage.get("hk", []),
    }
