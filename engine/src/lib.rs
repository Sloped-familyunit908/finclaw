//! WhaleTrader Engine
//! High-performance trading engine core.

pub mod core;
pub mod data;
pub mod exchange;

pub use core::engine::Engine;
pub use core::types::*;
pub use data::provider::DataProvider;
pub use exchange::paper::PaperExchange;
