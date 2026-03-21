/* ════════════════════════════════════════════════════════════════
   TECHNICAL INDICATORS — FinClaw 🦀📈
   Pure TypeScript, zero dependencies
   ════════════════════════════════════════════════════════════════ */

/**
 * Simple Moving Average
 */
export function calcSMA(data: number[], period: number): number[] {
  const result: number[] = [];
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(NaN);
    } else {
      let sum = 0;
      for (let j = i - period + 1; j <= i; j++) sum += data[j];
      result.push(sum / period);
    }
  }
  return result;
}

/**
 * Exponential Moving Average
 */
export function calcEMA(data: number[], period: number): number[] {
  const k = 2 / (period + 1);
  const result: number[] = [];
  // seed with SMA of first `period` values
  let sum = 0;
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      sum += data[i];
      result.push(NaN);
    } else if (i === period - 1) {
      sum += data[i];
      result.push(sum / period);
    } else {
      result.push(data[i] * k + result[i - 1] * (1 - k));
    }
  }
  return result;
}

/**
 * RSI — Relative Strength Index (Wilder smoothing)
 */
export function calcRSI(closes: number[], period = 14): number[] {
  const result: number[] = new Array(closes.length).fill(NaN);
  if (closes.length < period + 1) return result;

  let gainSum = 0;
  let lossSum = 0;

  for (let i = 1; i <= period; i++) {
    const diff = closes[i] - closes[i - 1];
    if (diff >= 0) gainSum += diff;
    else lossSum -= diff;
  }

  let avgGain = gainSum / period;
  let avgLoss = lossSum / period;
  result[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);

  for (let i = period + 1; i < closes.length; i++) {
    const diff = closes[i] - closes[i - 1];
    const gain = diff >= 0 ? diff : 0;
    const loss = diff < 0 ? -diff : 0;

    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;

    result[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }

  return result;
}

/**
 * MACD — Moving Average Convergence Divergence
 * Default periods: fast=12, slow=26, signal=9
 */
export function calcMACD(
  closes: number[],
  fastPeriod = 12,
  slowPeriod = 26,
  signalPeriod = 9,
): { macd: number[]; signal: number[]; histogram: number[] } {
  const emaFast = calcEMA(closes, fastPeriod);
  const emaSlow = calcEMA(closes, slowPeriod);

  const macdLine: number[] = [];
  for (let i = 0; i < closes.length; i++) {
    if (isNaN(emaFast[i]) || isNaN(emaSlow[i])) {
      macdLine.push(NaN);
    } else {
      macdLine.push(emaFast[i] - emaSlow[i]);
    }
  }

  // signal line = EMA of macd line (skip NaN prefix)
  const validMacd = macdLine.filter((v) => !isNaN(v));
  const signalOfValid = calcEMA(validMacd, signalPeriod);

  const signalLine: number[] = new Array(closes.length).fill(NaN);
  let vi = 0;
  for (let i = 0; i < closes.length; i++) {
    if (!isNaN(macdLine[i])) {
      signalLine[i] = signalOfValid[vi++];
    }
  }

  const histogram: number[] = [];
  for (let i = 0; i < closes.length; i++) {
    if (isNaN(macdLine[i]) || isNaN(signalLine[i])) {
      histogram.push(NaN);
    } else {
      histogram.push(macdLine[i] - signalLine[i]);
    }
  }

  return { macd: macdLine, signal: signalLine, histogram };
}

/**
 * Bollinger Bands (default: 20-period, 2 std deviations)
 */
export function calcBollingerBands(
  closes: number[],
  period = 20,
  stdDevMultiplier = 2,
): { upper: number[]; middle: number[]; lower: number[] } {
  const middle = calcSMA(closes, period);
  const upper: number[] = [];
  const lower: number[] = [];

  for (let i = 0; i < closes.length; i++) {
    if (isNaN(middle[i])) {
      upper.push(NaN);
      lower.push(NaN);
    } else {
      let sumSq = 0;
      for (let j = i - period + 1; j <= i; j++) {
        sumSq += (closes[j] - middle[i]) ** 2;
      }
      const std = Math.sqrt(sumSq / period);
      upper.push(middle[i] + stdDevMultiplier * std);
      lower.push(middle[i] - stdDevMultiplier * std);
    }
  }

  return { upper, middle, lower };
}

/**
 * KDJ indicator (default: 9,3,3)
 */
export function calcKDJ(
  highs: number[],
  lows: number[],
  closes: number[],
  nPeriod = 9,
  kSmooth = 3,
  dSmooth = 3,
): { k: number[]; d: number[]; j: number[] } {
  const len = closes.length;
  const rsv: number[] = new Array(len).fill(NaN);
  const k: number[] = new Array(len).fill(NaN);
  const d: number[] = new Array(len).fill(NaN);
  const j: number[] = new Array(len).fill(NaN);

  for (let i = nPeriod - 1; i < len; i++) {
    let high = -Infinity;
    let low = Infinity;
    for (let p = i - nPeriod + 1; p <= i; p++) {
      if (highs[p] > high) high = highs[p];
      if (lows[p] < low) low = lows[p];
    }
    rsv[i] = high === low ? 50 : ((closes[i] - low) / (high - low)) * 100;
  }

  // init K,D at first valid RSV to 50
  const startIdx = nPeriod - 1;
  k[startIdx] = (2 / kSmooth) * rsv[startIdx] + (1 - 2 / kSmooth) * 50;
  d[startIdx] = (2 / dSmooth) * k[startIdx] + (1 - 2 / dSmooth) * 50;
  j[startIdx] = 3 * k[startIdx] - 2 * d[startIdx];

  for (let i = startIdx + 1; i < len; i++) {
    if (isNaN(rsv[i])) continue;
    k[i] = (2 / kSmooth) * rsv[i] + (1 - 2 / kSmooth) * k[i - 1];
    d[i] = (2 / dSmooth) * k[i] + (1 - 2 / dSmooth) * d[i - 1];
    j[i] = 3 * k[i] - 2 * d[i];
  }

  return { k, d, j };
}
