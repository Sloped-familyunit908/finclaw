# Feature Gap Analysis: AgentProbe & ClawGuard

**Date:** 2026-03-27
**Author:** 螃蟹 (automated research)
**Purpose:** Identify feature gaps vs. top competitors, prioritize roadmap items before promotion push

---

## Table of Contents

1. [Task 1: AgentProbe Feature Gap Analysis](#task-1-agentprobe-feature-gap-analysis)
2. [Task 2: ClawGuard Feature Gap Analysis](#task-2-clawguard-feature-gap-analysis)
3. [Task 3: Ecosystem Gaps](#task-3-ecosystem-gaps)
4. [Task 4: Priority Feature Roadmap](#task-4-priority-feature-roadmap)

---

## Task 1: AgentProbe Feature Gap Analysis

### Competitor Overview

| Tool | Stars | Language | Focus | Key Differentiator |
|------|-------|----------|-------|-------------------|
| **Promptfoo** | 18.6K | TypeScript | Prompt eval + red teaming | Acquired by OpenAI, CI/CD-first, YAML configs |
| **DeepEval** | 14.3K | Python | LLM evaluation framework | 50+ metrics, Pytest-like, G-Eval research-backed |
| **AgentOps** | 5.4K | Python | Agent observability | Session tracking, cost monitoring, replay analytics |
| **Arize Phoenix** | 9K | Python | AI observability + eval | OpenTelemetry-native, tracing, prompt playground |
| **LangSmith** | N/A (SaaS) | Python/TS | Full lifecycle platform | LangChain ecosystem, deployment, Fleet visual builder |

### Feature Comparison Matrix

| Feature | Promptfoo | DeepEval | AgentOps | Arize Phoenix | LangSmith | **AgentProbe** | Gap? |
|---------|-----------|---------|----------|---------------|-----------|---------------|------|
| **LLM-as-Judge evaluation** | ✅ Custom graders | ✅ G-Eval, 50+ metrics | ❌ | ✅ Pre-built + custom | ✅ Custom evaluators | ✅ `llm_judge` assertion | ✅ Parity |
| **Cost tracking per test** | ⚠️ Basic | ❌ | ✅ Per-session, per-agent | ⚠️ Via tracing | ✅ Detailed | ✅ `cost_usd` assertion | ✅ Parity |
| **Latency benchmarking** | ⚠️ Implicit via timing | ⚠️ Basic | ✅ Session timing | ✅ Span-level latency | ✅ P50/P99 latency | ✅ `latency_ms` assertion | ✅ Parity |
| **A/B testing of agent versions** | ✅ Multi-prompt matrix | ✅ Via test datasets | ❌ | ✅ Experiments (compare versions) | ✅ Experiments + datasets | ❌ No built-in A/B | ❌ **GAP** |
| **Regression detection** | ✅ CI quality gates | ✅ Via Confident AI cloud | ❌ | ✅ Experiments comparison | ✅ Annotation queues | ⚠️ Manual via CI diff | ❌ **GAP** |
| **CI/CD integration** | ✅ GitHub Action, GitLab, Jenkins, Azure, CircleCI, Bitbucket, Travis | ✅ Pytest integration | ❌ | ⚠️ Manual setup | ⚠️ Manual setup | ✅ JUnit, GH Actions, GitLab | ✅ Parity |
| **Dashboard/UI for results** | ✅ Web viewer + shareable | ✅ Confident AI cloud platform | ✅ Full dashboard | ✅ Phoenix UI (local + cloud) | ✅ Full SaaS platform | ❌ CLI only, no dashboard | ❌ **GAP** |
| **OpenTelemetry integration** | ❌ | ❌ | ❌ | ✅ Native OTel (OTLP) | ⚠️ Custom tracing format | ❌ | ❌ **GAP** |
| **Multi-model comparison** | ✅ Side-by-side matrix view | ✅ Via multiple test runs | ❌ | ✅ Prompt playground | ✅ Prompt playground | ⚠️ Via adapter swap, no matrix view | ❌ **GAP** |
| **Red teaming / security scanning** | ✅ Full red team suite, OWASP | ✅ Toxicity, bias | ❌ | ❌ | ❌ | ✅ PII, injection, system leak (via ClawGuard) | ✅ Parity |
| **Synthetic data generation** | ❌ | ✅ Evolution-based dataset gen | ❌ | ❌ | ✅ Via datasets | ❌ | ❌ **GAP** |
| **RAG-specific evaluation** | ✅ Context-based metrics | ✅ Faithfulness, relevancy, recall, precision, RAGAS | ❌ | ✅ Context retrieval analysis | ✅ Retrieval evaluators | ❌ No RAG-specific metrics | ❌ **GAP** |
| **Agent-specific metrics** | ⚠️ Prompt-focused | ✅ Task Completion, Tool Correctness, Step Efficiency, Plan Quality | ❌ | ⚠️ Via custom evals | ⚠️ Via custom evals | ✅ Tool assertions, contracts, chaos | ✅ **Strength** |
| **Multi-agent testing** | ❌ | ❌ | ✅ Multi-agent visualization | ⚠️ Via tracing | ⚠️ Via tracing | ✅ Orchestration testing | ✅ **Strength** |
| **Chaos/fault injection** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Full chaos testing | ✅ **Unique** |
| **Tool call assertions** | ❌ | ✅ Tool Correctness metric | ❌ | ❌ | ❌ | ✅ 6 assertion types | ✅ **Strength** |
| **Behavioral contracts** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Built-in | ✅ **Unique** |
| **Trace record & replay** | ❌ | ❌ | ✅ Time Travel Debugging | ✅ Span replay | ✅ Replay | ✅ Record/codegen/replay | ✅ Parity |
| **Prompt management/versioning** | ⚠️ Via YAML configs | ❌ | ❌ | ✅ Prompt Management | ✅ Full versioning | ❌ | ❌ **GAP** |
| **MCP-specific evaluation** | ❌ | ✅ MCP Task Completion, MCP Use | ❌ | ❌ | ❌ | ⚠️ Via tool assertions | ⚠️ Minor gap |
| **Multimodal evaluation** | ⚠️ Basic | ✅ Text-to-Image, Image Editing, Coherence | ❌ | ⚠️ Basic | ⚠️ Basic | ❌ | ❌ **GAP** |
| **Human annotation/feedback** | ⚠️ Share for review | ✅ Via Confident AI | ❌ | ✅ In-UI annotations | ✅ Annotation queues | ❌ | ❌ **GAP** |
| **Code scanning (static analysis)** | ✅ PR-level code scanning | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ **GAP** |
| **Hallucination detection** | ⚠️ Via graders | ✅ Dedicated metric | ❌ | ✅ Via evaluators | ✅ Via evaluators | ✅ `no_hallucination` assertion | ✅ Parity |
| **Python SDK** | ✅ pip install | ✅ Native Python | ✅ Python | ✅ Python | ✅ Python + TS | ❌ TypeScript only | ❌ **GAP** |
| **Structured output validation** | ✅ JSON schema | ✅ JSON Correctness | ❌ | ❌ | ❌ | ✅ `json_schema` assertion | ✅ Parity |

### AgentProbe Strengths (Unique Selling Points)

1. **Chaos/Fault Injection** — No competitor offers this. Unique differentiator.
2. **Behavioral Contracts** — Invariant enforcement across agent versions. Novel concept.
3. **Tool Call Assertions (6 types)** — Deepest tool behavior testing in the market.
4. **Multi-agent Orchestration Testing** — Purpose-built for testing agent handoffs.
5. **YAML + TypeScript dual API** — Both declarative and programmatic.
6. **Zero-config start** — `npx agentprobe run` works without API keys (mock adapters).

### AgentProbe Critical Gaps

1. **No Dashboard/UI** — Every major competitor has one. #1 blocker for team adoption.
2. **No A/B testing / experiments** — Can't compare agent versions side-by-side.
3. **No Python SDK** — All 4 major competitors are Python-first. Blocks ML/AI teams.
4. **No regression detection** — No automatic "this version is worse than last" alerts.
5. **No RAG-specific metrics** — Missing faithfulness, relevancy, recall metrics.
6. **No OpenTelemetry integration** — Can't plug into existing observability stacks.
7. **No synthetic data generation** — Can't auto-generate test cases.

---

## Task 2: ClawGuard Feature Gap Analysis

### Competitor Overview

| Tool | Stars | Language | Focus | Key Differentiator |
|------|-------|----------|-------|-------------------|
| **Guardrails AI** | 6.5K | Python | LLM I/O validation | Hub marketplace (100+ validators), structured output, SnowGlobe synthetic data |
| **NeMo Guardrails** | 5.9K | Python | Conversational rails | NVIDIA-backed, Colang DSL, dialog flow control, 5 rail types |
| **garak** | 7.4K | Python | LLM vulnerability scanning | NVIDIA, nmap-style scanning, extensive probe library |
| **LLM Guard** | 2.7K | Python | Security toolkit | ProtectAI ($60M+), 30+ scanners, input/output separation |
| **ProtectAI** | N/A (SaaS) | Python | Enterprise AI security | $60M+ funding, commercial platform, enterprise compliance |

### Feature Comparison Matrix

| Feature | Guardrails AI | NeMo Guardrails | garak | LLM Guard | **ClawGuard** | Gap? |
|---------|--------------|-----------------|-------|-----------|--------------|------|
| **Runtime protection (real-time)** | ✅ Guard wrapper | ✅ LLMRails async | ❌ Scan-only | ✅ Scanner pipeline | ✅ Scan + MCP Firewall | ✅ Parity |
| **Static scanning** | ❌ | ❌ | ✅ CLI scanner | ⚠️ Basic | ✅ CLI scanner | ✅ Parity |
| **Prompt injection detection** | ✅ Via validators | ✅ Via rails | ✅ Probes | ✅ PromptInjection scanner | ✅ 93 patterns, 13 categories | ✅ **Strength** |
| **PII detection/sanitization** | ⚠️ Plugin-based | ❌ | ❌ | ✅ Anonymize/Deanonymize | ✅ Built-in, reversible | ✅ Parity |
| **Benchmark suites (standard attack datasets)** | ✅ Guardrails Index (24 guardrails, 6 categories) | ⚠️ LLM vulnerability scan results | ✅ Standard probes (DAN, encoding, etc.) | ❌ | ❌ No standard benchmark suite | ❌ **GAP** |
| **Integration: LangChain** | ✅ Native | ✅ LangChain chains support | ❌ | ⚠️ Via API | ❌ | ❌ **GAP** |
| **Integration: CrewAI** | ⚠️ Community | ❌ | ❌ | ❌ | ❌ | ❌ **GAP** |
| **Integration: AutoGen** | ⚠️ Community | ❌ | ❌ | ❌ | ❌ | ❌ **GAP** |
| **Compliance reporting (SOC2, HIPAA)** | ❌ | ❌ | ❌ | ❌ (ProtectAI SaaS only) | ⚠️ Compliance patterns exist (GDPR, SOC2, HIPAA, PCI-DSS) but no formal reports | ❌ **GAP** |
| **Rate limiting / throttling** | ❌ | ❌ | ❌ | ✅ TokenLimit scanner | ❌ No rate limiter | ❌ **GAP** |
| **Custom rule creation UI** | ✅ Hub with community validators | ✅ Colang DSL | ❌ CLI only | ❌ Code only | ❌ Code/YAML only | ❌ **GAP** |
| **Logging/audit trail** | ⚠️ Basic | ⚠️ Basic | ✅ JSONL logs | ⚠️ Basic | ✅ SARIF, JSONL, Syslog/CEF, Webhook | ✅ **Strength** |
| **Multi-language support (Python SDK)** | ✅ Python native | ✅ Python native | ✅ Python native | ✅ Python native | ❌ TypeScript only | ❌ **GAP** |
| **Validator/Rule marketplace** | ✅ Guardrails Hub (100+ validators) | ❌ | ❌ | ❌ | ❌ | ❌ **GAP** |
| **Dialog flow control** | ❌ | ✅ Colang 2.0, 5 rail types | ❌ | ❌ | ❌ Not applicable (different focus) | N/A |
| **Tool call governance** | ❌ | ❌ | ❌ | ❌ | ✅ Policy engine | ✅ **Unique** |
| **MCP Firewall** | ❌ | ❌ | ❌ | ❌ | ✅ Real-time proxy | ✅ **Unique** |
| **Insider threat / misalignment** | ❌ | ❌ | ❌ | ❌ | ✅ 39 patterns | ✅ **Unique** |
| **Supply chain scanning** | ❌ | ❌ | ❌ | ❌ | ✅ 35 patterns | ✅ **Unique** |
| **Memory/RAG poisoning detection** | ❌ | ❌ | ❌ | ❌ | ✅ 38 patterns | ✅ **Unique** |
| **Cross-agent contamination** | ❌ | ❌ | ❌ | ❌ | ✅ Detection | ✅ **Unique** |
| **Risk scoring + attack chains** | ❌ | ❌ | ⚠️ Pass/fail per probe | ❌ | ✅ Weighted scoring + multipliers | ✅ **Strength** |
| **Structured output validation** | ✅ Pydantic, JSON Schema | ❌ | ❌ | ✅ JSON scanner | ❌ Not focus area | N/A |
| **Toxicity detection** | ✅ ToxicLanguage validator | ❌ | ✅ Toxicity probes | ✅ Toxicity scanner | ⚠️ Via patterns, no ML model | ⚠️ Minor gap |
| **Bias detection** | ❌ | ❌ | ✅ Bias probes | ✅ Bias scanner | ❌ | ❌ **GAP** |
| **Hallucination detection** | ⚠️ Via validators | ✅ Fact-checking rails | ✅ Hallucination probes | ✅ FactualConsistency | ❌ Not focus area | N/A |
| **Code execution sandboxing** | ❌ | ❌ | ❌ | ✅ BanCode scanner | ⚠️ Pattern-based detection | ⚠️ Minor gap |
| **Sensitive data masking** | ⚠️ Via validators | ❌ | ❌ | ✅ Anonymize + Deanonymize | ✅ PII Sanitizer (reversible) | ✅ Parity |
| **REST API / Server mode** | ✅ Flask server | ✅ Guardrails server | ❌ CLI only | ✅ API deployment | ❌ Library + CLI only | ❌ **GAP** |
| **Zero dependencies** | ❌ Heavy Python | ❌ Heavy Python + C++ | ❌ Heavy Python + ML | ❌ Heavy Python | ✅ Zero deps, pure TS | ✅ **Strength** |
| **YARA rules engine** | ❌ | ❌ | ❌ | ❌ | ✅ Built-in | ✅ **Unique** |

### ClawGuard Strengths (Unique Selling Points)

1. **Agent-layer security** — Only tool focused on the agent execution surface (not just LLM I/O).
2. **MCP Firewall** — No competitor has this. First-mover advantage in MCP security.
3. **Insider threat detection** — 39 patterns for agentic misalignment. Unique.
4. **Supply chain scanning** — 35 patterns. No competitor covers this.
5. **Memory/RAG poisoning** — 38 patterns. Novel attack surface coverage.
6. **Zero dependencies** — Pure TypeScript, no ML models needed. Easy deployment.
7. **SARIF + CI integration** — GitHub Code Scanning compatible.
8. **Risk scoring with attack chain detection** — Composite scoring with multipliers.
9. **285+ threat patterns** — Largest agent-specific pattern library.
10. **YARA engine** — Custom rule authoring for advanced users.

### ClawGuard Critical Gaps

1. **No Python SDK** — All 4 major competitors are Python. Blocks Python AI ecosystem adoption.
2. **No standard benchmark suite** — Can't demonstrate coverage against known attack datasets (like garak).
3. **No LangChain/CrewAI/AutoGen integration** — Missing the most popular agent frameworks.
4. **No compliance report generation** — Has compliance patterns but no formatted SOC2/HIPAA/GDPR reports.
5. **No rate limiting / throttling** — Basic feature that LLM Guard has.
6. **No rule/validator marketplace** — Guardrails AI Hub is a massive adoption driver.
7. **No REST API / server mode** — Can't deploy as a standalone security service.
8. **No bias detection** — Both garak and LLM Guard have this.

---

## Task 3: Ecosystem Gaps

### AgentProbe Ecosystem Gaps

#### Missing Integrations
| Integration | Priority | Reason |
|-------------|----------|--------|
| **Python SDK** | 🔴 Critical | Python dominates ML/AI. No Python = no adoption from AI engineers |
| **LangChain adapter** | 🔴 Critical | Most popular agent framework. Already have LangChain adapter but need deeper integration |
| **CrewAI adapter** | 🟡 High | Fast-growing multi-agent framework |
| **AutoGen adapter** | 🟡 High | Microsoft-backed, enterprise traction |
| **Vercel AI SDK** | 🟡 High | Growing TS ecosystem player |
| **OpenTelemetry exporter** | 🟡 High | Standard observability protocol |
| **Pydantic AI adapter** | 🟢 Medium | Growing Python agent framework |
| **Mastra adapter** | 🟢 Medium | TypeScript agent framework |

#### Missing Plugins/Extensions
- **VS Code Extension** — Inline test results, test discovery in sidebar
- **GitHub App** — Auto-comment on PRs with test results (like Promptfoo's action)
- **Slack/Discord bot** — Post test results on merge
- **Grafana dashboard** — For teams using Grafana for monitoring

#### Missing Documentation
- **Migration guide from Promptfoo** — Show "you already use Promptfoo? Here's how to switch"
- **Migration guide from DeepEval** — Same for Python teams
- **Cookbook: Testing LangChain agents** — Step-by-step guide with real examples
- **Cookbook: Testing CrewAI multi-agent systems** — Multi-agent is our strength, show it
- **Cookbook: Testing MCP servers** — MCP is hot, capitalize on it
- **Cookbook: CI/CD pipeline setup** — End-to-end from code to deploy
- **Architecture decision records** — Why AgentProbe exists (vs using Promptfoo + custom scripts)
- **Performance benchmarks** — How fast is AgentProbe vs. Promptfoo?

#### Examples That Would Attract Users
1. **"Test your OpenAI Swarm agent in 5 minutes"** — Swarm is trending
2. **"Chaos test a customer support agent"** — Relatable use case
3. **"Replace Promptfoo with AgentProbe for agent testing"** — Direct comparison
4. **"Test a full CrewAI pipeline"** — Multi-agent showcase
5. **"Security scan + behavioral test in one pipeline"** — AgentProbe + ClawGuard integration
6. **"Record a live Claude session and replay it"** — Demos the record/replay feature
7. **"Test MCP tool calls"** — MCP is hot right now

### ClawGuard Ecosystem Gaps

#### Missing Integrations
| Integration | Priority | Reason |
|-------------|----------|--------|
| **Python SDK** | 🔴 Critical | Python AI ecosystem is 10x larger than TS for security |
| **LangChain middleware** | 🔴 Critical | Drop-in security layer for most popular framework |
| **CrewAI plugin** | 🟡 High | Multi-agent security is ClawGuard's story |
| **AutoGen security handler** | 🟡 High | Microsoft enterprise market |
| **OpenAI Swarm wrapper** | 🟡 High | Trending framework |
| **FastAPI middleware** | 🟡 High | Standard Python web framework for AI APIs |
| **Express.js middleware** | 🟢 Medium | Standard Node.js framework |
| **OpenClaw skill** | 🟢 Medium | Natural ecosystem fit |

#### Missing Plugins/Extensions
- **REST API server** — Deploy ClawGuard as a security microservice
- **Docker image** — Ready-to-deploy container
- **Helm chart** — K8s deployment for enterprise
- **Terraform module** — Infrastructure-as-code deployment
- **VS Code Extension** — Real-time security warnings while coding agents

#### Missing Documentation
- **OWASP LLM Top 10 mapping** — Show which patterns cover which OWASP risks
- **Compliance cookbook: SOC2** — Step-by-step compliance setup
- **Compliance cookbook: HIPAA** — Healthcare AI compliance
- **Integration guide: LangChain** — Drop-in security
- **Integration guide: MCP Firewall deployment** — Production setup guide
- **Benchmark results** — ClawGuard vs. garak vs. LLM Guard detection rates
- **Architecture guide** — How to embed ClawGuard in your agent architecture

#### Examples That Would Attract Users
1. **"Secure your LangChain agent in 3 lines"** — Lowest friction adoption
2. **"MCP Firewall: protect your Claude Desktop"** — Viral potential, Claude Desktop is huge
3. **"Detect when your agent goes rogue"** — Insider threat showcase
4. **"SOC2 compliance for AI agents"** — Enterprise buyers need this
5. **"ClawGuard + AgentProbe: security + testing in one pipeline"** — Cross-sell
6. **"Block prompt injection in production"** — Immediate business value
7. **"Supply chain attack detection for AI"** — Novel, PR-worthy

---

## Task 4: Priority Feature Roadmap

### AgentProbe Feature Roadmap

#### P0: Must Have Before Promotion Push

| Feature | Effort | Impact | Notes |
|---------|--------|--------|-------|
| **Basic web dashboard** | 2-3 weeks | 🔴 Critical | HTML report generator at minimum. Interactive results viewer. Every competitor has one. Blocks team adoption. Consider `agentprobe view` (like `promptfoo view`) |
| **A/B testing / experiments** | 1-2 weeks | 🔴 Critical | Compare two agent versions on same dataset. Output a comparison report. Key for "upgrade with confidence" story |
| **Regression detection** | 1 week | 🔴 Critical | Store baseline results, diff against new runs, fail CI if regression. Can build on top of JUnit output |
| **Multi-model comparison view** | 1 week | 🟡 High | Matrix view comparing same test suite across GPT-4, Claude, Gemini. Promptfoo's killer feature |
| **Polish README examples** | 2-3 days | 🟡 High | Add animated GIF/video demo, playground link, "Try it now" section. First impressions matter |
| **Benchmark page** | 1 week | 🟡 High | Performance benchmarks vs Promptfoo/DeepEval. Speed is a selling point for TS |

#### P1: Should Have Within 1 Month

| Feature | Effort | Impact | Notes |
|---------|--------|--------|-------|
| **Python SDK wrapper** | 2-3 weeks | 🔴 Critical | Thin Python wrapper over the TS core (via subprocess or native binding). Unblocks ML teams |
| **RAG evaluation metrics** | 2 weeks | 🟡 High | Faithfulness, relevancy, contextual recall/precision. Port DeepEval's approach |
| **OpenTelemetry exporter** | 1 week | 🟡 High | Export test results as OTel spans. Integrates with Grafana/Datadog |
| **Synthetic test generation** | 2 weeks | 🟡 High | Use LLM to auto-generate test cases from agent description. DeepEval's evolution technique |
| **VS Code extension** | 2 weeks | 🟢 Medium | Test discovery, inline results, click-to-run |
| **GitHub Action v2** | 1 week | 🟢 Medium | Published to GitHub Marketplace. Auto-comment on PRs |

#### P2: Nice to Have Within 3 Months

| Feature | Effort | Impact | Notes |
|---------|--------|--------|-------|
| **Cloud dashboard (SaaS)** | 4-6 weeks | 🟡 High | Confident AI-style. Team collaboration, history, trend charts |
| **Multimodal evaluation** | 2-3 weeks | 🟢 Medium | Image/audio test assertions |
| **Human annotation flow** | 2 weeks | 🟢 Medium | Flag tests for human review, collect feedback |
| **Prompt management** | 2 weeks | 🟢 Medium | Version prompts, compare across versions |
| **MCP-specific metrics** | 1 week | 🟢 Medium | Dedicated MCP evaluation (like DeepEval's MCP metrics) |
| **Code scanning** | 3 weeks | 🟢 Medium | Static analysis of agent code for security issues (like Promptfoo) |
| **CrewAI/AutoGen deep integration** | 2 weeks | 🟢 Medium | Framework-aware test discovery and assertion helpers |
| **Grafana dashboard template** | 1 week | 🟢 Low | Pre-built dashboard for teams using Grafana |

### ClawGuard Feature Roadmap

#### P0: Must Have Before Promotion Push

| Feature | Effort | Impact | Notes |
|---------|--------|--------|-------|
| **Python SDK** | 2-3 weeks | 🔴 Critical | `pip install clawguard`. Thin binding over TS core. Unblocks 90% of AI security market |
| **LangChain middleware** | 1 week | 🔴 Critical | `from clawguard.langchain import ClawGuardMiddleware`. Drop-in security |
| **REST API / server mode** | 1-2 weeks | 🔴 Critical | `clawguard serve --port 8080`. Deploy as security microservice. Every competitor has this |
| **Benchmark suite** | 2 weeks | 🟡 High | Standard attack dataset (like garak's probes). Publish detection rate numbers. Needed for credibility |
| **OWASP LLM Top 10 mapping doc** | 3 days | 🟡 High | Map each ClawGuard category to OWASP LLM Top 10 risks. Enterprise buyers check this |
| **Docker image** | 2-3 days | 🟡 High | `docker run clawguard serve`. Easy deployment |

#### P1: Should Have Within 1 Month

| Feature | Effort | Impact | Notes |
|---------|--------|--------|-------|
| **Compliance report generator** | 2 weeks | 🟡 High | Generate SOC2/HIPAA/GDPR compliance reports from scan results. PDF/HTML output |
| **Rate limiting / throttling** | 1 week | 🟡 High | Token-per-minute, request-per-minute limits. Basic but expected |
| **Bias detection module** | 1-2 weeks | 🟡 High | Gender, racial, political bias detection in agent outputs |
| **CrewAI/AutoGen integration** | 1-2 weeks | 🟡 High | Security middleware for multi-agent frameworks |
| **Rule marketplace (Hub)** | 3-4 weeks | 🟡 High | Community-contributed threat patterns. Like Guardrails Hub |
| **Express.js middleware** | 3 days | 🟢 Medium | `app.use(clawguardMiddleware())` — natural for TS users |

#### P2: Nice to Have Within 3 Months

| Feature | Effort | Impact | Notes |
|---------|--------|--------|-------|
| **Web UI for rule management** | 3-4 weeks | 🟡 High | Visual rule editor, test playground, results viewer |
| **ML-based toxicity detection** | 2-3 weeks | 🟢 Medium | Use small ONNX models for ML-based detection (vs pattern-only) |
| **Helm chart** | 1 week | 🟢 Medium | Kubernetes deployment for enterprise |
| **Terraform module** | 1 week | 🟢 Medium | Infrastructure-as-code |
| **OpenAI Swarm wrapper** | 3-5 days | 🟢 Medium | Security wrapper for trending framework |
| **VS Code Extension** | 2-3 weeks | 🟢 Medium | Real-time security warnings while coding agents |
| **Grafana integration** | 1 week | 🟢 Low | Export security metrics to Grafana dashboards |
| **FastAPI middleware** | 3-5 days | 🟢 Low | Python web framework middleware (after Python SDK) |

---

## Summary: Key Takeaways

### AgentProbe

**Position:** Best-in-class for **agent behavioral testing** (tool calls, chaos, contracts, multi-agent). Clear differentiation from Promptfoo (prompt-focused) and DeepEval (LLM output-focused).

**Biggest risks:**
1. No dashboard = no team adoption = stays a single-developer tool
2. No Python SDK = invisible to 80% of AI developers
3. DeepEval added agent metrics (Task Completion, Tool Correctness) which overlap AgentProbe's niche

**Moat:** Chaos testing + behavioral contracts + multi-agent orchestration testing. No one else has this combination.

### ClawGuard

**Position:** Only **agent-layer security** tool. Clear blue ocean vs. Guardrails AI (LLM I/O), NeMo (conversation rails), garak (model red-teaming), LLM Guard (LLM I/O scanning).

**Biggest risks:**
1. No Python SDK = invisible to the security research community
2. No standard benchmarks = can't prove detection rates vs. competitors
3. No REST API = can't be deployed as a security service in production architectures

**Moat:** MCP Firewall + insider threat detection + supply chain scanning + memory poisoning + cross-agent contamination. Nobody else covers these attack surfaces.

### Cross-Project Synergies

The **AgentProbe + ClawGuard** story is powerful. Position them as:
- **AgentProbe** = "Test your agent does the right thing"
- **ClawGuard** = "Protect your agent from doing the wrong thing"
- Together = Complete agent quality + security pipeline

Priority: Create a combined example/tutorial showing both tools in a single CI/CD pipeline.
