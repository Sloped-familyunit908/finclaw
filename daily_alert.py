# FinClaw Daily Stock Alert
# Runs every trading day at 8:30 AM (Asia/Shanghai)
# Scans A-shares + HK, picks top 20 opportunities

import asyncio, sys, os
sys.path.insert(0, "Q:\\src\\side-projects\\ai-trading-engine")
import logging, warnings
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")
import yfinance as yf
from datetime import datetime

# Check if today is a trading day (Mon-Fri)
today = datetime.now()
if today.weekday() >= 5:  # Saturday or Sunday
    print("Weekend, no scan needed.")
    exit(0)

SCAN_UNIVERSE = {
    # AI / Chip
    "688498.SS":"RuiChip","688256.SS":"Cambricon","603019.SS":"Zhongke Shuguang",
    "688012.SS":"SMIC","002230.SZ":"iFLYTEK","002371.SZ":"Naura Tech",
    "688008.SS":"Anji Micro","002049.SZ":"Unigroup","603986.SS":"GigaDevice",
    # Optical module
    "002281.SZ":"Guangxun Tech","300308.SZ":"Innolight","002396.SZ":"Star Semicom",
    "300602.SZ":"Flyco Fiber",
    # PCB
    "002938.SZ":"Shennan","002916.SZ":"Suntak","000063.SZ":"ZTE",
    # New energy / battery
    "300750.SZ":"CATL","002594.SZ":"BYD","300274.SZ":"Sungrow Power",
    "002812.SZ":"Yunnan Energy","300014.SZ":"EVE Energy",
    "601012.SS":"LONGi","688599.SS":"Trina Solar",
    # Resources / gold
    "601899.SS":"Zijin Mining","603993.SS":"Luoyang Moly",
    "601600.SS":"Aluminum Corp","600547.SS":"Shandong Gold",
    "600489.SS":"Zhongjin Gold","600362.SS":"Jiangxi Copper",
    "002466.SZ":"Tianqi Lithium",
    # Defense
    "600893.SS":"AVIC Shenyang","000768.SZ":"AVICOPTER",
    # Robotics
    "300124.SZ":"Inovance","002747.SZ":"Estun",
    # Finance
    "601688.SS":"Huatai Sec","600030.SS":"CITIC Sec","601318.SS":"Ping An",
    # Consumer
    "600519.SS":"Moutai","000333.SZ":"Midea","000651.SZ":"Gree",
    # Medical
    "300760.SZ":"Mindray","300122.SZ":"Zhifei Bio",
    # Tech
    "002415.SZ":"Hikvision","300059.SZ":"East Money","300474.SZ":"Kingdee",
    # Power
    "601985.SS":"CRPC Nuclear","600900.SS":"CYPC Hydro",
    # HK
    "1860.HK":"Mobvista","0700.HK":"Tencent","9988.HK":"Alibaba",
    "1810.HK":"Xiaomi","2318.HK":"Ping An HK",
}

def scan():
    results = []
    for ticker, name in SCAN_UNIVERSE.items():
        try:
            df = yf.Ticker(ticker).history(period="3mo")
            if df.empty or len(df) < 20: continue
            prices = [float(row["Close"]) for _, row in df.iterrows()]
            volumes = [float(row["Volume"]) for _, row in df.iterrows()]

            current = prices[-1]
            ma5 = sum(prices[-5:]) / 5
            ma10 = sum(prices[-10:]) / 10
            ma20 = sum(prices[-20:]) / 20

            gains = [max(prices[i]-prices[i-1], 0) for i in range(-14, 0)]
            losses = [max(prices[i-1]-prices[i], 0) for i in range(-14, 0)]
            ag = sum(gains)/14; al = sum(losses)/14
            rsi = 100 - 100/(1+ag/max(al,0.001))

            mom_5d = prices[-1] / prices[-6] - 1 if len(prices) > 5 else 0
            mom_1d = prices[-1] / prices[-2] - 1 if len(prices) > 1 else 0
            mom_20d = prices[-1] / prices[-21] - 1 if len(prices) > 20 else 0

            vol_5 = sum(volumes[-5:]) / 5
            vol_20 = sum(volumes[-20:]) / 20
            vol_ratio = vol_5 / max(vol_20, 1)

            high_20 = max(prices[-20:])
            from_high = current / high_20 - 1

            trend_up = current > ma5 > ma10 > ma20

            # Score
            score = 0
            if 0.02 < mom_5d < 0.15 and rsi < 70: score += 3
            elif mom_5d > 0 and rsi < 65: score += 2
            if trend_up: score += 2
            if current > ma5 and ma5 > ma20: score += 1
            if vol_ratio > 1.3: score += 1
            if trend_up and mom_1d < -0.02 and rsi < 65: score += 3
            if from_high > -0.05 and from_high < 0: score += 2
            if rsi > 75: score -= 2
            if mom_5d > 0.20: score -= 2
            if current < ma20: score -= 1

            if score >= 2:
                signal = "STRONG BUY" if score >= 6 else ("BUY" if score >= 4 else "WATCH")
                results.append((score, ticker, name, current, rsi, mom_5d, mom_1d, mom_20d, vol_ratio, from_high, signal))
        except:
            continue

    results.sort(reverse=True)
    return results[:20]

results = scan()
date_str = today.strftime("%Y-%m-%d %A")

# Format output
lines = []
lines.append("FinClaw Daily Alert - %s" % date_str)
lines.append("")
lines.append("TOP 20 Opportunities:")
lines.append("")

for i, (score, ticker, name, price, rsi, m5, m1, m20, vr, fh, signal) in enumerate(results, 1):
    emoji = "***" if signal == "STRONG BUY" else "** " if signal == "BUY" else "   "
    lines.append("%s%2d. %s %s %.2f RSI=%.0f 5D=%+.1f%% 1D=%+.1f%% Vol=%.1fx [%s]" % (
        emoji, i, ticker, name, price, rsi, m5*100, m1*100, vr, signal))

lines.append("")
lines.append("STRONG BUY = score 6+, RSI safe, trend UP, near breakout")
lines.append("BUY = score 4+, good setup")
lines.append("WATCH = score 2+, wait for confirmation")
lines.append("")
lines.append("Not financial advice.")

output = "\n".join(lines)
print(output)
