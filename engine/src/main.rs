//! WhaleTrader — AI-Powered Quantitative Trading Engine
//! Main entry point for the Rust engine.

use rust_decimal::Decimal;
use std::str::FromStr;
use whale_engine::{DataProvider, Engine, PaperExchange, Side};

#[tokio::main]
async fn main() {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .init();

    println!(r#"
 __      ___         _     _____              _
 \ \    / / |_  __ _| |___|_   _| _ __ _ __| |___ _ _
  \ \/\/ /| ' \/ _` | / -_) | || '_/ _` / _` / -_) '_|
   \_/\_/ |_||_\__,_|_\___| |_||_| \__,_\__,_\___|_|

   AI-Powered Quantitative Trading Engine v0.1.0
   Built with Rust + Python + TypeScript
"#);

    // Initialize engine
    let engine = Engine::new();
    engine.start().await;

    // Initialize paper trading
    let mut exchange = PaperExchange::new(Decimal::new(10_000, 0));

    // Fetch live prices
    let provider = DataProvider::new();

    println!("\nFetching live market data...\n");

    match provider.get_prices(&["BTC", "ETH", "SOL"]).await {
        Ok(prices) => {
            for (symbol, price) in &prices {
                println!("  {} = ${:.2}", symbol, price);
            }

            // Update positions with live prices
            for (symbol, price) in &prices {
                exchange.update_price(symbol, Decimal::from_str(&format!("{:.2}", price)).unwrap_or_default());
            }
        }
        Err(e) => {
            eprintln!("Failed to fetch prices: {}", e);
        }
    }

    // Fetch BTC history & compute indicators
    println!("\nComputing technical indicators for BTC...\n");
    match provider.get_history("BTC", 200).await {
        Ok(history) => {
            let closes: Vec<f64> = history.iter().map(|(_, p)| *p).collect();
            
            use whale_engine::data::provider::indicators;
            
            if let Some(rsi) = indicators::rsi(&closes, 14) {
                println!("  RSI(14):  {:.1}", rsi);
            }
            if let Some(sma) = indicators::sma(&closes, 20) {
                println!("  SMA(20):  ${:.2}", sma);
            }
            if let Some(sma) = indicators::sma(&closes, 50) {
                println!("  SMA(50):  ${:.2}", sma);
            }
            if let Some(sma) = indicators::sma(&closes, 200) {
                println!("  SMA(200): ${:.2}", sma);
            }
            if let Some((macd, signal, hist)) = indicators::macd(&closes) {
                println!("  MACD:     {:.2} | Signal: {:.2} | Hist: {:.2}", macd, signal, hist);
            }
            if let Some((upper, middle, lower)) = indicators::bollinger_bands(&closes, 20, 2.0) {
                println!("  BB:       ${:.2} / ${:.2} / ${:.2}", upper, middle, lower);
            }
        }
        Err(e) => {
            eprintln!("Failed to fetch history: {}", e);
        }
    }

    // Show portfolio
    let snapshot = exchange.snapshot();
    println!("\nPortfolio:");
    println!("  Cash:          ${}", snapshot.cash);
    println!("  Total Value:   ${}", snapshot.total_value);
    println!("  P&L:           ${} ({:.2}%)", snapshot.total_pnl, snapshot.total_pnl_pct);
    println!("  Positions:     {}", snapshot.positions.len());

    engine.stop().await;
}
