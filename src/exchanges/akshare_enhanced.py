"""
Enhanced A-Share Data Adapter using AKShare
Provides real-time quotes, historical data, fundamentals, fund flows.
"""


def get_realtime_quotes(symbols: list = None) -> list:
    """Get real-time A-share quotes for all or specific stocks."""
    try:
        import akshare as ak

        df = ak.stock_zh_a_spot_em()
        # Returns: code, name, price, change%, volume, turnover, PE, etc.
        results = []
        for _, row in df.iterrows():
            code = row.get('代码', '')
            if symbols and code not in symbols:
                continue
            results.append({
                'code': code,
                'name': row.get('名称', ''),
                'price': row.get('最新价'),
                'change_pct': row.get('涨跌幅'),
                'volume': row.get('成交量'),
                'turnover': row.get('成交额'),
                'pe': row.get('市盈率-动态'),
                'market_cap': row.get('总市值'),
                'high': row.get('最高'),
                'low': row.get('最低'),
            })
        return results
    except Exception as e:
        return []


def get_stock_fundamentals(code: str) -> dict:
    """Get fundamental data for a specific A-share stock."""
    try:
        import akshare as ak

        # Financial indicators
        fin = ak.stock_financial_analysis_indicator(symbol=code)
        if fin is not None and not fin.empty:
            latest = fin.iloc[0]
            return {
                'roe': latest.get('净资产收益率(%)'),
                'gross_margin': latest.get('销售毛利率(%)'),
                'net_margin': latest.get('销售净利率(%)'),
                'debt_ratio': latest.get('资产负债率(%)'),
                'revenue_yoy': latest.get('主营业务收入增长率(%)'),
            }
        return {}
    except Exception:
        return {}


def get_fund_flow(code: str) -> dict:
    """Get capital flow data (main force, retail, etc.)."""
    try:
        import akshare as ak

        df = ak.stock_individual_fund_flow(
            stock=code,
            market="sh" if code.startswith('6') else "sz",
        )
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            return {
                'main_net_inflow': latest.get('主力净流入-净额'),
                'retail_net_inflow': latest.get('散户净流入-净额'),
                'date': str(latest.get('日期', '')),
            }
        return {}
    except Exception:
        return {}


def get_north_bound_flow() -> dict:
    """Get northbound capital flow (Hong Kong -> A-shares)."""
    try:
        import akshare as ak

        df = ak.stock_hsgt_north_net_flow_in_em()
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            return {
                'date': str(latest.get('日期', '')),
                'net_inflow': latest.get('当日净买入-北向'),
            }
        return {}
    except Exception:
        return {}
