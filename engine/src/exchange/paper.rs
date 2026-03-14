//! WhaleTrader Paper Trading Exchange
//! Simulates real exchange behavior without risking money.

use crate::core::types::*;
use chrono::Utc;
use rust_decimal::Decimal;
use std::collections::HashMap;
use tracing::{info, warn};
use uuid::Uuid;

/// Paper trading engine — simulates an exchange
pub struct PaperExchange {
    cash: Decimal,
    initial_capital: Decimal,
    positions: HashMap<String, Position>,
    orders: Vec<Order>,
    trade_count: u64,
}

impl PaperExchange {
    pub fn new(initial_capital: Decimal) -> Self {
        info!("Paper exchange initialized with ${} capital", initial_capital);
        Self {
            cash: initial_capital,
            initial_capital,
            positions: HashMap::new(),
            orders: Vec::new(),
            trade_count: 0,
        }
    }

    pub fn cash(&self) -> Decimal {
        self.cash
    }

    pub fn total_value(&self) -> Decimal {
        let pos_value: Decimal = self.positions.values().map(|p| p.market_value()).sum();
        self.cash + pos_value
    }

    pub fn total_pnl(&self) -> Decimal {
        self.total_value() - self.initial_capital
    }

    pub fn positions(&self) -> &HashMap<String, Position> {
        &self.positions
    }

    /// Update market prices for all positions
    pub fn update_price(&mut self, instrument: &str, price: Decimal) {
        if let Some(pos) = self.positions.get_mut(instrument) {
            pos.current_price = price;
            pos.unrealized_pnl = (price - pos.avg_entry_price) * pos.quantity;
            pos.updated_at = Utc::now();
        }
    }

    /// Execute a market order immediately at given price
    pub fn execute_market_order(
        &mut self,
        instrument: &str,
        side: Side,
        quantity: Decimal,
        price: Decimal,
        reason: &str,
    ) -> Result<Order, String> {
        let mut order = Order::market(instrument, side, quantity, reason);

        match side {
            Side::Buy => {
                let cost = quantity * price;
                if cost > self.cash {
                    order.status = OrderStatus::Rejected;
                    warn!(
                        "Order rejected: insufficient cash. Need {}, have {}",
                        cost, self.cash
                    );
                    return Err(format!(
                        "Insufficient cash: need ${}, have ${}",
                        cost, self.cash
                    ));
                }

                self.cash -= cost;
                self.trade_count += 1;

                if let Some(pos) = self.positions.get_mut(instrument) {
                    // Average up/down
                    let total_cost =
                        (pos.avg_entry_price * pos.quantity) + cost;
                    pos.quantity += quantity;
                    pos.avg_entry_price = total_cost / pos.quantity;
                    pos.current_price = price;
                    pos.updated_at = Utc::now();
                } else {
                    self.positions.insert(
                        instrument.to_string(),
                        Position {
                            instrument: instrument.to_string(),
                            side: Side::Buy,
                            quantity,
                            avg_entry_price: price,
                            current_price: price,
                            unrealized_pnl: Decimal::ZERO,
                            realized_pnl: Decimal::ZERO,
                            opened_at: Utc::now(),
                            updated_at: Utc::now(),
                        },
                    );
                }

                order.status = OrderStatus::Filled;
                order.filled_quantity = quantity;
                order.avg_fill_price = Some(price);
                order.updated_at = Utc::now();
            }
            Side::Sell => {
                let pos = self.positions.get(instrument);
                if pos.is_none() || pos.unwrap().quantity < quantity {
                    order.status = OrderStatus::Rejected;
                    let available = pos.map_or(Decimal::ZERO, |p| p.quantity);
                    return Err(format!(
                        "Insufficient position: want to sell {}, have {}",
                        quantity, available
                    ));
                }

                let proceeds = quantity * price;
                self.cash += proceeds;
                self.trade_count += 1;

                let pos = self.positions.get_mut(instrument).unwrap();
                let realized = (price - pos.avg_entry_price) * quantity;
                pos.realized_pnl += realized;
                pos.quantity -= quantity;
                pos.current_price = price;
                pos.updated_at = Utc::now();

                // Remove position if fully closed
                if pos.quantity <= Decimal::new(1, 8) {
                    // ~0 threshold
                    self.positions.remove(instrument);
                }

                order.status = OrderStatus::Filled;
                order.filled_quantity = quantity;
                order.avg_fill_price = Some(price);
                order.updated_at = Utc::now();
            }
        }

        info!(
            "Order filled: {} {} {} @ ${}",
            side_str(side),
            quantity,
            instrument,
            price
        );

        self.orders.push(order.clone());
        Ok(order)
    }

    /// Get portfolio snapshot
    pub fn snapshot(&self) -> PortfolioSnapshot {
        let positions: Vec<Position> = self.positions.values().cloned().collect();
        let positions_value: Decimal = positions.iter().map(|p| p.market_value()).sum();
        let total_value = self.cash + positions_value;
        let total_pnl = total_value - self.initial_capital;
        let total_pnl_pct = if self.initial_capital.is_zero() {
            Decimal::ZERO
        } else {
            (total_pnl / self.initial_capital) * Decimal::ONE_HUNDRED
        };

        PortfolioSnapshot {
            timestamp: Utc::now(),
            cash: self.cash,
            positions_value,
            total_value,
            total_pnl,
            total_pnl_pct,
            positions,
            daily_return: None,
            sharpe_ratio: None,
            max_drawdown: None,
        }
    }
}

fn side_str(side: Side) -> &'static str {
    match side {
        Side::Buy => "BUY",
        Side::Sell => "SELL",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_paper_exchange_buy() {
        let mut exchange = PaperExchange::new(Decimal::new(10_000, 0));
        assert_eq!(exchange.cash(), Decimal::new(10_000, 0));

        let order = exchange
            .execute_market_order(
                "BTC",
                Side::Buy,
                Decimal::new(1, 1), // 0.1 BTC
                Decimal::new(70_000, 0),
                "Test buy",
            )
            .unwrap();

        assert_eq!(order.status, OrderStatus::Filled);
        assert_eq!(exchange.cash(), Decimal::new(3_000, 0)); // 10000 - 7000
        assert_eq!(exchange.positions().len(), 1);
    }

    #[test]
    fn test_paper_exchange_buy_sell_pnl() {
        let mut exchange = PaperExchange::new(Decimal::new(10_000, 0));

        // Buy 0.1 BTC at 70,000
        exchange
            .execute_market_order(
                "BTC",
                Side::Buy,
                Decimal::new(1, 1),
                Decimal::new(70_000, 0),
                "Buy",
            )
            .unwrap();

        // Price goes to 80,000
        exchange.update_price("BTC", Decimal::new(80_000, 0));

        // Sell at 80,000
        exchange
            .execute_market_order(
                "BTC",
                Side::Sell,
                Decimal::new(1, 1),
                Decimal::new(80_000, 0),
                "Sell",
            )
            .unwrap();

        // Should have 10,000 + 1,000 profit = 11,000
        assert_eq!(exchange.cash(), Decimal::new(11_000, 0));
        assert_eq!(exchange.positions().len(), 0);
    }

    #[test]
    fn test_insufficient_cash() {
        let mut exchange = PaperExchange::new(Decimal::new(100, 0));

        let result = exchange.execute_market_order(
            "BTC",
            Side::Buy,
            Decimal::new(1, 0), // 1 BTC
            Decimal::new(70_000, 0),
            "Too expensive",
        );

        assert!(result.is_err());
    }
}
