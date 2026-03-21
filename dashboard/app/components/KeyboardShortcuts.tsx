"use client";

import { useEffect, useState, useCallback } from "react";

/* ════════════════════════════════════════════════════════════════
   KEYBOARD SHORTCUTS — FinClaw
   Global keyboard shortcuts with help modal
   ════════════════════════════════════════════════════════════════ */

const SHORTCUTS = [
  { key: "/", label: "Focus search" },
  { key: "Esc", label: "Close panel / Go back" },
  { key: "?", label: "Show this help" },
];

export default function KeyboardShortcuts() {
  const [showHelp, setShowHelp] = useState(false);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Don't trigger when typing in inputs
      const tag = (document.activeElement?.tagName ?? "").toLowerCase();
      const isInput = tag === "input" || tag === "textarea" || tag === "select";
      const isEditable = (document.activeElement as HTMLElement)?.isContentEditable;

      // Help modal dismiss — any key closes it
      if (showHelp) {
        setShowHelp(false);
        e.preventDefault();
        return;
      }

      if (isInput || isEditable) return;

      switch (e.key) {
        case "/": {
          e.preventDefault();
          // Find the search input in the header
          const searchInput = document.querySelector<HTMLInputElement>(
            'input[placeholder="Search ticker..."]',
          );
          if (searchInput) {
            searchInput.focus();
            searchInput.select();
          }
          break;
        }
        case "Escape": {
          // Close chat panel if open
          const chatToggle = document.querySelector<HTMLButtonElement>(
            '[data-chat-toggle]',
          );
          if (chatToggle) {
            chatToggle.click();
          }
          break;
        }
        case "?": {
          e.preventDefault();
          setShowHelp(true);
          break;
        }
      }
    },
    [showHelp],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  if (!showHelp) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={() => setShowHelp(false)}
    >
      <div
        className="bg-[#13131a] border border-gray-700/60 rounded-lg shadow-2xl p-6 max-w-sm w-full mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-sm font-semibold text-gray-300 mb-4">
          Keyboard Shortcuts
        </h2>
        <div className="space-y-3">
          {SHORTCUTS.map((s) => (
            <div key={s.key} className="flex items-center justify-between">
              <kbd className="px-2 py-1 text-xs font-mono bg-gray-800/80 border border-gray-700/50 rounded text-gray-300 min-w-[2.5rem] text-center">
                {s.key}
              </kbd>
              <span className="text-sm text-gray-400 ml-4">{s.label}</span>
            </div>
          ))}
        </div>
        <p className="text-[10px] text-gray-600 mt-4 pt-3 border-t border-gray-800/40 text-center">
          Press any key to dismiss
        </p>
      </div>
    </div>
  );
}
