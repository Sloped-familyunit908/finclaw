# ClawGuard — Full Competitive Audit & Product Assessment

**Date:** 2026-03-27  
**Version audited:** 1.0.3 (`@neuzhou/clawguard`)  
**Repo:** https://github.com/NeuZhou/clawguard

---

## 1. Current State of ClawGuard

### 1.1 Codebase Overview

| Metric | Value |
|--------|-------|
| **Version** | 1.0.3 (npm: `@neuzhou/clawguard`) |
| **Language** | TypeScript (Node.js ≥ 18) |
| **Source files** | 46 `.ts` files in `src/` |
| **Test files** | 48 `.test.ts` files in `tests/` |
| **Tests** | **684 tests, 84 suites, 0 failures** |
| **Dependencies** | **Zero runtime dependencies** |
| **License** | Dual: AGPL-3.0 (open source) + Commercial |
| **Build** | `tsc` → `dist/` |
| **Test runner** | Node.js native `--test` with tsx |
| **CI** | GitHub Actions |
| **Python bindings** | Yes (`python/` directory, subprocess bridge) |

### 1.2 GitHub Stats (as of 2026-03-27)

| Metric | Value |
|--------|-------|
| Stars | 1 ⭐ |
| Forks | 0 |
| Open issues | 7 |

### 1.3 Project Structure

```
clawguard/
├── src/
│   ├── cli.ts                    # CLI entry point
│   ├── index.ts                  # Main exports
│   ├── security-engine.ts        # Core scanning engine
│   ├── risk-engine.ts            # Risk scoring
│   ├── policy-engine.ts          # Tool call governance
│   ├── sanitizer.ts              # PII sanitizer
│   ├── integrity.ts              # Hash chain / tamper detection
│   ├── intent-action.ts          # Intent-action mismatch
│   ├── alert-engine.ts           # Alerting
│   ├── cost-engine.ts            # Cost tracking
│   ├── skill-scanner.ts          # Skill file scanning
│   ├── store.ts                  # Local data store
│   ├── yara-engine.ts            # YARA-like rule engine
│   ├── types.ts                  # Type definitions
│   ├── behavioral/               # Behavioral analysis
│   │   ├── analyzer.ts
│   │   └── multi-agent-detector.ts
│   ├── evolution/                # Rule evolution / auto-proposal
│   │   └── rule-proposer.ts
│   ├── exporters/                # SARIF, JSONL, Syslog/CEF, Webhook
│   ├── mcp-firewall/             # MCP security proxy (6 files)
│   └── rules/                    # 15 detection rule modules
│       ├── prompt-injection.ts   # 93 patterns
│       ├── data-leakage.ts       # 62 patterns
│       ├── insider-threat.ts     # 39 patterns
│       ├── supply-chain.ts       # 35 patterns
│       ├── mcp-security.ts       # 20 patterns
│       ├── identity-protection.ts# 19 patterns
│       ├── file-protection.ts    # 16 patterns
│       ├── memory-attacks.ts     # Memory injection, RAG poisoning, CMP
│       ├── cross-agent-contamination.ts
│       ├── privilege-escalation.ts
│       ├── resource-abuse.ts
│       ├── rug-pull.ts
│       ├── anomaly-detection.ts
│       ├── compliance.ts
│       └── compliance-frameworks.ts
├── hooks/                        # OpenClaw real-time hook pack
├── skill/                        # OpenClaw skill definition
├── rules.d/                      # Custom rule directory
├── python/                       # Python bindings
├── docs/                         # Documentation
├── examples/                     # Usage examples
└── tests/                        # 684 tests (48 files)
```

### 1.4 Feature Categories (15 built-in rule modules)

| # | Rule Module | Pattern Count | Coverage |
|---|-------------|:---:|----------|
| 1 | Prompt Injection | 93 | 13 sub-categories, multi-language (12 langs), encoding evasion |
| 2 | Data Leakage | 62 | API keys (OpenAI/AWS/GCP/Azure/HuggingFace), PII, DB URIs, JWTs |
| 3 | Insider Threat | 39 | Self-preservation, deception, goal conflict, unauthorized sharing |
| 4 | Supply Chain | 35 | Obfuscated code, reverse shells, DNS exfil, typosquatting |
| 5 | MCP Security | 20 | Tool shadowing, SSRF, schema poisoning, shadow servers |
| 6 | Identity Protection | 19 | SOUL.md/IDENTITY.md/MEMORY.md tampering, persona swap |
| 7 | File Protection | 16 | Destructive deletes, device writes |
| 8 | Memory Attacks | 14+ (MEM) + 11 (RAG) + 12 (CMP) | Memory injection, RAG poisoning, conversation manipulation |
| 9 | Cross-Agent Contamination | 9+ | Agent-to-agent instruction passing, context poisoning |
| 10 | Privilege Escalation | 17+ | sudo, chmod, chown, docker --privileged, nsenter |
| 11 | Resource Abuse | 11+ | Crypto mining, fork bombs, disk filling, DoS tools |
| 12 | Rug Pull | 9+ | Trust exploitation, scope creep, fake emergencies |
| 13 | Anomaly Detection | 6+ | Rapid-fire, token bombs, loops, recursive sub-agents |
| 14 | Compliance | 20+ | Filesystem mods, privilege escalation, external URLs |
| 15 | Compliance Frameworks | 9+ | GDPR, SOX, data retention, minors, audit logs |

**Total: 285+ patterns across 15 rule categories**

### 1.5 Unique Capabilities

1. **MCP Firewall** — Drop-in security proxy for Model Context Protocol. Rug pull detection (tool description pinning), parameter sanitization, output injection scanning. *No competitor has this.*
2. **Insider Threat Detection** — Based on Anthropic's agentic misalignment research. Detects when the AI agent itself becomes the threat. *No competitor has this.*
3. **Zero Dependencies** — Pure TypeScript, no torch/transformers/ML models required. Instant startup, no GPU needed.
4. **Attack Chain Detection** — Auto-correlates findings into multi-step attack patterns with multipliers.
5. **Memory Attack Detection** — 37+ patterns for memory injection, RAG poisoning, conversation manipulation. *Novel category.*
6. **Agent Identity Protection** — Guards SOUL.md, IDENTITY.md, MEMORY.md, AGENTS.md against tampering. *Agent-native.*
7. **Intent-Action Mismatch** — Detects when stated intent doesn't match actual actions (e.g., "read" intent + delete action).
8. **SARIF Output** — GitHub Code Scanning native integration.
9. **OpenClaw Hook Pack** — Real-time message and tool call interception.
10. **Python Bindings** — Subprocess bridge for Python ecosystem integration.

### 1.6 Build & Test Health

- ✅ `npm install` — works (zero runtime deps)
- ✅ `npm test` — **684 tests pass, 0 failures** (67s runtime)
- ✅ CI runs on GitHub Actions
- ✅ Python directory exists with `setup.py` + `pyproject.toml`

---

## 2. Competitive Landscape

### 2.1 Competitor Matrix

| Project | Stars | Forks | Language | Scope | Backing |
|---------|:-----:|:-----:|----------|-------|---------|
| **NVIDIA garak** | 7,384 | 847 | Python | LLM red-teaming / vuln scanner | NVIDIA (corporate) |
| **Guardrails AI** | 6,595 | 558 | Python | LLM I/O validation + structured data | VC-backed startup ($32M+) |
| **NeMo Guardrails** | 5,862 | 635 | Python | Programmable conversational rails | NVIDIA (corporate) |
| **Meta PurpleLlama** | 4,087 | 710 | Python | LLM safety assessment tools | Meta (corporate) |
| **LLM Guard** (ProtectAI) | 2,738 | 364 | Python | Content moderation / security scanning | VC-backed ($60M+) |
| **Rebuff** (ProtectAI) | 1,454 | 132 | Python/TS | Prompt injection detection only | ProtectAI |
| **LangKit** (WhyLabs) | 979 | 71 | Python | LLM observability / monitoring | WhyLabs |
| **ClawGuard** | **1** | **0** | TypeScript | **AI agent security (full stack)** | Solo developer |

### 2.2 Detailed Competitor Analysis

#### NVIDIA garak (7.4K ⭐)
- **What it does:** LLM red-teaming tool. Probes for hallucination, data leakage, prompt injection, toxicity, jailbreaks. "nmap for LLMs."
- **Approach:** Active probing / attack simulation. Sends adversarial prompts to test model resilience.
- **Strengths:** Backed by NVIDIA, large probe library, multimodel support, academic paper.
- **Gaps for ClawGuard:**
  - ❌ No runtime protection (scan-time only, generates attacks but doesn't block them)
  - ❌ No tool call governance
  - ❌ No MCP security
  - ❌ No agent identity/memory protection
  - ❌ No insider threat detection
  - ❌ Requires Python + heavy dependencies

#### Guardrails AI (6.6K ⭐, $32M+ funded)
- **What it does:** Framework for adding input/output validators to LLM calls. Hub of community validators.
- **Approach:** Validator pipeline on LLM I/O. Structured data extraction.
- **Strengths:** Large validator ecosystem (Hub), good docs, structured output generation, well-funded.
- **Gaps for ClawGuard:**
  - ❌ No tool call governance policy engine
  - ❌ No MCP security
  - ❌ No insider threat / AI misalignment detection
  - ❌ No supply chain scanning
  - ❌ No file/identity protection
  - ❌ No attack chain correlation
  - ❌ No risk scoring engine
  - ❌ Focused on LLM I/O, not agent behavior

#### NeMo Guardrails (5.9K ⭐)
- **What it does:** Programmable guardrails for conversational LLM systems. Colang DSL for defining conversation flows.
- **Approach:** Dialog management + guardrail rules. Conversation steering.
- **Strengths:** NVIDIA backing, Colang DSL, academic paper, good for chatbot safety.
- **Gaps for ClawGuard:**
  - ❌ No tool call governance
  - ❌ No MCP security
  - ❌ No supply chain / file protection
  - ❌ No insider threat detection
  - ❌ No agent-specific protections (identity, memory)
  - ❌ Focused on conversations, not agent tool use
  - ❌ Heavy dependency chain (requires C++ compiler for annoy)

#### Meta PurpleLlama (4.1K ⭐)
- **What it does:** Safety assessment tools for LLMs. CyberSecEval benchmark + Llama Guard models.
- **Approach:** Model-based safety classification. Benchmark-driven.
- **Strengths:** Meta backing, Llama Guard models, CyberSecEval benchmark.
- **Gaps for ClawGuard:**
  - ❌ Assessment tool, not runtime protection
  - ❌ No tool call governance
  - ❌ No MCP/agent-specific security
  - ❌ No lightweight rule-based scanning
  - ❌ Requires running ML models (GPU)

#### LLM Guard (2.7K ⭐, ProtectAI)
- **What it does:** Security toolkit for LLM interactions. Input/output scanners.
- **Approach:** ML-model-based scanners (toxicity, prompt injection, PII, etc.) + heuristics.
- **Strengths:** Comprehensive scanner library, API deployment mode, backed by ProtectAI ($60M+).
- **Gaps for ClawGuard:**
  - ❌ No tool call governance
  - ❌ No MCP security
  - ❌ No insider threat / misalignment detection
  - ❌ No supply chain scanning
  - ❌ No attack chain detection
  - ❌ Requires torch/transformers (heavy, GPU-hungry)
  - ❌ Content moderation focus, not agent security
  - Has good PII anonymization (comparable to ClawGuard's sanitizer)

#### Rebuff (1.5K ⭐, ProtectAI)
- **What it does:** Prompt injection detection. 4-layer defense.
- **Approach:** Heuristics + LLM-based detection + VectorDB embeddings + canary tokens.
- **Strengths:** Multi-layer approach, canary token innovation, TypeScript SDK.
- **Gaps for ClawGuard:**
  - ❌ Prompt injection only (single threat vector)
  - ❌ Requires OpenAI API key + Pinecone (external deps, cost)
  - ❌ No tool call governance, MCP, supply chain, etc.
  - ❌ Still a prototype (own disclaimer)
  - ❌ No OWASP mapping
  - ClawGuard has 93 prompt injection patterns without requiring external API calls

### 2.3 Positioning Map

```
                    SCOPE: Narrow ←———————→ Broad (Agent Security)
                    
    Runtime ↑       LLM Guard          ClawGuard ★
    Protection      Rebuff             (tool governance + MCP firewall +
                    Guardrails AI       insider threat + 285 patterns)
                    NeMo Guardrails
                    
                    
    Assessment ↓    garak              PurpleLlama
    Only            (red-teaming)      (benchmarks)
```

---

## 3. ClawGuard's Unique Positioning

### 3.1 The One-Sentence Pitch

> **ClawGuard is the only security framework purpose-built for AI agents — protecting not just LLM I/O, but the agent's tools, files, MCP connections, identity, memory, and detecting when the agent itself becomes the threat.**

### 3.2 Differentiators Nobody Else Has

| Capability | ClawGuard | Closest Competitor | Gap |
|-----------|:---------:|:------------------:|-----|
| MCP Firewall (tool description pinning, rug pull) | ✅ | ❌ None | **Category creator** |
| Insider threat / AI misalignment detection | ✅ 39 patterns | ❌ None | **Category creator** |
| Agent identity protection (SOUL.md, etc.) | ✅ | ❌ None | **Agent-native** |
| Memory attack detection (MEM/RAG/CMP) | ✅ 37+ patterns | ❌ None | **Category creator** |
| Cross-agent contamination detection | ✅ | ❌ None | **Multi-agent native** |
| Tool call policy engine | ✅ | ❌ None (agent-level) | **Agent-native** |
| Attack chain correlation | ✅ | ❌ None | **Unique** |
| Zero dependencies, instant startup | ✅ | ❌ All competitors need Python+ML | **Dev experience** |
| OWASP Agentic AI Top 10 full mapping | ✅ | ⚠️ Partial (NeMo, Guardrails) | **Complete** |
| SARIF for GitHub Code Scanning | ✅ | ❌ None in this space | **CI/CD native** |

### 3.3 OWASP Compliance — Who Else Does This?

- **ClawGuard:** Full OWASP Agentic AI Top 10 mapping across all 15 rule categories
- **NeMo Guardrails:** Partial — covers LLM vulnerability scanning but not agent-specific categories
- **Guardrails AI:** Partial — focuses on LLM Top 10, not Agentic AI Top 10
- **LLM Guard:** Partial — content moderation alignment
- **Others:** None explicitly map to OWASP Agentic AI

### 3.4 PII Sanitizer Comparison

| Feature | ClawGuard | LLM Guard | Guardrails AI |
|---------|:---------:|:---------:|:------------:|
| Email detection | ✅ | ✅ | ✅ (via validator) |
| Phone numbers | ✅ | ✅ | ✅ |
| SSN | ✅ | ✅ | ✅ |
| Credit cards | ✅ | ✅ | ✅ |
| API keys (multi-provider) | ✅ (OpenAI, AWS, GCP, Azure, HuggingFace, DigitalOcean) | ✅ | ⚠️ Limited |
| JWT tokens | ✅ | ❌ | ❌ |
| Database URIs | ✅ | ❌ | ❌ |
| IP addresses | ✅ | ✅ | ❌ |
| Private keys | ✅ | ❌ | ❌ |
| Reversible sanitization | ✅ (`restore()`) | ✅ (Deanonymize) | ❌ |
| Zero deps | ✅ | ❌ (presidio, spaCy) | ❌ |

ClawGuard's PII sanitizer is **regex-based** (fast, zero deps) vs. LLM Guard's **NER-model-based** (more accurate for edge cases, but requires torch). Trade-off: speed + portability vs. ML accuracy.

---

## 4. Gap Analysis

### 4.1 What ClawGuard Is Missing

| Priority | Gap | Impact | Effort |
|:--------:|-----|--------|--------|
| 🔴 **P0** | **Community & stars** — 1 star, no external contributors | Credibility | Marketing |
| 🔴 **P0** | **Documentation site** — no hosted docs (only README) | Adoption | Medium |
| 🟡 **P1** | **LangChain/CrewAI/AutoGen integration** — Python agent frameworks | Ecosystem reach | Medium |
| 🟡 **P1** | **VS Code extension** — inline security warnings | Developer experience | Medium |
| 🟡 **P1** | **Machine learning augmentation** — optional ML-based prompt injection | Detection accuracy | High |
| 🟡 **P1** | **Benchmarks vs. competitors** — detection rate, latency, false positive rate | Credibility | Medium |
| 🟢 **P2** | **Custom rule authoring DSL** — beyond YAML regex rules | Enterprise customization | High |
| 🟢 **P2** | **SOC/SIEM integration** — Splunk, Elastic Security | Enterprise adoption | Medium |
| 🟢 **P2** | **Rule marketplace** — community-contributed rules | Community growth | High |
| 🟢 **P2** | **Docker image** — containerized deployment | DevOps | Low |
| 🟤 **P3** | **Streaming support** — scan token-by-token as LLM streams | Performance | High |
| 🟤 **P3** | **Multi-tenant mode** — SaaS deployment option | Revenue | High |

### 4.2 Technical Gaps

1. **No ML-based detection** — All detection is regex/heuristic. This is a strength (speed, zero deps) AND a weakness (can be evaded by novel attacks). Consider optional ML augmentation.
2. **No canary token system** — Rebuff's canary tokens are clever for detecting prompt leakage. Could be added.
3. **No LLM-based detection layer** — Using an LLM to analyze ambiguous inputs (Rebuff does this). Could be optional.
4. **Limited internationalization** — Prompt injection covers 12 languages, but PII patterns are primarily English/US formats.
5. **No web dashboard persistence** — Dashboard exists but ephemeral.

### 4.3 README Improvement Plan

The current README is **already excellent** (one of the best I've seen for a v1 project). Specific improvements:

| Section | Issue | Fix |
|---------|-------|-----|
| Hero badges | Missing npm downloads badge | Add `[![Downloads](https://img.shields.io/npm/dm/@neuzhou/clawguard)]` |
| Quick Start | Could highlight "zero deps" more | Add "No Python. No ML models. No GPU. Just `npx`." |
| Comparison table | Good but could add garak & PurpleLlama | Add 2 more columns |
| Benchmark | Missing | Add latency benchmark (e.g., "scans 10K tokens in <50ms") |
| Social proof | None | Add "Used by" section (even if internal projects) |
| Why not X? | Missing | FAQ section: "Why not Guardrails AI / LLM Guard?" |
| Community | Missing contributing guide depth | Add contributor guide, code of conduct |
| Logo | Missing | Add a logo/icon for brand recognition |

---

## 5. Prioritized Action Plan

### Phase 1: Foundation (Week 1-2) — Credibility & Discovery

1. **Add a logo/icon** — Brand recognition in GitHub / npm
2. **Create a documentation site** — Docusaurus/VitePress, deploy to GitHub Pages
3. **Add benchmark numbers** — Scan speed, pattern count, false positive rate
4. **Publish Dev.to article** — "Why AI Agent Security Is Different from LLM Security"
5. **Create comparison blog post** — vs. Guardrails AI, LLM Guard, NeMo (SEO)
6. **Submit to HackerNews** — Show HN: ClawGuard — AI Agent Immune System (after karma threshold)
7. **Add npm download badge + real usage stats**

### Phase 2: Ecosystem (Week 3-4) — Reach Python Developers

8. **LangChain integration package** — `clawguard-langchain` middleware
9. **CrewAI integration** — agent security middleware
10. **Docker image** — `docker run clawguard scan .`
11. **VS Code extension (basic)** — highlight findings inline
12. **GitHub Action in marketplace** — one-click CI integration

### Phase 3: Depth (Month 2) — Technical Moat

13. **Optional ML augmentation** — pluggable ML models for ambiguous cases
14. **Canary token system** — detect prompt leakage
15. **Custom rule DSL** — upgrade from YAML regex to a proper DSL
16. **Streaming scanner** — token-by-token analysis for real-time agents
17. **Benchmark suite vs. competitors** — published, reproducible

### Phase 4: Enterprise (Month 3+) — Revenue

18. **SOC/SIEM integration** — Splunk HEC, Elastic, Datadog
19. **Multi-tenant SaaS mode** — hosted ClawGuard service
20. **Rule marketplace** — community-contributed detection rules
21. **Compliance reports** — GDPR, SOC2, HIPAA audit trail generation

---

## 6. Marketing Positioning

### 6.1 Category: "AI Agent Security"

ClawGuard should **own the "AI Agent Security" category**, distinct from:
- "LLM Safety" (what Guardrails AI / NeMo do)
- "LLM Security Scanning" (what LLM Guard / garak do)
- "Prompt Injection Defense" (what Rebuff does)

**Key message:** *"Everyone else secures the LLM. We secure the agent."*

### 6.2 Taglines

- **Primary:** "AI Agent Immune System — 285+ threat patterns, zero dependencies"
- **Technical:** "The only security framework that protects tools, MCP, identity, memory, and detects when the AI itself goes rogue"
- **Comparison:** "Guardrails AI validates LLM outputs. LLM Guard moderates content. ClawGuard secures the entire agent."
- **Developer:** "npx clawguard scan — no Python, no ML models, no GPU, no API keys"

### 6.3 Target Audiences

| Audience | Pain Point | ClawGuard Message |
|----------|-----------|-------------------|
| **AI agent developers** (OpenClaw, LangChain, CrewAI) | "My agent has shell access, how do I know it's safe?" | Runtime protection for agent tools |
| **Security engineers** | "How do I audit AI agent deployments?" | SARIF + OWASP mapping + policy engine |
| **Enterprise** | "We need compliance for AI agents" | OWASP Agentic AI Top 10, audit trail |
| **Open-source AI projects** | "How do I scan community-contributed skills/tools?" | `npx clawguard scan ./skills/ --strict` |

### 6.4 Competitive Talking Points

**vs. Guardrails AI:** "Guardrails AI validates what the LLM says. ClawGuard secures what the agent does — tool calls, file access, MCP connections, and the agent's own behavior."

**vs. LLM Guard:** "LLM Guard needs Python + PyTorch + GPU to scan text for toxicity. ClawGuard runs anywhere Node.js runs, scans 285+ patterns in milliseconds, and protects the entire agent stack — not just the text."

**vs. NeMo Guardrails:** "NeMo Guardrails steers conversations. ClawGuard secures everything the agent touches — before a single tool call executes."

**vs. garak:** "garak tests if your LLM can be broken. ClawGuard prevents the break from doing damage at runtime."

---

## 7. Summary

### Strengths ✅
- **Unique positioning** — Only tool purpose-built for AI agent security (not LLM safety)
- **Comprehensive coverage** — 285+ patterns across 15 categories including novel categories (MCP, insider threat, memory attacks)
- **Production-quality code** — 684 tests, 0 failures, zero dependencies, TypeScript
- **MCP Firewall** — Category-creating feature, no competitor has anything similar
- **Insider threat detection** — Based on Anthropic research, no competitor covers this
- **Multiple deployment modes** — CLI, npm library, OpenClaw skill, OpenClaw hooks, GitHub Action
- **OWASP Agentic AI Top 10** — Complete mapping (competitors are partial at best)
- **Excellent README** — Professional, comprehensive, good comparison table

### Weaknesses ❌
- **1 star** — Zero community traction yet
- **Solo developer** — Bus factor of 1 vs. backed competitors
- **No documentation site** — README-only docs
- **No ML layer** — Purely heuristic (can be evaded)
- **No Python agent framework integrations** — Missing LangChain/CrewAI/AutoGen
- **No benchmarks published** — Can't prove detection rate claims
- **No logo/brand** — Hurts recognition

### Opportunities 🎯
- **"AI Agent Security" category is unowned** — No competitor is explicitly positioned here
- **Agentic AI explosion** — Every new agent framework needs security
- **OWASP Agentic AI Top 10 is new** — First to fully map wins credibility
- **MCP adoption growing** — MCP Firewall could be standalone product
- **Zero-dep advantage** — Only option for edge/serverless/browser deployment

### Threats ⚠️
- **ProtectAI** could expand LLM Guard + Rebuff into agent security ($60M+ funding)
- **NVIDIA** could add agent security to NeMo Guardrails or garak (massive resources)
- **Guardrails AI** could pivot toward agent security (large community)
- **New entrants** — Agent security is hot, well-funded startups may emerge
- **Solo developer burnout** — 3 projects (ClawGuard + AgentProbe + FinClaw) is a lot

---

*Generated by ClawGuard audit subagent, 2026-03-27*
