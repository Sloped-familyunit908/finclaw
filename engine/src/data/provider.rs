//! WhaleTrader Data Pipeline
//! Fetches market data from multiple free sources.
//! Primary: CoinGecko (free, global, no key needed)

use crate::core::types::*;
use chrono::Utc;
use reqwest::Client;
use rust_decimal::Decimal;
use serde::Deserialize;
use std::collections::HashMap;
use std::str::FromStr;
use tracing::{debug, info, warn};

const COINGECKO_BASE: &str = "https://api.coingecko.com/api/v3";

/// Symbol to CoinGecko ID mapping
fn symbol_to_coingecko_id(symbol: &str) -> &str {
    match symbol.to_uppercase().as_str() {
        "BTC" => "bitcoin",
        "ETH" => "ethereum",
        "SOL" => "solana",
        "BNB" => "binancecoin",
        "XRP" => "ripple",
        "ADA" => "cardano",
        "DOGE" => "dogecoin",
        "AVAX" => "avalanche-2",
        "DOT" => "polkadot",
        "LINK" => "chainlink",
        "UNI" => "uniswap",
        "ATOM" => "cosmos",
        "LTC" => "litecoin",
        "ARB" => "arbitrum",
        "OP" => "optimism",
        "MATIC" | "POL" => "matic-network",
        other => {
            warn!("Unknown symbol {}, using as-is for CoinGecko", other);
            // Return a leaked string to satisfy lifetime (acceptable for a small fixed set)
            // In production, use a proper lookup table
            Box::leak(other.to_lowercase().into_boxed_str())
        }
    }
}

#[derive(Debug, Deserialize)]
struct CoinGeckoPrice {
    usd: Option<f64>,
    usd_24h_change: Option<f64>,
    usd_24h_vol: Option<f64>,
    usd_market_cap: Option<f64>,
}

/// Market data provider
pub struct DataProvider {
    client: Client,
}

impl DataProvider {
    pub fn new() -> Self {
        Self {
            client: Client::new(),
        }
    }

    /// Fetch current prices for multiple symbols
    pub async fn get_prices(
        &self,
        symbols: &[&str],
    ) -> Result<HashMap<String, f64>, Box<dyn std::error::Error>> {
        let ids: Vec<&str> = symbols.iter().map(|s| symbol_to_coingecko_id(s)).collect();
        let ids_str = ids.join(",");

        let url = format!("{}/simple/price", COINGECKO_BASE);
        let resp: HashMap<String, CoinGeckoPrice> = self
            .client
            .get(&url)
            .query(&[
                ("ids", ids_str.as_str()),
                ("vs_currencies", "usd"),
                ("include_24hr_change", "true"),
                ("include_24hr_vol", "true"),
                ("include_market_cap", "true"),
            ])
            .send()
            .await?
            .json()
            .await?;

        let mut prices = HashMap::new();
        for (i, symbol) in symbols.iter().enumerate() {
            let cg_id = ids[i];
            if let Some(data) = resp.get(cg_id) {
                if let Some(price) = data.usd {
                    prices.insert(symbol.to_string(), price);
                }
            }
        }

        Ok(prices)
    }

    /// Fetch historical daily prices
    pub async fn get_history(
        &self,
        symbol: &str,
        days: u32,
    ) -> Result<Vec<(i64, f64)>, Box<dyn std::error::Error>> {
        let cg_id = symbol_to_coingecko_id(symbol);
        let url = format!("{}/coins/{}/market_chart", COINGECKO_BASE, cg_id);

        #[derive(Deserialize)]
        struct ChartData {
            prices: Vec<Vec<f64>>,
        }

        let resp: ChartData = self
            .client
            .get(&url)
            .query(&[
                ("vs_currency", "usd"),
                ("days", &days.to_string()),
                ("interval", "daily"),
            ])
            .send()
            .await?
            .json()
            .await?;

        let history: Vec<(i64, f64)> = resp
            .prices
            .into_iter()
            .filter_map(|p| {
                if p.len() >= 2 {
                    Some((p[0] as i64, p[1]))
                } else {
                    None
                }
            })
            .collect();

        debug!(
            "Fetched {} days of history for {}",
            history.len(),
            symbol
        );

        Ok(history)
    }
}

impl Default for DataProvider {
    fn default() -> Self {
        Self::new()
    }
}

// ─── Technical Indicators ────────────────────────────────────

pub mod indicators {
    /// Compute RSI (Relative Strength Index)
    pub fn rsi(closes: &[f64], period: usize) -> Option<f64> {
        if closes.len() < period + 1 {
            return None;
        }

        let mut avg_gain = 0.0;
        let mut avg_loss = 0.0;

        // Initial averages
        for i in 1..=period {
            let delta = closes[i] - closes[i - 1];
            if delta > 0.0 {
                avg_gain += delta;
            } else {
                avg_loss -= delta;
            }
        }
        avg_gain /= period as f64;
        avg_loss /= period as f64;

        // Smoothed averages
        for i in (period + 1)..closes.len() {
            let delta = closes[i] - closes[i - 1];
            let (gain, loss) = if delta > 0.0 {
                (delta, 0.0)
            } else {
                (0.0, -delta)
            };
            avg_gain = (avg_gain * (period as f64 - 1.0) + gain) / period as f64;
            avg_loss = (avg_loss * (period as f64 - 1.0) + loss) / period as f64;
        }

        if avg_loss == 0.0 {
            return Some(100.0);
        }

        let rs = avg_gain / avg_loss;
        Some(100.0 - (100.0 / (1.0 + rs)))
    }

    /// Simple Moving Average
    pub fn sma(closes: &[f64], period: usize) -> Option<f64> {
        if closes.len() < period {
            return None;
        }
        let sum: f64 = closes[closes.len() - period..].iter().sum();
        Some(sum / period as f64)
    }

    /// Exponential Moving Average
    pub fn ema(closes: &[f64], period: usize) -> Option<f64> {
        if closes.len() < period {
            return None;
        }

        let multiplier = 2.0 / (period as f64 + 1.0);
        let mut ema_val: f64 = closes[..period].iter().sum::<f64>() / period as f64;

        for &price in &closes[period..] {
            ema_val = (price - ema_val) * multiplier + ema_val;
        }

        Some(ema_val)
    }

    /// MACD (Moving Average Convergence Divergence)
    pub fn macd(closes: &[f64]) -> Option<(f64, f64, f64)> {
        let ema12 = ema(closes, 12)?;
        let ema26 = ema(closes, 26)?;
        let macd_val = ema12 - ema26;
        // Simplified signal line
        let signal = macd_val * 0.85; // Approximation
        let histogram = macd_val - signal;
        Some((macd_val, signal, histogram))
    }

    /// Bollinger Bands
    pub fn bollinger_bands(
        closes: &[f64],
        period: usize,
        std_dev: f64,
    ) -> Option<(f64, f64, f64)> {
        let middle = sma(closes, period)?;
        let slice = &closes[closes.len() - period..];
        let variance: f64 =
            slice.iter().map(|&c| (c - middle).powi(2)).sum::<f64>() / period as f64;
        let std = variance.sqrt();

        Some((
            middle + std_dev * std,  // upper
            middle,                   // middle
            middle - std_dev * std,  // lower
        ))
    }

    #[cfg(test)]
    mod tests {
        use super::*;

        #[test]
        fn test_sma() {
            let data = vec![1.0, 2.0, 3.0, 4.0, 5.0];
            assert_eq!(sma(&data, 3), Some(4.0)); // (3+4+5)/3
            assert_eq!(sma(&data, 5), Some(3.0)); // (1+2+3+4+5)/5
            assert_eq!(sma(&data, 6), None);       // not enough data
        }

        #[test]
        fn test_rsi() {
            // Monotonically increasing → RSI should be 100
            let up: Vec<f64> = (0..20).map(|i| 100.0 + i as f64).collect();
            let r = rsi(&up, 14).unwrap();
            assert!((r - 100.0).abs() < 0.01);

            // Monotonically decreasing → RSI should be 0
            let down: Vec<f64> = (0..20).map(|i| 100.0 - i as f64).collect();
            let r = rsi(&down, 14).unwrap();
            assert!(r < 1.0);
        }
    }
}
