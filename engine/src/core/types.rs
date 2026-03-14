//! WhaleTrader Core Types
//! Fundamental data structures used across the entire engine.

use chrono::{DateTime, Utc};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use std::fmt;
use uuid::Uuid;

// ─── Asset & Market ───────────────────────────────────────────

/// Supported asset classes
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AssetClass {
    Crypto,
    Equity,
    Forex,
    Commodity,
    Index,
}

/// A tradeable instrument
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Instrument {
    pub symbol: String,
    pub base: String,       // e.g., "BTC"
    pub quote: String,      // e.g., "USDT"
    pub asset_class: AssetClass,
    pub exchange: String,
    pub min_quantity: Decimal,
    pub tick_size: Decimal,
    pub lot_size: Decimal,
}

impl fmt::Display for Instrument {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}:{}", self.exchange, self.symbol)
    }
}

// ─── Price Data ───────────────────────────────────────────────

/// OHLCV candlestick bar
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Bar {
    pub instrument: String,
    pub timestamp: DateTime<Utc>,
    pub open: Decimal,
    pub high: Decimal,
    pub low: Decimal,
    pub close: Decimal,
    pub volume: Decimal,
    pub interval: BarInterval,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum BarInterval {
    #[serde(rename = "1m")]
    Min1,
    #[serde(rename = "5m")]
    Min5,
    #[serde(rename = "15m")]
    Min15,
    #[serde(rename = "1h")]
    Hour1,
    #[serde(rename = "4h")]
    Hour4,
    #[serde(rename = "1d")]
    Day1,
    #[serde(rename = "1w")]
    Week1,
}

/// Real-time quote tick
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tick {
    pub instrument: String,
    pub bid: Decimal,
    pub ask: Decimal,
    pub last: Decimal,
    pub volume: Decimal,
    pub timestamp: DateTime<Utc>,
}

// ─── Orders ──────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Side {
    Buy,
    Sell,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrderType {
    Market,
    Limit,
    StopLoss,
    StopLimit,
    TrailingStop,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrderStatus {
    Pending,
    Submitted,
    PartiallyFilled,
    Filled,
    Cancelled,
    Rejected,
    Expired,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TimeInForce {
    Gtc,  // Good Till Cancel
    Ioc,  // Immediate or Cancel
    Fok,  // Fill or Kill
    Day,  // Day order
}

/// A trading order
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Order {
    pub id: Uuid,
    pub client_id: String,
    pub instrument: String,
    pub side: Side,
    pub order_type: OrderType,
    pub quantity: Decimal,
    pub price: Option<Decimal>,
    pub stop_price: Option<Decimal>,
    pub time_in_force: TimeInForce,
    pub status: OrderStatus,
    pub filled_quantity: Decimal,
    pub avg_fill_price: Option<Decimal>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub reason: String,  // AI agent's reasoning
}

impl Order {
    pub fn market(instrument: &str, side: Side, quantity: Decimal, reason: &str) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4(),
            client_id: format!("WT-{}", &Uuid::new_v4().to_string()[..8]),
            instrument: instrument.to_string(),
            side,
            order_type: OrderType::Market,
            quantity,
            price: None,
            stop_price: None,
            time_in_force: TimeInForce::Ioc,
            status: OrderStatus::Pending,
            filled_quantity: Decimal::ZERO,
            avg_fill_price: None,
            created_at: now,
            updated_at: now,
            reason: reason.to_string(),
        }
    }

    pub fn limit(
        instrument: &str,
        side: Side,
        quantity: Decimal,
        price: Decimal,
        reason: &str,
    ) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4(),
            client_id: format!("WT-{}", &Uuid::new_v4().to_string()[..8]),
            instrument: instrument.to_string(),
            side,
            order_type: OrderType::Limit,
            quantity,
            price: Some(price),
            stop_price: None,
            time_in_force: TimeInForce::Gtc,
            status: OrderStatus::Pending,
            filled_quantity: Decimal::ZERO,
            avg_fill_price: None,
            created_at: now,
            updated_at: now,
            reason: reason.to_string(),
        }
    }
}

// ─── Positions ───────────────────────────────────────────────

/// An open position
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub instrument: String,
    pub side: Side,
    pub quantity: Decimal,
    pub avg_entry_price: Decimal,
    pub current_price: Decimal,
    pub unrealized_pnl: Decimal,
    pub realized_pnl: Decimal,
    pub opened_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

impl Position {
    pub fn market_value(&self) -> Decimal {
        self.quantity * self.current_price
    }

    pub fn pnl_percent(&self) -> Decimal {
        if self.avg_entry_price.is_zero() {
            return Decimal::ZERO;
        }
        ((self.current_price - self.avg_entry_price) / self.avg_entry_price)
            * Decimal::ONE_HUNDRED
    }
}

// ─── Signals ─────────────────────────────────────────────────

/// Trading signal produced by an AI agent
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Signal {
    pub id: Uuid,
    pub agent: String,
    pub instrument: String,
    pub direction: SignalDirection,
    pub strength: f64,       // -1.0 (strong sell) to 1.0 (strong buy)
    pub confidence: f64,     // 0.0 to 1.0
    pub reasoning: String,
    pub key_factors: Vec<String>,
    pub price_target: Option<Decimal>,
    pub stop_loss: Option<Decimal>,
    pub time_horizon: TimeHorizon,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SignalDirection {
    StrongBuy,
    Buy,
    Neutral,
    Sell,
    StrongSell,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TimeHorizon {
    Scalp,    // minutes
    Short,    // hours-days
    Medium,   // days-weeks
    Long,     // weeks-months
    Position, // months-years
}

// ─── Portfolio ───────────────────────────────────────────────

/// Portfolio snapshot
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PortfolioSnapshot {
    pub timestamp: DateTime<Utc>,
    pub cash: Decimal,
    pub positions_value: Decimal,
    pub total_value: Decimal,
    pub total_pnl: Decimal,
    pub total_pnl_pct: Decimal,
    pub positions: Vec<Position>,
    pub daily_return: Option<Decimal>,
    pub sharpe_ratio: Option<f64>,
    pub max_drawdown: Option<f64>,
}

// ─── Events ──────────────────────────────────────────────────

/// Core event types for the event-driven architecture
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Event {
    TickUpdate(Tick),
    BarUpdate(Bar),
    SignalGenerated(Signal),
    OrderSubmitted(Order),
    OrderFilled {
        order_id: Uuid,
        fill_price: Decimal,
        fill_quantity: Decimal,
        timestamp: DateTime<Utc>,
    },
    OrderCancelled {
        order_id: Uuid,
        reason: String,
    },
    PositionOpened(Position),
    PositionClosed {
        instrument: String,
        realized_pnl: Decimal,
    },
    PortfolioUpdate(PortfolioSnapshot),
    DebateRound {
        topic: String,
        round: u32,
        statements: Vec<DebateStatement>,
    },
    Error {
        source: String,
        message: String,
    },
}

/// A statement in the Agent Debate Arena
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DebateStatement {
    pub agent: String,
    pub position: SignalDirection,
    pub argument: String,
    pub counter_to: Option<String>,  // which agent they're responding to
    pub confidence_change: f64,      // how debate affected confidence
}
