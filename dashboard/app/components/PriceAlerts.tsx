"use client";

import { useState, useEffect, useRef } from "react";

/* ════════════════════════════════════════════════════════════════
   PRICE ALERTS — localStorage-based alert system
   ════════════════════════════════════════════════════════════════ */

export interface PriceAlert {
  id: string;
  ticker: string;
  targetPrice: number;
  direction: "above" | "below";
  createdAt: string;
  triggered: boolean;
}

const STORAGE_KEY = "finclaw_alerts";

/* ── Helpers ── */

export function loadAlerts(): PriceAlert[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch {
    // ignore
  }
  return [];
}

export function saveAlerts(alerts: PriceAlert[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(alerts));
  } catch {
    // ignore
  }
}

export function addAlert(
  ticker: string,
  targetPrice: number,
  direction: "above" | "below"
): PriceAlert {
  const alerts = loadAlerts();
  const alert: PriceAlert = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    ticker: ticker.toUpperCase(),
    targetPrice,
    direction,
    createdAt: new Date().toISOString(),
    triggered: false,
  };
  alerts.push(alert);
  saveAlerts(alerts);
  return alert;
}

export function removeAlert(id: string) {
  const alerts = loadAlerts().filter((a) => a.id !== id);
  saveAlerts(alerts);
}

export function checkAlerts(
  prices: Map<string, number>
): PriceAlert[] {
  const alerts = loadAlerts();
  const triggered: PriceAlert[] = [];
  let changed = false;

  for (const alert of alerts) {
    if (alert.triggered) continue;
    const price = prices.get(alert.ticker);
    if (price === undefined) continue;

    if (
      (alert.direction === "above" && price >= alert.targetPrice) ||
      (alert.direction === "below" && price <= alert.targetPrice)
    ) {
      alert.triggered = true;
      triggered.push(alert);
      changed = true;
    }
  }

  if (changed) saveAlerts(alerts);
  return triggered;
}

export function getActiveAlertCount(): number {
  return loadAlerts().filter((a) => !a.triggered).length;
}

export function getTriggeredAlertCount(): number {
  return loadAlerts().filter((a) => a.triggered).length;
}

/* ════════════════════════════════════════════════════════════════
   SET ALERT MODAL
   ════════════════════════════════════════════════════════════════ */

export function SetAlertModal({
  ticker,
  currentPrice,
  onClose,
}: {
  ticker: string;
  currentPrice: number;
  onClose: () => void;
}) {
  const [price, setPrice] = useState(currentPrice > 0 ? currentPrice.toFixed(2) : "");
  const [direction, setDirection] = useState<"above" | "below">("above");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const p = parseFloat(price);
    if (isNaN(p) || p <= 0) return;
    addAlert(ticker, p, direction);
    onClose();
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-[100]"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-[#13131a] border border-gray-800/60 rounded-lg p-6 w-full max-w-sm animate-fade-in">
        <h3 className="text-sm font-semibold text-gray-300 mb-4">
          Set Price Alert
        </h3>
        <p className="text-xs text-gray-500 mb-4">
          Alert when <span className="font-mono text-gray-300">{ticker}</span>{" "}
          crosses your target price
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Direction */}
          <div>
            <label className="text-xs text-gray-500 block mb-2">
              Trigger when price goes
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setDirection("above")}
                className={`flex-1 px-3 py-2 text-xs rounded border transition-colors ${
                  direction === "above"
                    ? "bg-green-950/40 border-green-800/50 text-[#22c55e]"
                    : "bg-gray-900/60 border-gray-700/50 text-gray-400 hover:text-gray-200"
                }`}
              >
                Above
              </button>
              <button
                type="button"
                onClick={() => setDirection("below")}
                className={`flex-1 px-3 py-2 text-xs rounded border transition-colors ${
                  direction === "below"
                    ? "bg-red-950/40 border-red-800/50 text-[#ef4444]"
                    : "bg-gray-900/60 border-gray-700/50 text-gray-400 hover:text-gray-200"
                }`}
              >
                Below
              </button>
            </div>
          </div>

          {/* Price input */}
          <div>
            <label className="text-xs text-gray-500 block mb-1">
              Target Price ($)
            </label>
            <input
              ref={inputRef}
              type="number"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              step="any"
              placeholder="0.00"
              className="w-full px-3 py-2 text-sm bg-gray-900/60 border border-gray-700/50 rounded text-gray-200 placeholder-gray-600 focus:outline-none focus:border-slate-500/60 font-mono"
              required
            />
            {currentPrice > 0 && (
              <p className="text-[10px] text-gray-600 mt-1">
                Current: ${currentPrice.toFixed(2)}
              </p>
            )}
          </div>

          {/* Preview */}
          {price && parseFloat(price) > 0 && (
            <div className="rounded bg-gray-900/40 border border-gray-800/40 p-3">
              <p className="text-xs text-gray-400">
                Alert when{" "}
                <span className="font-mono text-gray-200">{ticker}</span>{" "}
                {direction === "above" ? "rises above" : "falls below"}{" "}
                <span className="font-mono text-gray-200">
                  ${parseFloat(price).toFixed(2)}
                </span>
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs text-gray-400 hover:text-gray-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-xs bg-slate-700/60 border border-slate-600/50 rounded text-white hover:bg-slate-700/80 transition-colors"
            >
              Set Alert
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   ALERTS BADGE — shows count in header
   ════════════════════════════════════════════════════════════════ */

export function AlertsBadge() {
  const [activeCount, setActiveCount] = useState(0);
  const [triggeredCount, setTriggeredCount] = useState(0);
  const [showPanel, setShowPanel] = useState(false);
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const update = () => {
      const all = loadAlerts();
      setAlerts(all);
      setActiveCount(all.filter((a) => !a.triggered).length);
      setTriggeredCount(all.filter((a) => a.triggered).length);
    };
    update();
    const interval = setInterval(update, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setShowPanel(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleRemoveAlert = (id: string) => {
    removeAlert(id);
    const all = loadAlerts();
    setAlerts(all);
    setActiveCount(all.filter((a) => !a.triggered).length);
    setTriggeredCount(all.filter((a) => a.triggered).length);
  };

  if (activeCount === 0 && triggeredCount === 0) return null;

  return (
    <div ref={panelRef} className="relative">
      <button
        onClick={() => setShowPanel(!showPanel)}
        className="relative px-2 py-1 text-xs text-gray-400 hover:text-gray-200 transition-colors"
        title="Price Alerts"
      >
        <span className="font-mono">Alerts</span>
        {activeCount > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-slate-600 rounded-full text-[9px] text-white flex items-center justify-center font-mono">
            {activeCount}
          </span>
        )}
        {triggeredCount > 0 && (
          <span className="absolute -top-1 right-4 w-4 h-4 bg-[#22c55e] rounded-full text-[9px] text-black flex items-center justify-center font-mono animate-pulse">
            !
          </span>
        )}
      </button>

      {showPanel && (
        <div className="absolute top-full right-0 mt-2 w-72 bg-[#13131a] border border-gray-700/60 rounded shadow-xl z-[60] max-h-80 overflow-y-auto">
          {alerts.length === 0 ? (
            <p className="p-4 text-xs text-gray-600 text-center">
              No alerts set
            </p>
          ) : (
            <div>
              <div className="px-3 py-2 border-b border-gray-800/40">
                <p className="text-[10px] text-gray-500 uppercase tracking-wider">
                  {activeCount} active / {triggeredCount} triggered
                </p>
              </div>
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`px-3 py-2.5 border-b border-gray-800/30 flex items-center justify-between text-xs ${
                    alert.triggered ? "bg-green-950/10" : ""
                  }`}
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold text-gray-200">
                        {alert.ticker}
                      </span>
                      {alert.triggered && (
                        <span className="text-[9px] px-1 py-0.5 bg-green-950/40 text-[#22c55e] rounded">
                          TRIGGERED
                        </span>
                      )}
                    </div>
                    <p className="text-gray-500 text-[10px] mt-0.5">
                      {alert.direction === "above" ? "Above" : "Below"} $
                      {alert.targetPrice.toFixed(2)}
                    </p>
                  </div>
                  <button
                    onClick={() => handleRemoveAlert(alert.id)}
                    className="text-gray-600 hover:text-red-400 transition-colors font-mono"
                  >
                    X
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
