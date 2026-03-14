//! WhaleTrader Event Bus
//! Central message bus for the event-driven architecture.
//! All components communicate through events.

use crate::core::types::Event;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{broadcast, RwLock};
use tracing::{debug, info};

/// Event handler callback type
pub type EventHandler = Arc<dyn Fn(Event) + Send + Sync>;

/// Central event bus for the trading engine
pub struct EventBus {
    sender: broadcast::Sender<Event>,
    _receiver: broadcast::Receiver<Event>,
    handlers: Arc<RwLock<HashMap<String, Vec<EventHandler>>>>,
    event_count: Arc<std::sync::atomic::AtomicU64>,
}

impl EventBus {
    pub fn new(capacity: usize) -> Self {
        let (sender, receiver) = broadcast::channel(capacity);
        Self {
            sender,
            _receiver: receiver,
            handlers: Arc::new(RwLock::new(HashMap::new())),
            event_count: Arc::new(std::sync::atomic::AtomicU64::new(0)),
        }
    }

    /// Publish an event to all subscribers
    pub fn publish(&self, event: Event) {
        self.event_count
            .fetch_add(1, std::sync::atomic::Ordering::Relaxed);

        let event_type = match &event {
            Event::TickUpdate(_) => "tick_update",
            Event::BarUpdate(_) => "bar_update",
            Event::SignalGenerated(_) => "signal_generated",
            Event::OrderSubmitted(_) => "order_submitted",
            Event::OrderFilled { .. } => "order_filled",
            Event::OrderCancelled { .. } => "order_cancelled",
            Event::PositionOpened(_) => "position_opened",
            Event::PositionClosed { .. } => "position_closed",
            Event::PortfolioUpdate(_) => "portfolio_update",
            Event::DebateRound { .. } => "debate_round",
            Event::Error { .. } => "error",
        };

        debug!(event_type, "Publishing event");

        // broadcast to channel subscribers
        let _ = self.sender.send(event);
    }

    /// Subscribe to events
    pub fn subscribe(&self) -> broadcast::Receiver<Event> {
        self.sender.subscribe()
    }

    /// Get total events published
    pub fn event_count(&self) -> u64 {
        self.event_count
            .load(std::sync::atomic::Ordering::Relaxed)
    }
}

impl Default for EventBus {
    fn default() -> Self {
        Self::new(10_000)
    }
}

/// The trading engine core — orchestrates all components
pub struct Engine {
    pub event_bus: Arc<EventBus>,
    running: Arc<std::sync::atomic::AtomicBool>,
}

impl Engine {
    pub fn new() -> Self {
        info!("Initializing WhaleTrader Engine v{}", env!("CARGO_PKG_VERSION"));
        Self {
            event_bus: Arc::new(EventBus::default()),
            running: Arc::new(std::sync::atomic::AtomicBool::new(false)),
        }
    }

    pub fn is_running(&self) -> bool {
        self.running.load(std::sync::atomic::Ordering::Relaxed)
    }

    pub async fn start(&self) {
        info!("WhaleTrader Engine starting...");
        self.running
            .store(true, std::sync::atomic::Ordering::Relaxed);
        info!("WhaleTrader Engine started");
    }

    pub async fn stop(&self) {
        info!("WhaleTrader Engine stopping...");
        self.running
            .store(false, std::sync::atomic::Ordering::Relaxed);
        info!(
            "WhaleTrader Engine stopped. Total events processed: {}",
            self.event_bus.event_count()
        );
    }
}

impl Default for Engine {
    fn default() -> Self {
        Self::new()
    }
}
