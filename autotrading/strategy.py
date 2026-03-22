"""
Trading Strategy — Modified by AI Agent
This is the file the AutoTrading agent experiments with.

The agent can change anything here: signals, indicators, parameters,
entry/exit logic, risk management. Everything is fair game.

Must implement: generate_signals(code, closes, volumes, highs, lows, opens, dates)
Returns: list of {'action': 'buy'|'sell', 'index': int, 'price': float}
"""


def compute_rsi(closes: list, period: int = 14) -> list:
    """Compute RSI indicator."""
    if len(closes) < period + 1:
        return [50.0] * len(closes)
    
    rsi = [50.0] * period
    gains, losses = 0.0, 0.0
    
    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains += change
        else:
            losses -= change
    
    avg_gain = gains / period
    avg_loss = losses / period if losses > 0 else 0.001
    
    rs = avg_gain / avg_loss
    rsi.append(100 - (100 / (1 + rs)))
    
    for i in range(period + 1, len(closes)):
        change = closes[i] - closes[i - 1]
        gain = max(change, 0)
        loss = max(-change, 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        rs = avg_gain / (avg_loss if avg_loss > 0 else 0.001)
        rsi.append(100 - (100 / (1 + rs)))
    
    return rsi


def compute_sma(data: list, period: int) -> list:
    """Compute Simple Moving Average."""
    sma = [0.0] * len(data)
    for i in range(period - 1, len(data)):
        sma[i] = sum(data[i - period + 1:i + 1]) / period
    return sma


def generate_signals(code, closes, volumes, highs, lows, opens, dates):
    """
    Generate buy/sell signals for a stock.
    
    This is the baseline RSI mean-reversion strategy.
    The AI agent will modify this to find better strategies.
    
    Returns: list of {'action': 'buy'|'sell', 'index': int, 'price': float}
    """
    signals = []
    
    # Parameters (agent can tune these)
    rsi_buy = 30
    rsi_sell = 70
    hold_days = 5
    stop_loss = 0.08
    take_profit = 0.20
    
    # Compute indicators
    rsi = compute_rsi(closes)
    sma20 = compute_sma(closes, 20)
    
    position = None
    
    for i in range(20, len(closes)):
        if position is None:
            # Buy signal: RSI oversold + price near SMA
            if rsi[i] < rsi_buy and closes[i] > sma20[i] * 0.95:
                position = {'buy_price': closes[i], 'buy_idx': i}
                signals.append({'action': 'buy', 'index': i, 'price': closes[i]})
        else:
            # Sell conditions
            pnl = (closes[i] - position['buy_price']) / position['buy_price']
            days_held = i - position['buy_idx']
            
            sell = False
            if pnl <= -stop_loss:  # Stop loss
                sell = True
            elif pnl >= take_profit:  # Take profit
                sell = True
            elif days_held >= hold_days and rsi[i] > rsi_sell:  # RSI overbought
                sell = True
            elif days_held >= hold_days * 3:  # Max hold time
                sell = True
            
            if sell:
                signals.append({'action': 'sell', 'index': i, 'price': closes[i]})
                position = None
    
    return signals
