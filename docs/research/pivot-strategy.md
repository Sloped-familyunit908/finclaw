# Pivot Strategy: Maximizing Star Potential Across NeuZhou Repos

*Generated: 2026-03-27 | Research-based analysis*

---

## Executive Summary

**#1 Pick: AgentProbe** — Highest star ceiling, least crowded niche, strongest tailwind.  
**#2 Pick: ClawGuard** — Excellent complementary play, strong niche but more competition.  
**#3 Pick: FinClaw** — Already has traction (19 stars) but faces 48k-star incumbent. Keep but deprioritize.

**Do NOT merge into a super-repo.** Keep separate. Cross-promote heavily.

---

## 1. Competitive Landscape (Live Data, March 2026)

### Trading Bot Space (finclaw's market)

| Repo | Stars | Forks | Notes |
|------|-------|-------|-------|
| freqtrade/freqtrade | **48,083** | 10,019 | Dominant. 7+ years. Massive community |
| NeuZhou/finclaw | 19 | 5 | New. GA evolution angle is unique |

**Other competitors:** Jesse (~5k), FinRL (~10k), Qlib (~16k by Microsoft)

**Verdict:** This space is BRUTALLY competitive. Freqtrade is an 8-year institution with 48k stars. Qlib is backed by Microsoft. Getting to 1k stars here means beating entrenched players with massive teams. finclaw's GA angle is differentiated but not enough to overcome the network effects.

### AI Agent Security Space (clawguard's market)

| Repo | Stars | Forks | Notes |
|------|-------|-------|-------|
| guardrails-ai/guardrails | **6,595** | 558 | LLM I/O validation, not agent-specific |
| protectai/llm-guard | **2,738** | 364 | Content moderation focus |
| always-further/nono | 1,301 | 92 | Kernel-level sandbox (Rust) |
| openguardrails/openguardrails | 321 | 45 | OpenClaw-focused, most downloaded skill |
| ClawSecure/clawsecure | 20 | 1 | OpenClaw scanner |
| NeuZhou/clawguard | 1 | 0 | New |

**15 repos** in the `ai-agent-security` GitHub topic. **90 repos** in `mcp-security`.

**Verdict:** Growing fast but still early. Guardrails AI (6.5k) and LLM Guard (2.7k) focus on LLM I/O — they don't cover agent-level threats (tool call governance, MCP firewall, insider threat). clawguard's differentiation is clear: it's the only one covering the FULL agent attack surface. But openguardrails (321 stars) with its "install and forget" OpenClaw plugin is a direct competitor with first-mover advantage in the OpenClaw ecosystem.

### AI Agent Testing Space (agentprobe's market)

| Repo | Stars | Forks | Notes |
|------|-------|-------|-------|
| promptfoo/promptfoo | **18,616** | 1,594 | Prompt eval + red teaming. Acquired by OpenAI |
| confident-ai/deepeval | **14,309** | 1,307 | LLM eval framework (Python) |
| flakestorm/flakestorm | 39 | 4 | Robustness testing for agents |
| NeuZhou/agentprobe | 1 | 0 | New |

**Only 4 repos** in the `ai-agent-testing` GitHub topic.

**Verdict:** This is THE opportunity. Here's why:

1. **Promptfoo** was just acquired by OpenAI (March 2026) — prompt-focused, not agent-focused
2. **DeepEval** is Python-only, LLM output eval — no tool call testing, no chaos testing
3. **Neither tests actual agent behavior** — tool calls, multi-step workflows, fault injection
4. The entire "agent testing" topic has only **4 repos**
5. 17,922 repos tagged `ai-agents` × 0 proper testing framework = massive gap

---

## 2. Scorecard: Star Ceiling Analysis

| Dimension | FinClaw | ClawGuard | AgentProbe |
|-----------|---------|-----------|------------|
| **TAM (addressable devs)** | ~50k algo traders | ~500k+ agent builders | ~500k+ agent builders |
| **Niche crowding** | 🔴 Very crowded | 🟡 Moderately crowded | 🟢 Almost empty |
| **One-sentence pitch** | 🟡 "GA evolves trading strategies" | 🟢 "Immune system for AI agents" | 🟢 "Playwright for AI agents" |
| **Solves daily problem?** | 🔴 No (occasional use) | 🟡 Yes (but devs ignore security) | 🟢 Yes (every CI run) |
| **Competition moat** | 🔴 Freqtrade 48k | 🟡 Guardrails 6.5k (different scope) | 🟢 No direct competitor |
| **Tailwind (market growth)** | 🟡 Crypto cycles | 🟢 Agent security incidents growing | 🟢 Agent adoption exploding |
| **Viral potential** | 🔴 Niche audience | 🟡 Fear-driven sharing | 🟢 "Playwright for X" is proven meme |
| **Star ceiling estimate** | 500-2k | 2k-8k | 5k-20k |

### Why AgentProbe Has the Highest Ceiling

1. **"Playwright for AI Agents"** — This is a category-defining phrase. Playwright has 70k+ stars. Everyone knows what it means. When someone says "Playwright for X," developers instantly understand the value proposition.

2. **No incumbent.** Promptfoo tests prompts. DeepEval evaluates outputs. Nobody tests agent *behavior* — tool calls, multi-step workflows, fault injection, chaos testing. AgentProbe is the ONLY one.

3. **CI/CD integration = daily use.** Unlike security tools (which devs often skip), testing tools get built into CI pipelines. Every PR triggers tests. That's daily value.

4. **YAML test definitions.** Low barrier to entry. Developers can write a test in 30 seconds. Promptfoo proved this format works (18k stars).

5. **The timing is perfect.** 2026 is the year of AI agents. 17,922 repos tagged `ai-agents`. All of them need testing. None of them have a testing framework.

---

## 3. Cross-Pollination Strategy

### DO NOT merge into a super-repo

**Why not:**
- Different audiences (quant traders ≠ agent security ≠ agent testing)
- Different languages (Python vs TypeScript)
- Monorepos get fewer stars (people star what they USE, not what's impressive)
- Harder to rank in GitHub search/topics

### DO cross-promote heavily

```
agentprobe ←→ clawguard (natural pairing)
     ↑
  finclaw (agent example / use case)
```

**Specific integrations:**
1. **AgentProbe + ClawGuard:** Already exists! AgentProbe has ClawGuard integration for security scanning in tests. This is the killer combo — "test AND secure your agents."
2. **FinClaw as showcase:** Use finclaw's MCP server as a real-world example in AgentProbe's docs. "Here's how to test a real financial AI agent."

---

## 4. The Umbrella Brand Question

### Don't create a parent project

"NeuZhou AI Toolkit" sounds corporate and vague. It would get zero stars on its own.

### DO build a personal brand

The **NeuZhou GitHub org** is the brand. The narrative:

> "The developer who builds tools for AI agents: test them (AgentProbe), secure them (ClawGuard), and watch them trade (FinClaw)."

Each repo links to the others. Each README mentions the ecosystem. But each repo stands on its own.

---

## 5. Final Rankings & Action Plan

### 🥇 #1: AgentProbe — GO ALL IN

**Star potential: 5,000-20,000**  
**Time to 100 stars: 2-4 weeks (with proper launch)**  
**Time to 1,000 stars: 3-6 months**

**What needs to change to maximize stars:**

1. **README is already excellent** — The YAML examples, comparison table, and "Playwright for AI Agents" positioning are perfect
2. **Needs real-world examples** — Create a `examples/` directory with tests for:
   - OpenAI function-calling agents
   - LangChain agents
   - CrewAI multi-agent workflows
   - OpenClaw agents
   - MCP server testing
3. **Needs a demo GIF** — 15-second terminal recording: write YAML → run → see pass/fail results
4. **Needs blog posts:**
   - "Why nobody is testing their AI agents (and why that's terrifying)"
   - "I tested my AI agent with AgentProbe and found 12 bugs in 5 minutes"
   - "The missing piece in AI agent development: behavioral testing"
5. **Launch on:**
   - Hacker News: "Show HN: AgentProbe – Playwright for AI Agents" (wait for HN karma ≥ 50)
   - Reddit: r/MachineLearning, r/LocalLLaMA, r/ChatGPT, r/artificial
   - Dev.to: Tutorial-style post
   - Twitter/X: Thread showing before/after (untested agent fails badly vs tested agent)
6. **Publish to ClawHub** — Get it into the OpenClaw ecosystem
7. **GitHub Topics:** Add `ai-agent-testing`, `ai-agents`, `testing-framework`, `mcp`, `llm-testing`, `developer-tools`

**The 24/7 AI assistant advantage:** Use the AI assistant to:
- Auto-generate test examples for popular agent frameworks
- Keep adapters updated as APIs change
- Auto-respond to issues
- Generate blog content drafts
- Monitor competitor activity

### 🥈 #2: ClawGuard — STRONG SECOND

**Star potential: 2,000-8,000**  
**Keep developing but don't split focus from AgentProbe**

**Key actions:**
1. **Position as AgentProbe's security companion** — "Test with AgentProbe, secure with ClawGuard"
2. **Differentiate from openguardrails** — ClawGuard is a library/CLI; openguardrails is an OpenClaw plugin. Different use cases.
3. **MCP Firewall is the killer feature** — With 90 repos in `mcp-security`, this is hot. Make it the headline feature.
4. **Get listed in OWASP resources** — The OWASP mapping in the README is excellent. Reach out to OWASP AI Security group.
5. **Blog: "We scanned 100 OpenClaw skills for security threats — here's what we found"**

### 🥉 #3: FinClaw — MAINTAIN, DON'T ABANDON

**Star potential: 500-2,000**  
**Don't archive. It's already your highest-starred repo.**

**Key actions:**
1. **Keep as a showcase** — It demonstrates you can build real systems
2. **Use it as an example** in AgentProbe docs ("test a real financial agent")
3. **Don't invest heavy development time** — Market is too crowded
4. **The GA evolution angle is genuinely unique** — but it's hard to explain in one sentence to non-quant people
5. **Opportunistic growth:** If crypto enters another bull run, finclaw will get organic traffic

### ❌ Should anything be abandoned?
**No.** All three repos serve a purpose:
- AgentProbe = star magnet, growth engine
- ClawGuard = credibility builder, security expertise proof
- FinClaw = existing traction, real-world showcase

### 💡 Should a NEW project be started?
**Not yet.** Focus beats diversification. The 24/7 AI assistant advantage means you can maintain all three, but marketing and community-building energy should go to ONE project. That's AgentProbe.

**Future project idea (after AgentProbe hits 1k stars):**
- **"AgentBench"** — A public leaderboard comparing AI agents on standardized behavioral tests (built on AgentProbe). This could be the "Stanford HELM" for agents. Leaderboards are star magnets.

---

## 6. 90-Day Execution Plan

### Week 1-2: AgentProbe Launch Prep
- [ ] Create 5+ real-world examples (OpenAI, LangChain, CrewAI, OpenClaw)
- [ ] Record demo GIF/video
- [ ] Write Dev.to launch post
- [ ] Add comprehensive GitHub topics
- [ ] Ensure npm package is polished (`npx agentprobe` just works)

### Week 3-4: Soft Launch
- [ ] Post on Dev.to
- [ ] Post on Reddit (r/MachineLearning, r/LocalLLaMA)
- [ ] Tweet/X thread
- [ ] Submit to "awesome-ai-agents" lists
- [ ] Submit to OpenClaw ClawHub

### Week 5-8: Community Building
- [ ] Open issues for "help wanted" / "good first issue"
- [ ] Create Discord/discussions
- [ ] Write weekly "What's new" updates
- [ ] Respond to all issues within 24h (AI assistant can draft responses)
- [ ] Cross-post: "How to test your LangChain agent" tutorial

### Week 9-12: HN Launch + Scale
- [ ] Build HN karma to 50+ (if not already)
- [ ] "Show HN: AgentProbe" launch
- [ ] Pitch to agent framework newsletters
- [ ] Reach out to AI security researchers for ClawGuard
- [ ] Evaluate: is AgentBench worth starting?

### Ongoing (AI Assistant Tasks)
- [ ] Monitor competitor releases (promptfoo, deepeval)
- [ ] Auto-update adapter compatibility
- [ ] Draft blog posts for review
- [ ] Keep all three repos' dependencies updated
- [ ] Respond to GitHub issues/discussions

---

## 7. Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Promptfoo adds agent testing | They're now OpenAI — likely to focus on OpenAI ecosystem. AgentProbe stays multi-provider |
| DeepEval adds tool call testing | DeepEval is Python-only. AgentProbe is TypeScript + YAML. Different audience |
| Someone else launches "Playwright for AI agents" | First-mover advantage. Ship fast, build community |
| OpenGuardrails dominates agent security | ClawGuard is a library, not just a plugin. Broader scope |
| Crypto winter kills finclaw interest | Already expected. That's why it's #3 |

---

## Bottom Line

The AI agent ecosystem has **17,922 repos** and **zero proper testing frameworks**. AgentProbe fills this gap with a proven playbook ("Playwright for X") and zero competition. This is a once-in-a-cycle opportunity.

Put 70% of energy into AgentProbe, 20% into ClawGuard, 10% into FinClaw maintenance.

The 24/7 AI assistant is the unfair advantage — use it to ship faster than any solo developer could.

**Target: AgentProbe at 1,000 stars by September 2026.**
