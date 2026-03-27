# AgentProbe — Full Competitive Audit & Product Assessment

> Generated: 2026-03-27 | Auditor: 🦀 螃蟹  
> Repo: https://github.com/NeuZhou/agentprobe  
> npm: @neuzhou/agentprobe v0.1.1

---

## 1. Current State Assessment

### Codebase Snapshot

| Metric | Value |
|--------|-------|
| Version (npm) | 0.1.1 |
| Language | TypeScript |
| Source .ts files | 206 |
| Test .ts files | 98 |
| Source lines of code | ~47,000 |
| Test lines of code | ~29,100 |
| Total tests | **2,907** (all passing) |
| Dependencies | 4 (chalk, commander, glob, yaml) |
| Peer deps | @neuzhou/clawguard (optional) |
| npm weekly downloads | 20 |
| GitHub stars | 1 |
| GitHub forks | 0 |
| Open issues | 4 |
| Created | 2026-03-16 (11 days old) |
| Last push | 2026-03-21 |

### What's Working
- ✅ `npm install` — clean, no warnings
- ✅ `npm test` — **2,907 tests pass in 21.6s**, zero failures
- ✅ Clean build with `tsc`
- ✅ Published on npm, installable globally
- ✅ 19 documentation files in `docs/`
- ✅ Rich examples directory (30+ YAML test files across 10+ categories)
- ✅ Comprehensive CLI (run, record, security, compliance, contract, profile, codegen, diff, init, doctor, watch, portal)
- ✅ 9 LLM adapters (OpenAI, Anthropic, Gemini, LangChain, Ollama, HTTP, OpenClaw, A2A, OpenAI-compatible)
- ✅ 17+ assertion types
- ✅ VS Code extension scaffolded (in `src/vscode/`)
- ✅ GitHub Actions integration (`src/github-action/`)
- ✅ MCP server support
- ✅ OpenTelemetry export

### What's Concerning
- ⚠️ 1 star, 0 forks — no external adoption yet
- ⚠️ 20 npm downloads/week (likely all from dev/CI)
- ⚠️ Last push was 6 days ago (momentum pause)
- ⚠️ No GIF/video demo in README
- ⚠️ No "real" end-to-end example (all mocked)
- ⚠️ package.json says `0.1.1` but CHANGELOG says `1.0.0` — version mismatch
- ⚠️ README comparison table may overstate capabilities vs battle-tested competitors
- ⚠️ Massive feature surface for a v0.1 project — may look aspirational to skeptics

---

## 2. Competitive Landscape

### Tier 1: Established Players

#### Promptfoo
| Metric | Value |
|--------|-------|
| Stars | **18,616** |
| Forks | 1,594 |
| npm weekly downloads | **157,401** |
| Language | TypeScript |
| Status | Acquired by OpenAI (rumored) |
| Fortune 500 customers | 127 |
| Community | ~300K developers |

**What it does:** Prompt evaluation + red teaming. YAML-based test configs. Compare model outputs side-by-side. Red team with 50+ vulnerability types. CI/CD integration. Used by OpenAI and Anthropic internally.

**What it does well:**
- Best red-teaming/security scanning in the space
- Enterprise-grade (SOC2, on-prem)
- YAML configs (similar to agentprobe)
- Massive community generating real-time threat intel
- Beautiful web UI for comparing eval results

**What it does NOT do (agentprobe's opportunity):**
- ❌ No tool call assertions (can't verify which tools an agent called)
- ❌ No tool mocking or fault injection
- ❌ No chaos testing
- ❌ No multi-agent orchestration testing
- ❌ No contract testing
- ❌ No trace record & replay
- ❌ Prompt-centric, not agent-centric

**Pricing:** Open source core. Enterprise plan (custom pricing) with cloud dashboard.

---

#### DeepEval
| Metric | Value |
|--------|-------|
| Stars | **14,309** |
| Forks | 1,307 |
| Language | Python |
| Platform | Confident AI (cloud) |

**What it does:** LLM evaluation framework. "Like Pytest but for LLMs." G-Eval, hallucination detection, answer relevancy, task completion metrics. LLM-as-judge patterns.

**What it does well:**
- Best LLM output quality metrics (G-Eval, faithfulness, contextual relevancy)
- Pytest-style familiarity for Python devs
- Great for RAG pipeline evaluation
- Confident AI cloud platform for team collaboration

**What it does NOT do (agentprobe's opportunity):**
- ❌ Python only — no TypeScript API
- ❌ No tool call assertions
- ❌ No tool mocking or fault injection
- ❌ No chaos testing
- ❌ No multi-agent testing
- ❌ No YAML test definitions
- ❌ No contract testing
- ❌ Evaluates LLM *outputs*, not agent *behaviors*

**Pricing:** Open source. Confident AI cloud platform (freemium + paid tiers).

---

#### Arize Phoenix
| Metric | Value |
|--------|-------|
| Stars | **9,058** |
| Forks | 776 |
| Language | Python/Jupyter |

**What it does:** AI observability platform. OpenTelemetry-based tracing, evaluation, datasets, experiments. Visual playground for prompt optimization.

**What it does NOT do:**
- ❌ No behavioral testing framework
- ❌ No tool call assertions
- ❌ No chaos or fault injection
- ❌ Observability-first, not testing-first

**Pricing:** Open source. Arize cloud for enterprise.

---

#### AgentOps
| Metric | Value |
|--------|-------|
| Stars | **5,406** |
| Forks | 552 |
| Language | Python |

**What it does:** Agent monitoring/observability. Cost tracking across 400+ LLMs. Time-travel debugging. Session replay. Integrates with CrewAI, Autogen, LangChain.

**What it does NOT do:**
- ❌ Not a testing framework — it's monitoring
- ❌ No YAML test definitions
- ❌ No assertions or pass/fail results
- ❌ No tool mocking or fault injection
- ❌ No chaos testing

**Pricing:** Free (5K events/mo), Pro ($40/mo), Enterprise (custom).

---

#### LangSmith
| Metric | Value |
|--------|-------|
| Stars | N/A (closed-source platform) |
| Company | LangChain Inc. |
| Funding | $35M Series A |

**What it does:** Full platform for developing, debugging, deploying AI agents. Tracing, evaluation, prompt engineering, deployment. Framework-agnostic (despite LangChain branding).

**What it does NOT do:**
- ❌ Not open source (lock-in risk)
- ❌ No YAML behavioral test definitions
- ❌ No chaos/fault injection
- ❌ No standalone CLI tool
- ❌ No tool call assertions in the agentprobe sense

**Pricing:** Free tier, Plus ($39/seat/mo), Enterprise (custom).

---

#### Braintrust
| Metric | Value |
|--------|-------|
| Stars | N/A (primarily SaaS) |
| Focus | AI observability + evals |

**What it does:** Traces, evals with LLMs/code/humans, CI integration, production monitoring. Custom database (Brainstore) for AI traces. SOC2, GDPR, HIPAA.

**What it does NOT do:**
- ❌ Not a behavioral testing framework
- ❌ No tool mocking or fault injection
- ❌ No chaos testing

**Pricing:** SaaS platform (freemium).

---

### Competitive Map Summary

| Capability | AgentProbe | Promptfoo | DeepEval | AgentOps | LangSmith | Phoenix |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|
| **Tool call assertions** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Tool mocking** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Fault/chaos injection** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Multi-agent orchestration testing** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Contract testing** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Trace record & replay** | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **YAML test definitions** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Security scanning** | ✅ | ✅✅ | ⚠️ | ⚠️ | ❌ | ❌ |
| **LLM-as-Judge** | ✅ | ✅ | ✅✅ | ❌ | ✅ | ✅ |
| **LLM output quality metrics** | ⚠️ | ✅ | ✅✅ | ❌ | ✅ | ✅ |
| **Observability/monitoring** | ⚠️ | ⚠️ | ⚠️ | ✅✅ | ✅✅ | ✅✅ |
| **Enterprise/cloud platform** | ❌ | ✅✅ | ✅ | ✅ | ✅✅ | ✅ |
| **Community size** | 1 | 300K+ | 14K+ | 5K+ | Huge | 9K+ |

---

## 3. AgentProbe's Unique Positioning

### What AgentProbe Does That NO Competitor Does

1. **Tool Call Assertions** — Assert which tools were called, with what parameters, in what order, and which tools were NOT called. No competitor tests this.

2. **Tool Mocking + Fault Injection** — Mock external tool responses and inject faults (timeouts, malformed data, rate limits) to test agent resilience. This is Playwright-level infrastructure.

3. **Chaos Testing for Agents** — Systematically stress-test agent behavior under adverse conditions. Nobody else does this.

4. **Contract Testing** — Define and enforce behavioral invariants ("MUST call authenticate before booking"). This is a new category.

5. **Multi-Agent Orchestration Testing** — Test agent-to-agent handoffs, sequences, and coordination. As multi-agent systems become standard, this is a massive gap elsewhere.

### Is "Playwright for AI Agents" Accurate?

**Yes, with caveats.** After reading the code:

- ✅ Like Playwright: declarative test definitions, assertion engine, trace recording, replay, mocking, fault injection, CI/CD integration, multi-browser ≈ multi-adapter
- ✅ Like Playwright: focuses on *behavior* not just *output*
- ⚠️ Unlike Playwright: no interactive recorder (record by running, not by clicking)
- ⚠️ Unlike Playwright: no visual debugging UI (yet — portal command exists)
- ⚠️ Unlike Playwright: Playwright had Microsoft backing from day 1

The analogy is strong and accurate for the *concept*. The execution needs to match.

### One-Sentence Pitch

> **"The first testing framework purpose-built for AI agents — test tool calls, mock failures, inject chaos, and enforce behavioral contracts, all from YAML."**

Alternative (punchier):
> **"Promptfoo tests your prompts. DeepEval scores your outputs. AgentProbe tests your agent's *behavior* — what it calls, how it fails, and whether it follows the rules."**

---

## 4. Gap Analysis

### Missing Features Users Would Expect

| Gap | Impact | Difficulty |
|-----|--------|-----------|
| **Interactive playground / web UI** | High — competitors all have one | High |
| **Real end-to-end example** (with actual API key) | Critical — proves it works | Low |
| **Python SDK** | High — 60%+ of AI devs use Python | High |
| **Cloud platform / dashboard** | High — for team collaboration | Very High |
| **Video demo / GIF** | Critical — README conversion | Low |
| **Benchmarks** (vs promptfoo speed) | Medium — credibility proof | Medium |
| **Plugin ecosystem** | Medium — extensibility story | Medium |
| **Integration guides** (LangChain, CrewAI, AutoGen) | High — adoption paths | Medium |

### README Assessment

**Strengths:**
- Excellent structure — problem → solution → quick start → features → comparison
- Comparison table is powerful differentiator
- Terminal output preview is a nice touch
- Good feature coverage with code examples
- NeuZhou ecosystem section ties projects together

**Weaknesses:**
- 📌 No GIF/video — readers decide in 5 seconds, and they need to SEE it working
- 📌 Too long — could split into a more concise README + docs link
- 📌 Comparison table may seem biased (every ✅ for us, ❌ for them)
- 📌 No social proof (no testimonials, no "who uses this")
- 📌 No "Why not just use Promptfoo?" section (address the elephant)
- 📌 Quick start requires an API key but doesn't say so — the mock example should be first
- 📌 The `1.0.0` in CHANGELOG vs `0.1.1` in package.json is confusing

### Install Experience

- ✅ `npm install @neuzhou/agentprobe` works cleanly
- ✅ Zero-dependency in production (just chalk/commander/glob/yaml)
- ⚠️ `npx agentprobe run examples/quickstart/test-mock.yaml` — does this actually work without an API key? README says "no API key required" but the YAML references an adapter
- ⚠️ No `npx create-agentprobe` scaffolding command

### Documentation Assessment

- ✅ 19 docs covering most features
- ⚠️ No searchable doc site (just markdown files)
- ⚠️ No API reference generated from TypeScript (TSDoc → site)
- ⚠️ Tutorial/walkthrough style is missing — just reference docs

---

## 5. Prioritized Action Items

### 🔴 P0: Critical (This Week)

1. **Record a 30-second terminal GIF** showing `agentprobe run` with colorized output
   - Use `asciinema` or `terminalizer`
   - Embed at top of README, right after the badges
   - This alone could 5x conversion from page views to stars

2. **Fix version mismatch** — CHANGELOG says 1.0.0, package.json says 0.1.1
   - Decide: is this 0.x (pre-release) or 1.x (stable)?
   - Recommendation: stay at 0.x, update CHANGELOG

3. **Create a working zero-API-key example**
   - The quickstart mock example must run without ANY env vars
   - `npx @neuzhou/agentprobe run examples/quickstart/test-mock.yaml` → instant pass/fail output
   - This is the "playground" moment

4. **Write the "Why AgentProbe, Not Promptfoo?" FAQ entry**
   - Address the elephant directly
   - Position: "Promptfoo tests prompts. AgentProbe tests agents. Use both."
   - Link from README comparison section

5. **Push code to GitHub** — last push was 6 days ago, momentum matters

### 🟡 P1: High Priority (Next 2 Weeks)

6. **Dev.to launch post**: "I Built Playwright for AI Agents — Here's Why Promptfoo Isn't Enough"
   - Include the comparison table
   - Include the terminal GIF
   - Cross-post to HackerNews when karma is sufficient

7. **Shorten README to ~60% current length**
   - Move detailed feature docs to `docs/` and link
   - Keep: problem, quick start, GIF, comparison table, ecosystem
   - Remove: full YAML examples for every feature (link to examples/ instead)

8. **Create `agentprobe init` interactive scaffolder**
   - Like `npm init` or `vitest init`
   - Ask: adapter, model, first test name
   - Generate: `.agentprobe.yml`, first test file, gitignore entry

9. **Add a "Real World" example**
   - A simple OpenAI function-calling agent
   - Test it with agentprobe
   - Show: tool call assertions, fault injection, security scan
   - This proves the framework works end-to-end

10. **Social proof campaign**
    - Ask 5-10 AI developer friends/colleagues to try it and star if they like it
    - Get to 10+ stars (removes "zero traction" signal)

### 🟢 P2: Important (Next Month)

11. **Publish a VS Code extension** (scaffolded in `src/vscode/`)
    - YAML autocomplete for `.test.yaml` files
    - Inline test results
    - This is a major DX differentiator

12. **Create a documentation site** (Docusaurus/VitePress)
    - Search, sidebar, code tabs
    - Auto-generated API reference from TSDoc
    - Deploy to agentprobe.dev or similar

13. **Integration guides for top frameworks**
    - LangChain + agentprobe
    - CrewAI + agentprobe
    - OpenAI Agents SDK + agentprobe
    - Each guide = 1 blog post = 1 SEO page

14. **GitHub Actions Marketplace listing**
    - Publish the action from `src/github-action/`
    - Makes it zero-config for CI

15. **Python SDK** (or at least a Python wrapper)
    - Even a subprocess wrapper that calls the TypeScript CLI
    - Python devs need this

### 🔵 P3: Nice to Have (Quarter)

16. **Web dashboard** — `agentprobe portal` should generate a shareable HTML report
17. **Benchmarks page** — speed vs promptfoo, reliability metrics
18. **Plugin marketplace** (`agentprobe install plugin-name`) 
19. **Cloud platform** (long-term SaaS play if desired)
20. **Conference talk / YouTube video** explaining the "why"

---

## 6. Marketing Positioning Recommendations

### Current: "Playwright for AI Agents"
**Verdict: Keep it.** But supplement with clearer differentiation.

### Recommended positioning stack:

**Tagline:** "Playwright for AI Agents"

**Subtitle:** "Test tool calls. Mock failures. Inject chaos. Enforce contracts. All from YAML."

**Elevator pitch (30s):**
> "Every AI framework lets you build agents. None of them help you test them properly. Promptfoo evaluates prompts. DeepEval scores outputs. But who verifies that your agent called the right tool, with the right parameters, in the right order — and handled failures gracefully? That's AgentProbe. Define behavioral tests in YAML, run them against any LLM, get deterministic pass/fail. Think Playwright, but for AI agents."

### Category creation opportunity:
AgentProbe has the chance to create and own the **"Agent Behavioral Testing"** category. No competitor owns this term. If you establish it in blog posts, docs, and SEO, you become the default answer when people search for it.

Target SEO keywords:
- "agent behavioral testing"
- "test AI agent tool calls"
- "AI agent chaos testing"
- "AI agent contract testing"
- "test multi-agent systems"

---

## 7. Honest Assessment

### Strengths
- **Genuine technical differentiation** — tool call assertions, chaos testing, and contract testing are real gaps in the market
- **Excellent code quality** — 2,907 tests, clean TypeScript, minimal dependencies
- **Comprehensive feature set** — almost too comprehensive for a v0.1
- **Good README structure** — professional, well-organized
- **Smart ecosystem play** — ClawGuard integration creates a moat

### Risks
- **"Feature-complete but community-empty" trap** — projects with tons of code but zero users struggle to build trust
- **Promptfoo + OpenAI acquisition** — if OpenAI integrates promptfoo deeply, the "eval" space gets very crowded
- **Solo developer risk** — all commits from one person
- **Aspiration vs reality gap** — README advertises 17+ assertion types and 9 adapters, but without real-world usage proof, skeptics will doubt
- **TypeScript-only** — excludes the majority of AI developers (Python-first)

### Bottom Line

AgentProbe has a **real, defensible technical position** in a gap that no major player fills. The "agent behavioral testing" niche is genuine and growing. But the project needs:

1. **Proof it works** (GIF, real example, early adopters)
2. **Distribution** (blog posts, HN, dev.to, SEO)
3. **Social proof** (stars, downloads, testimonials)

The code is ready. The marketing isn't. That's the #1 priority.

---

*End of audit. Updated 2026-03-27.*
