# Infrastructure Report — 2026-03-27

## 1. SECURITY.md — Created & Pushed

| Project     | Commit   | Content                                                    |
| ----------- | -------- | ---------------------------------------------------------- |
| agentprobe  | f6088a5  | Supported: 0.1.x. Security test generation highlighted.   |
| clawguard   | 261d1f0  | Supported: 1.x.x. Self-scanning with own threat patterns. |
| finclaw     | 674d9a0  | Supported: 5.x.x. No hardcoded API keys policy.           |

All include:
- Vulnerability reporting via email (security@neuzhou.dev) or GitHub private advisory
- 48-hour response commitment
- Supported versions table

## 2. GitHub Releases

| Project     | Tag     | Title                                                      | Status           |
| ----------- | ------- | ---------------------------------------------------------- | ---------------- |
| agentprobe  | v0.1.1  | v0.1.1 — Playwright for AI Agents                         | Already existed  |
| clawguard   | v1.0.3  | v1.0.3 — The Immune System for AI Agents                  | Already existed  |
| finclaw     | v5.2.0  | v5.2.0 — Walk-Forward Validation + Self-Evolving Strategies | Created ✅      |

Release URL: https://github.com/NeuZhou/finclaw/releases/tag/v5.2.0

## 3. ClawGuard CI Upgrade

**Commit:** 7679a80  
**Before:** Single Ubuntu runner, Node 20 only, `npm install` + `tsc --noEmit` + `npm test`  
**After:** Full matrix matching agentprobe's CI quality:

- **OS matrix:** ubuntu-latest, windows-latest, macos-latest
- **Node matrix:** 18, 20, 22
- **Steps:** `npm ci` → `npm run lint` → `npm run build` → `npm test`
- **Added:** `publish-dry` job (npm pack --dry-run) gated on test matrix pass

Total: 9 test configurations (3 OS × 3 Node versions) + 1 publish-dry check.
