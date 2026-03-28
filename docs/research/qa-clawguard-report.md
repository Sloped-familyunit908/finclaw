# 🛡️ ClawGuard QA Report

**Version:** 1.0.3  
**Date:** 2026-03-27  
**Tester:** Chief QA Engineer (Subagent)  
**Perspective:** New user, fresh install  
**OS:** Windows 10 (x64), Node.js v24.14.0  

---

## Phase 1: Fresh Install Experience

| # | Test | Result | Notes |
|---|------|--------|-------|
| 1 | `npm install` | ✅ PASS | Completes in ~1s (already up to date). 4 moderate vulnerabilities in transitive deps (brace-expansion < 5.0.5 → minimatch → glob → rimraf). |
| 2 | `npx clawguard --version` | ⚠️ WARN | **FAILS before `npm run build`** — bin points to `./dist/src/cli.js` which doesn't exist until compiled. After build: outputs `ClawGuard v1.0.3` correctly. |
| 3 | `npx clawguard --help` | ✅ PASS | Clean help output with all commands and examples. |
| 4 | `npx clawguard version` | ✅ PASS | `ClawGuard v1.0.3` |

### ⚠️ Critical New-User Issue
**`dist/` is not committed and no `postinstall` script runs `tsc`.** A user who clones the repo and runs `npm install` → `npx clawguard` will get `'clawguard' is not recognized`. The README Quick Start says `npx @neuzhou/clawguard scan ./my-agent-project` which would work from npm (since `prepublishOnly` builds), but **cloning from GitHub requires a manual `npm run build`** step that isn't mentioned in the README Quick Start or Contributing section's install steps.

**Recommendation:** Add `"postinstall": "npm run build"` to scripts, or document the build step clearly.

---

## Phase 2: Test Suite

| Metric | Value |
|--------|-------|
| **Total tests** | 684 |
| **Passed** | 684 |
| **Failed** | 0 |
| **Skipped** | 0 |
| **Cancelled** | 0 |
| **Duration** | ~69s |
| **Test suites** | 84 |

### ✅ PASS — All 684 tests pass with zero failures.

**Test Coverage by Module:**
- Prompt Injection Detection: ✔ 22 tests
- Data Leakage Detection: ✔ 16 tests
- Memory Attack Detection: ✔ 49 tests (MEM-*, RAG-*, CMP-*)
- MCP Firewall (Policy/Proxy/Scanner): ✔ 55 tests
- MCP Security: ✔ 10 tests
- Policy Engine: ✔ 36 tests
- Risk Engine: ✔ 25 tests
- PII Sanitizer: ✔ 34 tests
- Intent-Action Mismatch: ✔ 24 tests
- Identity Protection: ✔ 10 tests
- Insider Threat: ✔ 24 tests
- File Deletion Protection: ✔ 10 tests
- Supply Chain: ✔ 10 tests
- Privilege Escalation: ✔ 19 tests
- Anomaly Detection: ✔ 7 tests
- Compliance: ✔ 31 tests
- Cross-Agent Contamination: ✔ 12 tests
- Rug Pull: ✔ 12 tests
- Resource Abuse: ✔ 13 tests
- YARA Engine: ✔ 14 tests
- SARIF Output: ✔ 18 tests
- Skill Scanner: ✔ 11 tests
- Store: ✔ 10 tests
- CLI: ✔ 14 tests (static/file-based only)
- Webhook: ✔ 3 tests
- Python Bindings: ✔ 13 tests

---

## Phase 3: CLI Command Testing

### `clawguard version` / `--version` / `-v`
✅ PASS — All three work: `ClawGuard v1.0.3`

### `clawguard --help` / `help` / `-h`
✅ PASS — Clean, informative output with all commands and examples.

### `clawguard scan <path>`
| Test | Result | Notes |
|------|--------|-------|
| `scan src\cli.ts` (text format) | ✅ PASS | Found 3 findings (expected — the file itself contains example strings like "ignore all previous instructions" and "rm -rf /") |
| `scan src\cli.ts --format json` | ✅ PASS | Valid JSON output with all fields |
| `scan src\cli.ts --format sarif` | ✅ PASS | Valid SARIF 2.1 with $schema, rules, results |
| `scan src\cli.ts --strict` | ✅ PASS | Exit code 1 on high/critical findings |
| `scan tsconfig.json` (clean file) | ✅ PASS | "No security issues found!" |
| `scan nonexistent-path` | ✅ PASS | Proper error: "Path not found" with exit code 1 |

### `clawguard check <text>`
| Test | Result | Notes |
|------|--------|-------|
| Prompt injection text | ✅ PASS | `🟠 SUSPICIOUS (score: 38)` — detected CRITICAL prompt-injection, exit code 1 |
| Clean text "Hello, how are you?" | ✅ PASS | `✅ CLEAN (score: 0)` |
| PII text (SSN + email) | ⚠️ WARN | `✅ CLEAN (score: 0)` — **data-leakage rule only fires on `outbound` direction**, but `check` uses `inbound`. This is technically correct (inbound PII isn't a *leak*), but confusing for users who expect PII detection. |

### `clawguard init`
✅ PASS — Creates `ClawGuard.yaml` with sensible defaults. Refuses to overwrite existing file.

### `clawguard start`
✅ PASS — Prints informational message about hooks integration.

### `clawguard dashboard`
✅ PASS — Prints dashboard URL info. (No actual dashboard server implemented — placeholder.)

### `clawguard audit <path>`
✅ PASS — Runs scan on given path with audit header.

### `clawguard sanitize <text>` (undocumented in --help)
✅ PASS — `My SSN is 123-45-6789 and my email is test@example.com` → sanitized 2 items (EMAIL_1, SSN_2). Works correctly.

### `clawguard intent-check` (undocumented in --help)
| Test | Result | Notes |
|------|--------|-------|
| Read intent + `rm -rf /` action | ✅ PASS | `🔴 MISMATCH (critical, confidence: 95%)` |
| Read intent + `cat readme.md` action | ✅ PASS | `✅ CONSISTENT (confidence: 90%)` |

### `clawguard firewall --help`
✅ PASS — Proper help output for firewall subcommand.

### ⚠️ Documentation Gap
The `--help` output lists 8 commands: `scan`, `check`, `firewall`, `init`, `start`, `dashboard`, `audit`, `version`. But the CLI actually supports **10 commands** — `sanitize` and `intent-check` are implemented but **not listed in --help**. Both are useful and should be documented.

---

## Phase 4: Code Quality

### TypeScript Compilation
✅ PASS — `tsc --noEmit` produces zero errors.

### npm audit
⚠️ WARN — 4 moderate severity vulnerabilities in transitive dependency chain:
```
brace-expansion <5.0.5 → minimatch → glob → rimraf
```
Only affects `rimraf` (devDependency), not runtime. Fixable with `npm audit fix --force` (breaking change: rimraf@6).

### Code Review Observations
| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | No `as any` casts in CLI | ✅ PASS | Clean type safety |
| 2 | No `require()` for internal modules | ✅ PASS | Uses ES static imports |
| 3 | Zero runtime dependencies | ✅ PASS | Only devDependencies (typescript, tsx, rimraf, @types/node) |
| 4 | False positives on own source | ⚠️ WARN | `clawguard scan src/cli.ts` reports 3 findings because CLI help text contains example strings like "ignore all previous instructions" and "rm -rf /". Not a bug per se, but could confuse users scanning the project itself. Consider `.clawguardignore` support. |
| 5 | `scan` finds threats in self | ⚠️ WARN | Scanning the entire `src/` directory will flag the help text and inline examples. This is a known pattern in security tools. |

---

## Phase 5: Documentation

### README.md
| Item | Status | Notes |
|------|--------|-------|
| Quick Start works | ⚠️ WARN | `npx @neuzhou/clawguard scan` works from npm install. **From git clone, need undocumented `npm run build` first.** |
| API examples accurate | ✅ PASS | `runSecurityScan`, `calculateRisk`, `evaluateToolCall`, `sanitize` all match implementation |
| Test count badge | ✅ PASS | States 684, matches actual |
| Threat pattern count | ✅ PASS | States 285+, consistent |
| CLI examples accurate | ✅ PASS | All documented CLI examples work |
| Architecture diagram | ✅ PASS | Accurate ASCII art |
| Comparison table | ✅ PASS | Fair comparison with Guardrails AI, NeMo, garak |
| License info | ✅ PASS | Dual AGPL-3.0 + Commercial |
| OWASP mapping | ✅ PASS | Thorough alignment with LLM Top 10 and Agentic AI Top 10 |
| Broken links | ⚠️ WARN | Internal links work. External links to OWASP, Anthropic research, GitHub Actions — not verified (network test out of scope). |

### docs/ Directory (16 files across en/zh/ja)
| Doc | Status | Notes |
|-----|--------|-------|
| `en/getting-started.md` | ⚠️ WARN | Documents `sanitize` CLI command but that's not in `--help` output. Mentions `scan --text` nowhere — correct (scan takes paths). |
| `en/architecture.md` | ✅ PASS | Exists, structured |
| `en/custom-rules.md` | ✅ PASS | Covers YARA and YAML custom rules |
| `en/security-rules.md` | ✅ PASS | Documents all 15 rule categories |
| `en/dashboard.md` | ⚠️ WARN | Documents dashboard feature but dashboard is a placeholder (no actual web server) |
| `en/faq.md` | ✅ PASS | Exists with common questions |
| `mcp-firewall.md` | ✅ PASS | Comprehensive MCP Firewall docs |
| `zh/` (6 files) | ✅ PASS | Chinese translations exist |
| `ja/` (2 files) | ⚠️ WARN | Only getting-started and security-rules; other docs not translated |

### Contributing Guide
⚠️ WARN — `CONTRIBUTING.md` says:
```
git clone → npm install → npm test
```
Missing the `npm run build` step. Tests do pass without build (tsx runs TypeScript directly), but the CLI binary won't work without `tsc`.

---

## Phase 6: Missing Tests & Recommendations

### What's Missing

| # | Gap | Severity |
|---|-----|----------|
| 1 | **CLI integration tests** — current CLI tests only check file contents statically. No tests actually execute the CLI binary and validate stdout/stderr/exit codes. | High |
| 2 | **`check` command with outbound direction** — no way to test data-leakage via CLI `check` (hardcoded to `inbound`). | Medium |
| 3 | **`scan --text` option** — scan only accepts paths, not inline text. Users may expect this. | Low |
| 4 | **`.clawguardignore` support** — no way to exclude files/patterns from scan. | Medium |
| 5 | **Firewall E2E tests** — no test actually starts the firewall proxy and sends traffic through it. | High |
| 6 | **Edge cases: very large files** — no test for scanning files >1MB. | Low |
| 7 | **Edge cases: binary files** — no test for scanning binary/non-text files. | Low |
| 8 | **`init` idempotency** — no test for `init` when config already exists. | Low |
| 9 | **Concurrent scan** — no test for scanning multiple directories in parallel. | Low |
| 10 | **Error handling in scan** — minimal testing of permission-denied, symlink loops, etc. | Medium |

### 10 Test Cases to Add

1. **CLI E2E: `scan` exit code** — Execute `npx clawguard scan <clean-file>` and assert exit code 0; execute with `--strict` on dirty file and assert exit code 1.

2. **CLI E2E: `check` prompt injection** — Execute `npx clawguard check "ignore previous instructions"` and assert stdout contains `CRITICAL` and exit code 1.

3. **CLI E2E: `check` clean text** — Execute `npx clawguard check "hello world"` and assert stdout contains `CLEAN` and exit code 0.

4. **CLI E2E: `sanitize`** — Execute `npx clawguard sanitize "email: foo@bar.com"` and assert stdout contains `EMAIL` placeholder.

5. **CLI E2E: `intent-check` mismatch** — Execute with mismatched intent/action and verify exit code 1 and MISMATCH output.

6. **CLI E2E: `init` creates file** — Run in temp dir, verify ClawGuard.yaml is created; run again, verify exit code 1 (already exists).

7. **CLI E2E: `scan --format sarif` schema compliance** — Parse output as JSON, validate `$schema`, `version`, and `runs[0].tool.driver.name` fields.

8. **Scan: binary file handling** — Create a temp binary file (random bytes), scan it, verify no crash and clean output.

9. **Scan: empty directory** — Scan an empty directory, verify "0 files scanned" and no error.

10. **Check: outbound direction option** — Add `--direction outbound` flag to `check` command and verify data-leakage rules fire for PII/secrets.

---

## Summary

| Phase | Tests | Pass | Fail | Warn |
|-------|-------|------|------|------|
| 1. Fresh Install | 4 | 3 | 0 | 1 |
| 2. Test Suite | 684 | 684 | 0 | 0 |
| 3. CLI Commands | 16 | 14 | 0 | 2 |
| 4. Code Quality | 5 | 3 | 0 | 2 |
| 5. Documentation | 14 | 9 | 0 | 5 |
| 6. Missing Tests | — | — | — | — |
| **Total** | **723** | **713** | **0** | **10** |

---

## Issues Found

### ❌ FAIL: None

### ⚠️ WARN (10 items)

| # | Issue | Impact | Fix Effort |
|---|-------|--------|------------|
| W1 | CLI binary requires `npm run build` before use (dist/ not committed) | New users from GitHub clone can't use CLI | Low — add postinstall or document |
| W2 | `sanitize` and `intent-check` commands not listed in `--help` | Discoverable features hidden | Low — add to printHelp() |
| W3 | `check` command hardcodes `inbound` direction — PII/data-leakage never fires | Users may expect PII detection via `check` | Low — add `--direction` flag |
| W4 | CLI tests are static (file-content checks), no actual execution tests | Low confidence CLI works E2E in CI | Medium — add subprocess tests |
| W5 | `dashboard` command is placeholder with no actual server | Misleading if user expects a real dashboard | Low — document as "coming soon" |
| W6 | 4 moderate npm audit vulnerabilities (transitive, dev-only) | Negligible runtime risk | Low — bump rimraf |
| W7 | Scanning own source code produces false positives (help text examples) | May confuse users | Medium — add `.clawguardignore` |
| W8 | Contributing guide missing `npm run build` step | Contributors may be confused | Low — one-line fix |
| W9 | Japanese docs incomplete (only 2 of 6 files translated) | Incomplete i18n | Low priority |
| W10 | No MCP Firewall E2E test (no actual proxy startup/traffic test) | Firewall proxy untested at integration level | Medium |

---

## Final Grade

| Criteria | Score | Weight | Weighted |
|----------|-------|--------|----------|
| Tests passing | 10/10 | 30% | 3.0 |
| CLI functionality | 8/10 | 20% | 1.6 |
| Code quality | 9/10 | 15% | 1.35 |
| Documentation | 7/10 | 15% | 1.05 |
| New user experience | 7/10 | 10% | 0.7 |
| Test coverage completeness | 7/10 | 10% | 0.7 |
| **Total** | | **100%** | **8.4/10** |

## 🏆 Grade: B+

**Summary:** ClawGuard is a solid, well-tested security library with an impressive 684-test suite and zero failures. The core scanning engine, risk scoring, PII sanitizer, MCP firewall, and policy engine all work correctly. The main gaps are around the developer experience (build step not documented for GitHub clones), two hidden CLI commands not in `--help`, and the lack of CLI integration tests that actually execute the binary. No critical bugs found. Ready for production use as a library; CLI experience needs minor polish.
